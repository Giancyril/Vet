"""
Changelog & Release Notes API endpoints.
POST /api/v1/reviews/{review_id}/generate-changelog
POST /api/v1/reviews/{review_id}/sync-pr-description
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.review import PullRequestReview
from app.services.changelog_service import generate_changelog
from app.github.auth import get_installation_access_token
from app.core.config import settings
from app.core.logging import logger
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ChangelogResponse(BaseModel):
    review_id: str
    conventional_commits: str
    release_notes: str
    migration_guide: str
    executive_summary: str
    version_bump: str


class SyncPRDescriptionRequest(BaseModel):
    changelog_text: str
    append: bool = True


class SyncPRDescriptionResponse(BaseModel):
    success: bool
    pr_url: str
    message: str


@router.post("/reviews/{review_id}/generate-changelog", response_model=ChangelogResponse)
async def generate_review_changelog(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate Conventional Commits changelog and release notes for a PR review."""
    result = await db.execute(
        select(PullRequestReview).where(PullRequestReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    diff_summary = f"PR #{review.pr_number} on repository: {review.total_findings} finding(s), verdict: {review.verdict}."

    changelog = await generate_changelog(
        pr_title=review.pr_title or f"PR #{review.pr_number}",
        pr_description="",
        diff_summary=diff_summary,
        findings_summary=f"{review.total_findings} findings, verdict: {review.verdict}",
    )

    return ChangelogResponse(
        review_id=review_id,
        conventional_commits=changelog.conventional_commits,
        release_notes=changelog.release_notes,
        migration_guide=changelog.migration_guide,
        executive_summary=changelog.executive_summary,
        version_bump=changelog.version_bump,
    )


@router.post("/reviews/{review_id}/sync-pr-description", response_model=SyncPRDescriptionResponse)
async def sync_pr_description(
    review_id: str,
    body: SyncPRDescriptionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update the GitHub PR description with the generated changelog."""
    result = await db.execute(
        select(PullRequestReview).where(PullRequestReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    try:
        # Fetch installation token via repository relationship
        from sqlalchemy import select as sa_select
        from app.models.installation import Installation
        inst_result = await db.execute(
            sa_select(Installation).where(Installation.repository_id == review.repository_id)
        )
        installation = inst_result.scalar_one_or_none()
        if not installation:
            raise HTTPException(status_code=400, detail="No installation found for this repository")

        token = await get_installation_access_token(installation.installation_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        new_body = body.changelog_text

        from app.models.repository import Repository
        repo_result = await db.execute(
            sa_select(Repository).where(Repository.id == review.repository_id)
        )
        repo = repo_result.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=400, detail="Repository not found")

        owner, repo_name = repo.full_name.split("/", 1)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{review.pr_number}"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(url, headers=headers, json={"body": new_body})
            resp.raise_for_status()
            pr_data = resp.json()

        return SyncPRDescriptionResponse(
            success=True,
            pr_url=pr_data.get("html_url", ""),
            message="PR description updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[changelog] PR description sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update PR description: {str(e)}")
