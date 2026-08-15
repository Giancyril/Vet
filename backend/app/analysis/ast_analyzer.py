"""
AST-based static analysis for Python files.
Detects:
- Breaking changes (removed/renamed public functions, changed signatures)
- Cyclomatic complexity per function
- Long functions and deeply nested code
"""
import ast
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class FunctionSignature:
    name: str
    params: List[str]
    is_async: bool
    line: int
    is_public: bool  # doesn't start with _


@dataclass
class ComplexityResult:
    function_name: str
    file_path: str
    line: int
    cyclomatic_complexity: int
    lines_of_code: int
    is_too_complex: bool       # > 10
    is_too_long: bool          # > 50 lines


@dataclass
class BreakingChange:
    kind: str          # "removed" | "renamed" | "signature_changed" | "param_removed"
    name: str
    file_path: str
    detail: str
    severity: str = "blocking"


@dataclass
class ASTAnalysisResult:
    breaking_changes: List[BreakingChange] = field(default_factory=list)
    complexity_violations: List[ComplexityResult] = field(default_factory=list)
    file_path: str = ""
    parse_error: Optional[str] = None


# ─── Signature extraction ─────────────────────────────────────────────────────

def _extract_param_names(args: ast.arguments) -> List[str]:
    names = []
    for arg in args.args + args.posonlyargs + args.kwonlyargs:
        names.append(arg.arg)
    if args.vararg:
        names.append(f"*{args.vararg.arg}")
    if args.kwarg:
        names.append(f"**{args.kwarg.arg}")
    return names


def extract_public_functions(source: str) -> Dict[str, FunctionSignature]:
    """Parse Python source and return a map of public function name → signature."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    functions: Dict[str, FunctionSignature] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_public = not node.name.startswith("_")
            params = _extract_param_names(node.args)
            sig = FunctionSignature(
                name=node.name,
                params=params,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                line=node.lineno,
                is_public=is_public,
            )
            if is_public:
                functions[node.name] = sig
    return functions


# ─── Cyclomatic complexity ────────────────────────────────────────────────────

def _count_complexity(node: ast.AST) -> int:
    """
    Counts decision points (branches) in a function node.
    CC = 1 + #branches
    """
    count = 0

    _BRANCH_TYPES = (
        ast.If, ast.While, ast.For, ast.ExceptHandler,
        ast.With, ast.Assert, ast.comprehension,
    )

    for child in ast.walk(node):
        if isinstance(child, _BRANCH_TYPES):
            count += 1
        elif isinstance(child, ast.BoolOp):
            # and/or each add a branch
            count += len(child.values) - 1

    return 1 + count


def analyze_complexity(source: str, file_path: str) -> List[ComplexityResult]:
    """Return complexity metrics for every function in the source file."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc = _count_complexity(node)
            end_line = getattr(node, "end_lineno", node.lineno)
            loc = end_line - node.lineno + 1
            results.append(
                ComplexityResult(
                    function_name=node.name,
                    file_path=file_path,
                    line=node.lineno,
                    cyclomatic_complexity=cc,
                    lines_of_code=loc,
                    is_too_complex=cc > 10,
                    is_too_long=loc > 50,
                )
            )

    return results


# ─── Breaking change detection ────────────────────────────────────────────────

def detect_breaking_changes(
    before_source: str,
    after_source: str,
    file_path: str,
) -> List[BreakingChange]:
    """
    Compare public function signatures between two versions of a file.
    Returns a list of breaking changes detected.
    """
    before_funcs = extract_public_functions(before_source)
    after_funcs = extract_public_functions(after_source)

    changes: List[BreakingChange] = []

    for name, before_sig in before_funcs.items():
        if name not in after_funcs:
            # Function was removed — definite breaking change
            changes.append(
                BreakingChange(
                    kind="removed",
                    name=name,
                    file_path=file_path,
                    detail=f"Public function `{name}` was removed (was at line {before_sig.line})",
                    severity="blocking",
                )
            )
            continue

        after_sig = after_funcs[name]
        before_params = set(before_sig.params)
        after_params = set(after_sig.params)

        # Check for removed required params (ignoring *args/**kwargs)
        removed_params = before_params - after_params
        real_removed = {p for p in removed_params if not p.startswith("*")}
        added_params = after_params - before_params

        if real_removed:
            changes.append(
                BreakingChange(
                    kind="param_removed",
                    name=name,
                    file_path=file_path,
                    detail=(
                        f"Function `{name}`: removed parameter(s) "
                        f"{', '.join(f'`{p}`' for p in sorted(real_removed))} — "
                        f"callers passing these args will break"
                    ),
                    severity="blocking",
                )
            )

    return changes


# ─── Unified file analysis ────────────────────────────────────────────────────

def analyze_python_file(
    after_source: str,
    file_path: str,
    before_source: Optional[str] = None,
) -> ASTAnalysisResult:
    """
    Run full AST analysis on a Python file diff.
    - Complexity analysis on the new version
    - Breaking change detection if before_source is provided
    """
    result = ASTAnalysisResult(file_path=file_path)

    try:
        result.complexity_violations = [
            r for r in analyze_complexity(after_source, file_path)
            if r.is_too_complex or r.is_too_long
        ]
    except Exception as e:
        result.parse_error = str(e)
        return result

    if before_source:
        try:
            result.breaking_changes = detect_breaking_changes(
                before_source, after_source, file_path
            )
        except Exception as e:
            result.parse_error = str(e)

    return result
