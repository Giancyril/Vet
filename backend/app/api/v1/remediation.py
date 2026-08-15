"""
Auto-Remediation API Router.
Endpoints to preview auto-fixes and create companion Pull Requests.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.github.auth import get_installation_access_token
from app.github.diff_fetcher import build_pr_context
from app.github.remediation_pr import create_companion_remediation_pr
from app.models.finding import ReviewFinding
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.review import PullRequestReview
from app.schemas.remediation import (
    CompanionPRResponseSchema,
    PatchPreviewSchema,
    RemediationPlanSchema,
)
from app.services.remediation_service import build_remediation_plan

router = APIRouter(prefix="/reviews", tags=["Remediation"])


@router.get(
    "/{review_id}/remediation-plan",
    response_model=RemediationPlanSchema,
    summary="Preview auto-remediation diff patches for a review",
)
async def get_remediation_plan(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PullRequestReview)
        .options(
            selectinload(PullRequestReview.repository),
            selectinload(PullRequestReview.findings),
        )
        .where(PullRequestReview.id == review_id)
    )
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Extract findings with fixes
    fixable = [f for f in review.findings if f.suggested_fix]
    if not fixable:
        return RemediationPlanSchema(
            review_id=review_id,
            branch_name=f"vet/fix-pr-{review.pr_number}",
            total_fixes=0,
            patches=[],
        )

    # Build mock file contents from findings (or from GitHub if accessible)
    # For preview, we construct the target file representation from finding context
    file_contents = {}
    for f in fixable:
        if f.file_path not in file_contents:
            # Synthesize a workable placeholder buffer with lines up to finding line
            lines = ["# Existing code line\n"] * (f.line_number + 5)
            file_contents[f.file_path] = "".join(lines)

    plan = build_remediation_plan(
        review_id=review.id,
        pr_number=review.pr_number,
        findings=fixable,
        file_contents=file_contents,
    )

    return RemediationPlanSchema(
        review_id=plan.review_id,
        branch_name=plan.branch_name,
        total_fixes=plan.total_fixes,
        patches=[
            PatchPreviewSchema(
                file_path=p.file_path,
                diff=p.diff,
                findings_fixed=p.findings_fixed,
            )
            for p in plan.patches
        ],
    )


@router.post(
    "/{review_id}/create-companion-pr",
    response_model=CompanionPRResponseSchema,
    summary="Create companion PR on GitHub with all auto-remediated fixes",
)
async def create_companion_pr(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PullRequestReview)
        .options(
            selectinload(PullRequestReview.repository),
            selectinload(PullRequestReview.findings),
        )
        .where(PullRequestReview.id == review_id)
    )
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()

    if not review or not review.repository:
        raise HTTPException(status_code=404, detail="Review or repository not found")

    # Get installation
    repo = review.repository
    inst_stmt = select(Installation).where(Installation.id == repo.installation_id)
    inst_res = await db.execute(inst_stmt)
    installation = inst_res.scalar_one_or_none()

    if not installation:
        raise HTTPException(status_code=400, detail="Repository installation not found")

    token = await get_installation_access_token(installation.installation_id)

    # Build PR Context to fetch real file contents from GitHub
    context = await build_pr_context(
        owner=repo.owner,
        repo=repo.name,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_author=review.pr_author,
        pr_body="",
        head_sha=review.head_sha,
        base_sha=review.base_sha,
        installation_token=token,
    )

    file_contents = {
        f.filename: f.file_content
        for f in context.changed_files
        if f.file_content
    }

    fixable = [f for f in review.findings if f.suggested_fix]
    plan = build_remediation_plan(
        review_id=review.id,
        pr_number=review.pr_number,
        findings=fixable,
        file_contents=file_contents,
    )

    result = await create_companion_remediation_pr(
        owner=repo.owner,
        repo=repo.name,
        base_branch=review.head_sha,  # Point back to PR head
        pr_number=review.pr_number,
        plan=plan,
        installation_token=token,
    )

    if not result:
        return CompanionPRResponseSchema(
            success=False,
            total_fixes=0,
            message="Failed to create companion PR on GitHub. Ensure GitHub App has write permissions.",
        )

    return CompanionPRResponseSchema(
        success=True,
        pr_number=result["pr_number"],
        pr_url=result["pr_url"],
        branch_name=result["branch_name"],
        total_fixes=result["total_fixes"],
        message=f"Companion PR #{result['pr_number']} created successfully!",
    )
