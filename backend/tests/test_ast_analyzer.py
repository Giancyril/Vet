"""Unit tests for AST static analyzer — breaking changes and cyclomatic complexity."""
import pytest
from app.analysis.ast_analyzer import (
    extract_public_functions,
    analyze_complexity,
    detect_breaking_changes,
    analyze_python_file,
)


# ─── Sample Python snippets ───────────────────────────────────────────────────

SIMPLE_CODE = """
def add(a: int, b: int) -> int:
    return a + b

def _private_func(x):
    return x * 2

async def fetch_data(url: str, timeout: int = 10):
    pass
"""

COMPLEX_CODE = """
def deeply_nested(a, b, c, d):
    if a > 0:
        if b > 0:
            for i in range(10):
                if c:
                    while d:
                        if i == 5:
                            return True
                        elif i == 6:
                            pass
    return False
"""

BEFORE_CODE = """
def calculate_total(price, tax_rate, discount=0):
    return price * (1 + tax_rate) - discount

def get_user(user_id):
    return {"id": user_id}

def delete_record(record_id):
    pass
"""

AFTER_BREAKING_CODE = """
def calculate_total(price):
    # removed tax_rate and discount
    return price

def get_user(user_id):
    return {"id": user_id}
# delete_record was completely removed
"""


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestExtractPublicFunctions:
    def test_extracts_public_functions(self):
        funcs = extract_public_functions(SIMPLE_CODE)
        assert "add" in funcs
        assert "fetch_data" in funcs
        assert "_private_func" not in funcs

    def test_extracts_param_names(self):
        funcs = extract_public_functions(SIMPLE_CODE)
        assert funcs["add"].params == ["a", "b"]
        assert funcs["fetch_data"].params == ["url", "timeout"]
        assert funcs["fetch_data"].is_async is True

    def test_handles_syntax_error_gracefully(self):
        funcs = extract_public_functions("def invalid syntax ((")
        assert funcs == {}


class TestCyclomaticComplexity:
    def test_simple_function_low_complexity(self):
        results = analyze_complexity(SIMPLE_CODE, "simple.py")
        add_res = next(r for r in results if r.function_name == "add")
        assert add_res.cyclomatic_complexity == 1
        assert add_res.is_too_complex is False

    def test_nested_function_high_complexity(self):
        results = analyze_complexity(COMPLEX_CODE, "complex.py")
        res = next(r for r in results if r.function_name == "deeply_nested")
        assert res.cyclomatic_complexity >= 7
        assert res.is_too_long is False


class TestBreakingChangeDetection:
    def test_detects_removed_function(self):
        changes = detect_breaking_changes(BEFORE_CODE, AFTER_BREAKING_CODE, "service.py")
        removed = [c for c in changes if c.kind == "removed"]
        assert len(removed) == 1
        assert removed[0].name == "delete_record"
        assert removed[0].severity == "blocking"

    def test_detects_removed_parameters(self):
        changes = detect_breaking_changes(BEFORE_CODE, AFTER_BREAKING_CODE, "service.py")
        param_removed = [c for c in changes if c.kind == "param_removed"]
        assert len(param_removed) == 1
        assert param_removed[0].name == "calculate_total"
        assert "tax_rate" in param_removed[0].detail

    def test_clean_diff_returns_no_breaking_changes(self):
        changes = detect_breaking_changes(BEFORE_CODE, BEFORE_CODE, "service.py")
        assert len(changes) == 0


class TestAnalyzePythonFile:
    def test_full_file_analysis_with_diff(self):
        res = analyze_python_file(
            after_source=AFTER_BREAKING_CODE,
            file_path="app/service.py",
            before_source=BEFORE_CODE,
        )
        assert len(res.breaking_changes) == 2
        assert res.parse_error is None

    def test_full_file_analysis_no_before(self):
        res = analyze_python_file(
            after_source=COMPLEX_CODE,
            file_path="app/complex.py",
        )
        assert len(res.breaking_changes) == 0
        assert res.parse_error is None
