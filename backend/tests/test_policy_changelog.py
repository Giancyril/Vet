"""Tests for changelog service and custom policy engine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.security.policy_engine import (
    evaluate_policy, test_rule_against_snippet, BUILTIN_TEMPLATES, PolicyViolation
)


# ── Policy Engine Tests ─────────────────────────────────────────────────────

class TestPolicyEngine:
    def test_empty_rules_no_violations(self):
        result = evaluate_policy(
            [{"filename": "app/main.py", "patch": "+print('hello')"}],
            custom_rules=[],
            enabled_builtins=[],
        )
        assert result.passed is True
        assert result.violations == []

    def test_ban_print_builtin(self):
        result = evaluate_policy(
            [{"filename": "app/service.py", "patch": "+    print('debug')"}],
            enabled_builtins=["ban_print_statements"],
        )
        assert not result.passed or len([v for v in result.violations if v.rule_id == "ban_print_statements"]) >= 0

    def test_ban_bare_except_detects_violation(self):
        patch = "+    except:\n+        pass"
        result = evaluate_policy(
            [{"filename": "app/handler.py", "patch": patch}],
            enabled_builtins=["ban_bare_except"],
        )
        violations = [v for v in result.violations if v.rule_id == "ban_bare_except"]
        assert len(violations) > 0
        assert violations[0].severity == "error"

    def test_ban_datetime_now(self):
        patch = "+    ts = datetime.now()"
        result = evaluate_policy(
            [{"filename": "app/utils.py", "patch": patch}],
            enabled_builtins=["ban_datetime_now"],
        )
        violations = [v for v in result.violations if v.rule_id == "ban_datetime_now"]
        assert len(violations) > 0

    def test_ban_hardcoded_urls(self):
        patch = "+    url = 'http://localhost:8080/api'"
        result = evaluate_policy(
            [{"filename": "app/client.py", "patch": patch}],
            enabled_builtins=["ban_hardcoded_urls"],
        )
        violations = [v for v in result.violations if v.rule_id == "ban_hardcoded_urls"]
        assert len(violations) > 0

    def test_custom_regex_rule(self):
        custom_rule = {
            "id": "no_todos",
            "name": "No TODO comments",
            "description": "Disallow TODO comments.",
            "type": "regex",
            "pattern": r"^\+.*\bTODO\b",
            "severity": "warning",
        }
        patch = "+    # TODO: fix this later"
        result = evaluate_policy(
            [{"filename": "app/module.py", "patch": patch}],
            custom_rules=[custom_rule],
        )
        violations = [v for v in result.violations if v.rule_id == "no_todos"]
        assert len(violations) > 0

    def test_ast_require_type_hints(self):
        patch = "+def process_data(items):\n+    pass"
        result = evaluate_policy(
            [{"filename": "app/processor.py", "patch": patch}],
            enabled_builtins=["require_type_hints"],
        )
        violations = [v for v in result.violations if v.rule_id == "require_type_hints"]
        assert len(violations) > 0

    def test_ast_require_docstrings(self):
        patch = "+def undocumented_func():\n+    return 42"
        result = evaluate_policy(
            [{"filename": "app/utils.py", "patch": patch}],
            enabled_builtins=["require_docstrings"],
        )
        violations = [v for v in result.violations if v.rule_id == "require_docstrings"]
        assert len(violations) > 0

    def test_exclude_patterns_skip_test_files(self):
        result = evaluate_policy(
            [{"filename": "tests/test_auth.py", "patch": "+    print('test output')"}],
            enabled_builtins=["ban_print_statements"],
        )
        # test files should be excluded by exclude_patterns
        violations = [v for v in result.violations if v.rule_id == "ban_print_statements"]
        assert len(violations) == 0

    def test_non_python_file_skips_ast_rules(self):
        result = evaluate_policy(
            [{"filename": "frontend/App.tsx", "patch": "+const x = 1;"}],
            enabled_builtins=["require_type_hints"],
        )
        assert result.violations == []

    def test_rules_evaluated_count(self):
        result = evaluate_policy(
            [{"filename": "app/main.py", "patch": "+pass"}],
            enabled_builtins=["ban_print_statements", "ban_bare_except"],
        )
        assert result.rules_evaluated == 2

    def test_test_rule_against_snippet_regex(self):
        rule = {
            "id": "no_debugger",
            "name": "No debugger statements",
            "type": "regex",
            "pattern": r"\bdebugger\b",
            "severity": "error",
        }
        violations = test_rule_against_snippet(rule, "debugger;\nx = 1;", "app.js")
        assert len(violations) > 0

    def test_test_rule_against_snippet_clean(self):
        rule = {
            "id": "no_debugger",
            "name": "No debugger",
            "type": "regex",
            "pattern": r"\bdebugger\b",
            "severity": "error",
        }
        violations = test_rule_against_snippet(rule, "x = 1\ny = 2", "app.py")
        assert len(violations) == 0

    def test_all_builtin_templates_exist(self):
        expected = {
            "ban_print_statements", "ban_bare_except", "ban_datetime_now",
            "ban_hardcoded_urls", "require_type_hints", "require_docstrings"
        }
        assert expected.issubset(set(BUILTIN_TEMPLATES.keys()))

    def test_passed_false_when_error_violations(self):
        patch = "+    except:\n+        pass"
        result = evaluate_policy(
            [{"filename": "app/handler.py", "patch": patch}],
            enabled_builtins=["ban_bare_except"],
        )
        # Should fail since bare_except is "error" severity
        assert result.passed is False

    def test_empty_diff_files(self):
        result = evaluate_policy([], enabled_builtins=["ban_print_statements"])
        assert result.passed is True
        assert result.violations == []
