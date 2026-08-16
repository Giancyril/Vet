"""
Custom Repository Policy Engine.

Evaluates bespoke codebase rules (regex + AST-based) against PR diffs.
Rules are stored per-repository in RepoConfig.custom_policy_rules (JSON field).

Built-in rule templates:
  - ban_print_statements: No raw print() in production code
  - require_type_hints: Public functions must have return type annotations
  - ban_datetime_now: Require UTC-aware datetime usage
  - ban_bare_except: No bare except: clauses
  - require_docstrings: Public functions/classes must have docstrings
  - ban_hardcoded_urls: Disallow hardcoded localhost URLs
"""
import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PolicyViolation:
    rule_id: str
    rule_name: str
    severity: str          # "error" | "warning" | "info"
    file: str
    line: int
    message: str
    code_snippet: str = ""


@dataclass
class PolicyResult:
    passed: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    rules_evaluated: int = 0
    rules_passed: int = 0


# ── Built-in Rule Templates ──────────────────────────────────────────────────

BUILTIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ban_print_statements": {
        "id": "ban_print_statements",
        "name": "No print() Statements",
        "description": "Disallows raw print() calls in production code. Use structured logging instead.",
        "type": "regex",
        "pattern": r"^\+.*\bprint\s*\(",
        "severity": "warning",
        "exclude_patterns": ["test_", "conftest", "debug_"],
    },
    "ban_bare_except": {
        "id": "ban_bare_except",
        "name": "No Bare except: Clauses",
        "description": "Bare except clauses swallow all exceptions including SystemExit.",
        "type": "regex",
        "pattern": r"^\+\s*except\s*:",
        "severity": "error",
    },
    "ban_datetime_now": {
        "id": "ban_datetime_now",
        "name": "Require UTC-Aware Datetime",
        "description": "Disallows datetime.now() without UTC. Use datetime.now(UTC) or datetime.utcnow().",
        "type": "regex",
        "pattern": r"^\+.*datetime\.now\(\)",
        "severity": "error",
    },
    "ban_hardcoded_urls": {
        "id": "ban_hardcoded_urls",
        "name": "No Hardcoded localhost URLs",
        "description": "Hardcoded localhost URLs should use configuration/environment variables.",
        "type": "regex",
        "pattern": r"http://localhost",
        "severity": "warning",
    },
    "require_type_hints": {
        "id": "require_type_hints",
        "name": "Require Return Type Hints",
        "description": "Public function definitions must include return type annotations.",
        "type": "ast",
        "check": "missing_return_annotation",
        "severity": "info",
    },
    "require_docstrings": {
        "id": "require_docstrings",
        "name": "Require Docstrings",
        "description": "Public functions and classes must have docstrings.",
        "type": "ast",
        "check": "missing_docstring",
        "severity": "info",
    },
}


# ── Evaluator Functions ──────────────────────────────────────────────────────

def _evaluate_regex_rule(rule: Dict, patch: str, filename: str) -> List[PolicyViolation]:
    violations = []
    pattern = rule.get("pattern", "")
    if not pattern:
        return violations

    exclude = rule.get("exclude_patterns", [])
    if any(ex in filename for ex in exclude):
        return violations

    lines = patch.splitlines()
    for i, line in enumerate(lines):
        try:
            if re.search(pattern, line):
                violations.append(PolicyViolation(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    severity=rule.get("severity", "warning"),
                    file=filename,
                    line=i + 1,
                    message=rule.get("description", f"Rule {rule['id']} violated"),
                    code_snippet=line.strip(),
                ))
        except re.error:
            continue
    return violations


def _evaluate_ast_rule(rule: Dict, patch: str, filename: str) -> List[PolicyViolation]:
    violations = []
    check = rule.get("check", "")
    added = "\n".join(l[1:] for l in patch.splitlines() if l.startswith("+"))

    try:
        tree = ast.parse(added)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue

            if check == "missing_return_annotation" and node.returns is None:
                violations.append(PolicyViolation(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    severity=rule.get("severity", "info"),
                    file=filename,
                    line=node.lineno,
                    message=f"Function `{node.name}` is missing a return type annotation.",
                    code_snippet=f"def {node.name}(...)",
                ))

            if check == "missing_docstring":
                if not (node.body and isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)):
                    violations.append(PolicyViolation(
                        rule_id=rule["id"],
                        rule_name=rule["name"],
                        severity=rule.get("severity", "info"),
                        file=filename,
                        line=node.lineno,
                        message=f"Function `{node.name}` is missing a docstring.",
                        code_snippet=f"def {node.name}(...)",
                    ))

        if isinstance(node, ast.ClassDef) and check == "missing_docstring":
            if not (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant)):
                violations.append(PolicyViolation(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    severity=rule.get("severity", "info"),
                    file=filename,
                    line=node.lineno,
                    message=f"Class `{node.name}` is missing a docstring.",
                    code_snippet=f"class {node.name}",
                ))

    return violations


def evaluate_policy(
    diff_files: List[Dict],
    custom_rules: Optional[List[Dict]] = None,
    enabled_builtins: Optional[List[str]] = None,
) -> PolicyResult:
    all_rules = list(custom_rules or [])

    for bid in (enabled_builtins or []):
        if bid in BUILTIN_TEMPLATES:
            all_rules.append(BUILTIN_TEMPLATES[bid])

    all_violations = []

    for file_info in diff_files:
        fname = file_info.get("filename", "")
        patch = file_info.get("patch", "") or ""
        if not patch:
            continue

        for rule in all_rules:
            rule_type = rule.get("type", "regex")
            if rule_type == "regex":
                all_violations.extend(_evaluate_regex_rule(rule, patch, fname))
            elif rule_type == "ast" and fname.endswith(".py"):
                all_violations.extend(_evaluate_ast_rule(rule, patch, fname))

    errors = sum(1 for v in all_violations if v.severity == "error")
    passed = errors == 0

    return PolicyResult(
        passed=passed,
        violations=all_violations,
        rules_evaluated=len(all_rules),
        rules_passed=len(all_rules) - len(set(v.rule_id for v in all_violations)),
    )


def evaluate_rule_snippet(rule: Dict, code_snippet: str, filename: str = "test.py") -> List[PolicyViolation]:
    fake_patch = "\n".join("+" + line for line in code_snippet.splitlines())
    rule_type = rule.get("type", "regex")
    if rule_type == "regex":
        return _evaluate_regex_rule(rule, fake_patch, filename)
    elif rule_type == "ast":
        return _evaluate_ast_rule(rule, fake_patch, filename)
    return []
