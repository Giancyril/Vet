"""
Auto-remediation engine.
Applies suggested code fixes to source files and produces unified git patches.
"""
import difflib
from dataclasses import dataclass
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.models.finding import ReviewFinding
from app.schemas.gemini import GeminiFinding


@dataclass
class RemediationFilePatch:
    file_path: str
    original_content: str
    patched_content: str
    diff: str
    findings_fixed: List[str]


@dataclass
class RemediationPlan:
    review_id: str
    patches: List[RemediationFilePatch]
    total_fixes: int
    branch_name: str


def apply_inline_fix(
    file_content: str,
    line_number: int,
    suggested_fix: str,
) -> str:
    """
    Replace or patch around a specific line in a source file with suggested fix.
    Handles single-line and multi-line suggestions cleanly.
    """
    lines = file_content.splitlines(keepends=True)
    if not lines:
        return suggested_fix

    target_idx = max(0, min(line_number - 1, len(lines) - 1))

    # Check if the suggested fix is a multi-line replacement block or single line
    fix_lines = suggested_fix.splitlines(keepends=True)
    if not fix_lines[-1].endswith("\n") and lines[target_idx].endswith("\n"):
        fix_lines[-1] += "\n"

    new_lines = lines[:target_idx] + fix_lines + lines[target_idx + 1 :]
    return "".join(new_lines)


def build_remediation_plan(
    review_id: str,
    pr_number: int,
    findings: List[ReviewFinding],
    file_contents: Dict[str, str],
) -> RemediationPlan:
    """
    Takes actionable findings with `suggested_fix` and applies them against file contents.
    Returns a structured plan with unified diffs ready to commit to a companion branch.
    """
    patches: List[RemediationFilePatch] = []
    total_fixes = 0

    # Group findings by file path
    by_file: Dict[str, List[ReviewFinding]] = {}
    for f in findings:
        if f.suggested_fix and f.file_path in file_contents:
            by_file.setdefault(f.file_path, []).append(f)

    for file_path, file_findings in by_file.items():
        original = file_contents[file_path]
        current = original

        # Sort descending by line number so edits at bottom don't offset line numbers above
        sorted_findings = sorted(file_findings, key=lambda x: x.line_number, reverse=True)
        fixed_titles = []

        for finding in sorted_findings:
            if finding.suggested_fix:
                current = apply_inline_fix(current, finding.line_number, finding.suggested_fix)
                fixed_titles.append(finding.title)
                total_fixes += 1

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                current.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )
        diff_str = "".join(diff_lines)

        patches.append(
            RemediationFilePatch(
                file_path=file_path,
                original_content=original,
                patched_content=current,
                diff=diff_str,
                findings_fixed=fixed_titles,
            )
        )

    branch_name = f"vet/fix-pr-{pr_number}"

    return RemediationPlan(
        review_id=review_id,
        patches=patches,
        total_fixes=total_fixes,
        branch_name=branch_name,
    )
