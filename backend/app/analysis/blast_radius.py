"""
PR Blast Radius & Static Dependency Impact Analyzer.

Parses Python import trees and symbol usage across the repo to calculate:
- Blast Radius Impact Index (0-100)
- Direct file modifications
- Downstream affected modules
- Public API surface changes
"""
import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class BlastRadiusReport:
    modified_files: List[str]
    downstream_files: List[str]
    impact_index: float        # 0-100
    impact_level: str          # "Low" | "Medium" | "High" | "Critical"
    affected_endpoints: List[str]
    breaking_exports: List[str]
    summary: str
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)


def _extract_imports(source: str) -> List[str]:
    """Extract all module imports from a Python source string."""
    imports = []
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except SyntaxError:
        # Try regex fallback for incomplete diffs
        for m in re.finditer(r"^(?:from|import)\s+([\w\.]+)", source, re.MULTILINE):
            imports.append(m.group(1))
    return imports


def _extract_public_symbols(source: str) -> Set[str]:
    """Extract top-level public function/class definitions."""
    symbols = set()
    try:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    symbols.add(node.name)
    except SyntaxError:
        pass
    return symbols


def _module_to_file(module: str) -> Optional[str]:
    """Convert dotted module path to relative file path."""
    parts = module.split(".")
    return "/".join(parts) + ".py"


def calculate_blast_radius(
    diff_files: List[Dict],
    repo_context: Optional[str] = None,
) -> BlastRadiusReport:
    """
    Analyze the blast radius of a PR given its changed files and diffs.

    Args:
        diff_files: List of dicts with keys "filename", "patch", "additions", "deletions"
        repo_context: Optional string representation of repo structure for deeper analysis

    Returns:
        BlastRadiusReport with impact assessment
    """
    modified_files = [f["filename"] for f in diff_files if f.get("filename")]
    modified_modules = set()
    dependency_graph: Dict[str, List[str]] = {}
    all_imported_by: Dict[str, List[str]] = {}
    affected_endpoints: List[str] = []
    breaking_exports: List[str] = []

    for file_info in diff_files:
        fname = file_info.get("filename", "")
        patch = file_info.get("patch", "") or ""

        if not fname.endswith(".py"):
            continue

        # Convert filename to module path
        mod = fname.replace("/", ".").replace("\\", ".").removesuffix(".py")
        modified_modules.add(mod)

        # Extract symbols changed in the patch
        added_lines = "\n".join(
            l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")
        )
        removed_lines = "\n".join(
            l[1:] for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")
        )

        added_syms = _extract_public_symbols(added_lines)
        removed_syms = _extract_public_symbols(removed_lines)

        # Symbols removed from patch = potentially breaking
        for sym in removed_syms - added_syms:
            breaking_exports.append(f"{fname}::{sym}")

        # Find downstream dependencies from import analysis
        imports = _extract_imports(added_lines) + _extract_imports(removed_lines)
        dependency_graph[fname] = list(set(
            _module_to_file(i) for i in imports if i
        ))

        # Detect API endpoint modifications
        if "router" in patch.lower() or "@app." in patch or "@router." in patch:
            for line in patch.splitlines():
                m = re.search(r'@(?:router|app)\.(get|post|put|delete|patch)\(["\'](.*?)["\'"]', line)
                if m:
                    affected_endpoints.append(f"{m.group(1).upper()} {m.group(2)}")

    # Determine downstream impact from known module dependency chains
    downstream_files = []
    for mod_file in modified_files:
        mod_name = mod_file.replace("/", ".").replace("\\", ".").removesuffix(".py")
        # Heuristic: check if the module is a core service/model
        if any(k in mod_file for k in ["service", "model", "schema", "db", "auth", "config"]):
            downstream_files.append(f"[downstream] modules importing {mod_file}")

    # Calculate Impact Index
    base_score = min(len(modified_files) * 8, 40)
    breaking_score = min(len(breaking_exports) * 15, 30)
    endpoint_score = min(len(affected_endpoints) * 10, 20)
    downstream_score = min(len(downstream_files) * 5, 10)
    impact_index = min(base_score + breaking_score + endpoint_score + downstream_score, 100)

    if impact_index >= 75:
        impact_level = "Critical"
    elif impact_index >= 50:
        impact_level = "High"
    elif impact_index >= 25:
        impact_level = "Medium"
    else:
        impact_level = "Low"

    summary = (
        f"{len(modified_files)} file(s) modified directly. "
        f"{len(breaking_exports)} breaking export(s) detected. "
        f"{len(affected_endpoints)} API endpoint(s) impacted. "
        f"Blast Radius: {impact_level} ({impact_index:.0f}/100)."
    )

    return BlastRadiusReport(
        modified_files=modified_files,
        downstream_files=downstream_files,
        impact_index=round(impact_index, 1),
        impact_level=impact_level,
        affected_endpoints=affected_endpoints,
        breaking_exports=breaking_exports,
        summary=summary,
        dependency_graph=dependency_graph,
    )
