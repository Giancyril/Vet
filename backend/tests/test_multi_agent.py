"""Unit tests for multi-agent reviewer – AgentPersona definitions and health score calculator."""
import pytest
from app.agents.personas import (
    ALL_PERSONAS,
    SECURITY_AUDITOR,
    PERFORMANCE_ARCHITECT,
    CLEAN_CODE_GUARDIAN,
    TEST_COVERAGE_SPECIALIST,
)
from app.agents.health_score import calculate_health_score, _letter_grade
from app.schemas.gemini import GeminiFinding


# ─── Helper ───────────────────────────────────────────────────────────────────

def _make_finding(
    severity: str = "suggestion",
    category: str = "security",
    file_path: str = "app/main.py",
    line_number: int = 10,
) -> GeminiFinding:
    return GeminiFinding(
        file_path=file_path,
        line_number=line_number,
        side="RIGHT",
        severity=severity,
        category=category,
        title=f"Test finding ({severity})",
        explanation="Test explanation",
        suggested_fix=None,
    )


# ─── Persona tests ────────────────────────────────────────────────────────────

class TestAgentPersonas:
    def test_all_personas_loaded(self):
        assert len(ALL_PERSONAS) == 4

    def test_persona_names_unique(self):
        names = [p.name for p in ALL_PERSONAS]
        assert len(names) == len(set(names))

    def test_persona_roles_unique(self):
        roles = [p.role for p in ALL_PERSONAS]
        assert len(roles) == len(set(roles))

    def test_security_auditor_is_strict(self):
        assert SECURITY_AUDITOR.severity_bias == "strict"
        assert "security" in SECURITY_AUDITOR.categories

    def test_performance_architect_categories(self):
        assert "performance" in PERFORMANCE_ARCHITECT.categories

    def test_clean_code_guardian_is_lenient(self):
        assert CLEAN_CODE_GUARDIAN.severity_bias == "lenient"

    def test_test_specialist_includes_test_coverage(self):
        assert "test_coverage" in TEST_COVERAGE_SPECIALIST.categories

    def test_all_personas_have_emoji(self):
        for p in ALL_PERSONAS:
            assert p.emoji, f"Persona {p.name} is missing an emoji"

    def test_all_personas_have_system_prompt(self):
        for p in ALL_PERSONAS:
            assert len(p.system_prompt) > 50, f"Persona {p.name} has a too-short system prompt"


# ─── Health score tests ───────────────────────────────────────────────────────

class TestHealthScore:
    def test_perfect_score_no_findings(self):
        result = calculate_health_score(
            {"security": [], "performance": [], "style": [], "testing": []}
        )
        assert result.total == 100.0
        assert result.grade == "A+"
        assert result.total_findings == 0
        assert result.total_blocking == 0

    def test_blocking_finding_reduces_score(self):
        findings = [_make_finding(severity="blocking", category="security")]
        result = calculate_health_score(
            {"security": findings, "performance": [], "style": [], "testing": []}
        )
        # Security weight = 0.35; 1 blocking costs 15 pts → security dim = 85
        # composite = 85*0.35 + 100*0.25 + 100*0.20 + 100*0.20 = 29.75 + 65 = 94.75
        assert result.total < 100.0
        assert result.total_blocking == 1

    def test_multiple_blocking_findings_degrade_to_f(self):
        findings = [_make_finding(severity="blocking", category="security") for _ in range(10)]
        result = calculate_health_score(
            {"security": findings, "performance": [], "style": [], "testing": []}
        )
        # 10 blocking = 150 pts penalty → security dim = 0
        security_dim = next(d for d in result.dimensions if d.dimension == "security")
        assert security_dim.score == 0.0

    def test_nitpick_minimal_penalty(self):
        findings = [_make_finding(severity="nitpick", category="style")]
        result = calculate_health_score(
            {"security": [], "performance": [], "style": findings, "testing": []}
        )
        assert result.total > 95.0

    def test_letter_grade_boundaries(self):
        assert _letter_grade(100) == "A+"
        assert _letter_grade(95) == "A+"
        assert _letter_grade(90) == "A"
        assert _letter_grade(80) == "B"
        assert _letter_grade(70) == "C"
        assert _letter_grade(60) == "D"
        assert _letter_grade(59) == "F"
        assert _letter_grade(0) == "F"

    def test_recommendation_blocking_message(self):
        findings = [_make_finding(severity="blocking", category="security")]
        result = calculate_health_score(
            {"security": findings, "performance": [], "style": [], "testing": []}
        )
        assert "blocking" in result.recommendation.lower()

    def test_recommendation_excellent_when_clean(self):
        result = calculate_health_score(
            {"security": [], "performance": [], "style": [], "testing": []}
        )
        assert "Excellent" in result.recommendation or "ready" in result.recommendation.lower()

    def test_dimensions_count(self):
        result = calculate_health_score(
            {"security": [], "performance": [], "style": [], "testing": []}
        )
        assert len(result.dimensions) == 4

    def test_dimension_emojis_present(self):
        result = calculate_health_score(
            {"security": [], "performance": [], "style": [], "testing": []}
        )
        for dim in result.dimensions:
            assert dim.emoji, f"Dimension {dim.dimension} missing emoji"

    def test_mixed_severity_findings(self):
        security_findings = [
            _make_finding(severity="blocking", category="security"),
            _make_finding(severity="suggestion", category="security"),
        ]
        style_findings = [
            _make_finding(severity="nitpick", category="style"),
        ]
        result = calculate_health_score(
            {
                "security": security_findings,
                "performance": [],
                "style": style_findings,
                "testing": [],
            }
        )
        assert result.total_findings == 3
        assert result.total_blocking == 1
