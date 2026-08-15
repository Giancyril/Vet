"""
PR Health Score calculator.
Aggregates findings from all agents into a 0-100 composite score
with letter grade and a breakdown per dimension.
"""
from dataclasses import dataclass, field
from typing import Dict, List

from app.agents.personas import ALL_PERSONAS
from app.schemas.gemini import GeminiFinding


# Severity point costs (subtracted from base of 100)
_SEVERITY_COST = {
    "blocking": 15,
    "suggestion": 4,
    "nitpick": 1,
}

# Weight per dimension (must sum to 1.0)
_DIM_WEIGHT = {
    "security": 0.35,
    "performance": 0.25,
    "style": 0.20,
    "testing": 0.20,
}

_GRADE_THRESHOLDS = [
    (95, "A+"),
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
]


@dataclass
class DimensionScore:
    dimension: str
    score: float          # 0-100
    finding_count: int
    blocking_count: int
    emoji: str


@dataclass
class HealthScore:
    total: float                        # 0-100 weighted composite
    grade: str                          # A+ / A / B / C / D / F
    dimensions: List[DimensionScore] = field(default_factory=list)
    total_findings: int = 0
    total_blocking: int = 0
    recommendation: str = ""


def _dim_emoji(role: str) -> str:
    mapping = {
        "security": "🛡️",
        "performance": "⚡",
        "style": "✨",
        "testing": "🧪",
    }
    return mapping.get(role, "📊")


def _compute_dim_score(findings: List[GeminiFinding]) -> tuple[float, int, int]:
    """Returns (score, total_findings, blocking_count)."""
    penalty = 0
    blocking = 0
    for f in findings:
        cost = _SEVERITY_COST.get(f.severity, 1)
        penalty += cost
        if f.severity == "blocking":
            blocking += 1
    score = max(0.0, 100.0 - penalty)
    return score, len(findings), blocking


def _letter_grade(score: float) -> str:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _build_recommendation(score: float, blocking: int, dims: List[DimensionScore]) -> str:
    if blocking > 0:
        return f"🚫 {blocking} blocking issue(s) must be resolved before merging."
    if score >= 90:
        return "✅ Excellent — ready to merge with confidence."
    if score >= 75:
        weakest = min(dims, key=lambda d: d.score)
        return f"⚠️ Good shape, but consider improving {weakest.dimension} (score: {weakest.score:.0f})."
    if score >= 60:
        return "🔧 Needs work before merge — address suggestions across multiple areas."
    return "❌ Major issues found — significant rework required."


def calculate_health_score(
    findings_by_role: Dict[str, List[GeminiFinding]],
) -> HealthScore:
    """
    Compute a composite PR health score from multi-agent findings.

    Args:
        findings_by_role: {role: [finding, ...]} from run_multi_agent_analysis

    Returns:
        HealthScore with per-dimension breakdown and composite grade
    """
    dimensions: List[DimensionScore] = []
    composite = 0.0
    total_findings = 0
    total_blocking = 0

    for persona in ALL_PERSONAS:
        role_findings = findings_by_role.get(persona.role, [])
        dim_score, count, blocking = _compute_dim_score(role_findings)
        weight = _DIM_WEIGHT.get(persona.role, 0.0)
        composite += dim_score * weight
        total_findings += count
        total_blocking += blocking
        dimensions.append(
            DimensionScore(
                dimension=persona.role,
                score=dim_score,
                finding_count=count,
                blocking_count=blocking,
                emoji=_dim_emoji(persona.role),
            )
        )

    grade = _letter_grade(composite)
    recommendation = _build_recommendation(composite, total_blocking, dimensions)

    return HealthScore(
        total=round(composite, 1),
        grade=grade,
        dimensions=dimensions,
        total_findings=total_findings,
        total_blocking=total_blocking,
        recommendation=recommendation,
    )
