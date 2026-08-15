"""Unit tests for auto-remediation engine and patch generation."""
import pytest
from app.models.finding import ReviewFinding
from app.services.remediation_service import (
    apply_inline_fix,
    build_remediation_plan,
    RemediationFilePatch,
)


SAMPLE_SOURCE = """def process_items(items):
    res = []
    for i in range(len(items)):
        res.append(items[i] * 2)
    return res
"""


class TestAutoRemediation:
    def test_apply_inline_fix_single_line(self):
        original = "x = 1\ny = 2\nz = 3\n"
        fixed = apply_inline_fix(original, line_number=2, suggested_fix="y = 20\n")
        assert "y = 20" in fixed
        assert "x = 1" in fixed
        assert "z = 3" in fixed
        assert "y = 2\n" not in fixed

    def test_apply_inline_fix_multiline(self):
        original = "def foo():\n    pass\n"
        multiline_fix = "    x = 1\n    return x\n"
        fixed = apply_inline_fix(original, line_number=2, suggested_fix=multiline_fix)
        assert "def foo():" in fixed
        assert "x = 1" in fixed
        assert "return x" in fixed

    def test_build_remediation_plan_generates_diffs(self):
        finding1 = ReviewFinding(
            id="f1",
            review_id="r1",
            file_path="app/utils.py",
            line_number=3,
            side="RIGHT",
            severity="suggestion",
            category="performance",
            title="Use enumerate or direct iteration",
            explanation="Direct iteration is more pythonic and faster.",
            suggested_fix="    for item in items:\n        res.append(item * 2)",
        )

        file_contents = {"app/utils.py": SAMPLE_SOURCE}

        plan = build_remediation_plan(
            review_id="r1",
            pr_number=42,
            findings=[finding1],
            file_contents=file_contents,
        )

        assert plan.review_id == "r1"
        assert plan.branch_name == "vet/fix-pr-42"
        assert plan.total_fixes == 1
        assert len(plan.patches) == 1

        patch = plan.patches[0]
        assert patch.file_path == "app/utils.py"
        assert len(patch.diff) > 0
        assert "--- a/app/utils.py" in patch.diff
        assert "+++ b/app/utils.py" in patch.diff
        assert "for item in items:" in patch.patched_content

    def test_build_remediation_plan_skips_findings_without_fix(self):
        finding_no_fix = ReviewFinding(
            id="f2",
            review_id="r1",
            file_path="app/utils.py",
            line_number=1,
            side="RIGHT",
            severity="nitpick",
            category="style",
            title="Missing docstring",
            explanation="Add docstring",
            suggested_fix=None,
        )

        file_contents = {"app/utils.py": SAMPLE_SOURCE}

        plan = build_remediation_plan(
            review_id="r1",
            pr_number=42,
            findings=[finding_no_fix],
            file_contents=file_contents,
        )

        assert plan.total_fixes == 0
        assert len(plan.patches) == 0
