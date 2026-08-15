from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.finding import ReviewFinding
from app.models.repository import Repository
from app.models.review import PullRequestReview
from app.schemas.review import ReviewDetailSchema, ReviewMetrics, ReviewSummarySchema

router = APIRouter()


@router.get("/reviews", response_model=List[ReviewSummarySchema], tags=["Reviews"])
async def list_reviews(
    repository_id: Optional[str] = None,
    verdict: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lists PR reviews ordered by most recent first."""
    stmt = (
        select(PullRequestReview)
        .options(selectinload(PullRequestReview.repository))
        .order_by(PullRequestReview.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if repository_id:
        stmt = stmt.where(PullRequestReview.repository_id == repository_id)
    if verdict:
        stmt = stmt.where(PullRequestReview.verdict == verdict)

    res = await db.execute(stmt)
    reviews = res.scalars().all()

    output = []
    for r in reviews:
        metrics = ReviewMetrics(
            total_findings=r.total_findings,
            blocking_count=r.blocking_count,
            suggestion_count=r.suggestion_count,
            nitpick_count=r.nitpick_count,
            processing_duration_ms=r.processing_duration_ms,
        )
        repo_name = r.repository.full_name if r.repository else None
        output.append(
            ReviewSummarySchema(
                id=r.id,
                repository_id=r.repository_id,
                repo_full_name=repo_name,
                pr_number=r.pr_number,
                pr_title=r.pr_title,
                pr_author=r.pr_author,
                head_sha=r.head_sha,
                base_sha=r.base_sha,
                verdict=r.verdict,
                summary_markdown=r.summary_markdown,
                metrics=metrics,
                created_at=r.created_at,
            )
        )

    return output


@router.get("/reviews/{review_id}", response_model=ReviewDetailSchema, tags=["Reviews"])
async def get_review_detail(review_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves full PR review with all detailed findings."""
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )

    metrics = ReviewMetrics(
        total_findings=review.total_findings,
        blocking_count=review.blocking_count,
        suggestion_count=review.suggestion_count,
        nitpick_count=review.nitpick_count,
        processing_duration_ms=review.processing_duration_ms,
    )

    repo_name = review.repository.full_name if review.repository else None
    return ReviewDetailSchema(
        id=review.id,
        repository_id=review.repository_id,
        repo_full_name=repo_name,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_author=review.pr_author,
        head_sha=review.head_sha,
        base_sha=review.base_sha,
        verdict=review.verdict,
        summary_markdown=review.summary_markdown,
        metrics=metrics,
        created_at=review.created_at,
        findings=review.findings,
    )


@router.get("/stats", tags=["Dashboard"])
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Computes global metrics for the review dashboard."""
    # Total reviews
    total_revs_stmt = select(func.count(PullRequestReview.id))
    total_revs = (await db.execute(total_revs_stmt)).scalar() or 0

    # Severity counts
    counts_stmt = select(
        func.coalesce(func.sum(PullRequestReview.blocking_count), 0),
        func.coalesce(func.sum(PullRequestReview.suggestion_count), 0),
        func.coalesce(func.sum(PullRequestReview.nitpick_count), 0),
        func.coalesce(func.avg(PullRequestReview.processing_duration_ms), 0),
    )
    res = await db.execute(counts_stmt)
    blocking, suggestions, nitpicks, avg_duration = res.one()

    # Active repos
    active_repos_stmt = select(func.count(Repository.id)).where(Repository.is_active == True)
    active_repos = (await db.execute(active_repos_stmt)).scalar() or 0

    return {
        "total_reviews": total_revs,
        "total_blocking_prevented": int(blocking),
        "total_suggestions_made": int(suggestions),
        "total_nitpicks": int(nitpicks),
        "total_findings": int(blocking + suggestions + nitpicks),
        "avg_duration_ms": int(avg_duration),
        "active_repositories_count": active_repos,
    }
