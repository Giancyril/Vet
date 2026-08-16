"""
Custom Repository Policy Engine API endpoints.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.config import RepoConfig
from app.models.review import PullRequestReview
from app.models.finding import ReviewFinding
from app.security.policy_engine import (
    evaluate_policy, evaluate_rule_snippet, BUILTIN_TEMPLATES,
)
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


class PolicyConfigSchema(BaseModel):
    enabled_builtins: List[str] = []
    custom_rules: List[Dict[str, Any]] = []


class PolicyViolationSchema(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    file: str
    line: int
    message: str
    code_snippet: str


class PolicyResultResponse(BaseModel):
    passed: bool
    violations: List[PolicyViolationSchema]
    rules_evaluated: int
    rules_passed: int
    error_count: int
    warning_count: int


class TestRuleRequest(BaseModel):
    rule: Dict[str, Any]
    code_snippet: str
    filename: str = "test.py"


@router.get("/policy/templates")
async def get_policy_templates():
    """Return all available built-in policy rule templates."""
    return {"templates": list(BUILTIN_TEMPLATES.values())}


@router.get("/repos/{repo_id}/policy", response_model=PolicyConfigSchema)
async def get_policy_config(repo_id: str, db: AsyncSession = Depends(get_db)):
    """Get the policy configuration for a repository."""
    result = await db.execute(select(RepoConfig).where(RepoConfig.repository_id == repo_id))
    config = result.scalar_one_or_none()
    if not config or not config.custom_policy_rules:
        return PolicyConfigSchema()
    raw = json.loads(config.custom_policy_rules) if isinstance(config.custom_policy_rules, str) else config.custom_policy_rules
    return PolicyConfigSchema(
        enabled_builtins=raw.get("enabled_builtins", []),
        custom_rules=raw.get("custom_rules", []),
    )


@router.put("/repos/{repo_id}/policy", response_model=PolicyConfigSchema)
async def update_policy_config(
    repo_id: str,
    body: PolicyConfigSchema,
    db: AsyncSession = Depends(get_db),
):
    """Update the policy rule configuration for a repository."""
    result = await db.execute(select(RepoConfig).where(RepoConfig.repository_id == repo_id))
    config = result.scalar_one_or_none()

    policy_data = json.dumps({
        "enabled_builtins": body.enabled_builtins,
        "custom_rules": body.custom_rules,
    })

    if config:
        config.custom_policy_rules = policy_data
    else:
        config = RepoConfig(repository_id=repo_id, custom_policy_rules=policy_data)
        db.add(config)

    await db.commit()
    return body


@router.post("/policy/test-rule")
async def test_policy_rule(body: TestRuleRequest):
    """Test a single custom rule against a code snippet."""
    violations = evaluate_rule_snippet(body.rule, body.code_snippet, body.filename)
    return {
        "violations": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "line": v.line,
                "message": v.message,
                "code_snippet": v.code_snippet,
            }
            for v in violations
        ],
        "passed": len(violations) == 0,
    }


@router.post("/reviews/{review_id}/run-policy", response_model=PolicyResultResponse)
async def run_policy_check(review_id: str, db: AsyncSession = Depends(get_db)):
    """Run the policy engine against a stored review's findings."""
    result = await db.execute(
        select(PullRequestReview).where(PullRequestReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    repo_result = await db.execute(
        select(RepoConfig).where(RepoConfig.repository_id == review.repository_id)
    )
    config = repo_result.scalar_one_or_none()

    enabled_builtins = []
    custom_rules = []
    if config and config.custom_policy_rules:
        raw = json.loads(config.custom_policy_rules) if isinstance(config.custom_policy_rules, str) else config.custom_policy_rules
        enabled_builtins = raw.get("enabled_builtins", [])
        custom_rules = raw.get("custom_rules", [])

    # Get file paths from findings
    findings_result = await db.execute(
        select(ReviewFinding.file_path).where(ReviewFinding.review_id == review_id).distinct()
    )
    file_paths = [row[0] for row in findings_result.fetchall() if row[0]]
    diff_files = [{"filename": fp, "patch": ""} for fp in file_paths]

    policy_result = evaluate_policy(diff_files, custom_rules, enabled_builtins)

    return PolicyResultResponse(
        passed=policy_result.passed,
        violations=[
            PolicyViolationSchema(
                rule_id=v.rule_id,
                rule_name=v.rule_name,
                severity=v.severity,
                file=v.file,
                line=v.line,
                message=v.message,
                code_snippet=v.code_snippet,
            )
            for v in policy_result.violations
        ],
        rules_evaluated=policy_result.rules_evaluated,
        rules_passed=policy_result.rules_passed,
        error_count=sum(1 for v in policy_result.violations if v.severity == "error"),
        warning_count=sum(1 for v in policy_result.violations if v.severity == "warning"),
    )
