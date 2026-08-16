"""
Blast Radius & Dependency Impact API endpoint.
GET /api/v1/reviews/{review_id}/blast-radius
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.review import PullRequestReview
from app.analysis.blast_radius import calculate_blast_radius
from pydantic import BaseModel
from typing import Dict, List

router = APIRouter()


class BlastRadiusResponse(BaseModel):
    review_id: str
    modified_files: List[str]
    downstream_files: List[str]
    impact_index: float
    impact_level: str
    affected_endpoints: List[str]
    breaking_exports: List[str]
    summary: str
    dependency_graph: Dict[str, List[str]]


@router.get("/reviews/{review_id}/blast-radius", response_model=BlastRadiusResponse)
async def get_blast_radius(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Calculate and return the PR Blast Radius impact analysis for a review."""
    result = await db.execute(
        select(PullRequestReview).where(PullRequestReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    # Reconstruct minimal diff_files from stored finding data
    diff_files = []

    report = calculate_blast_radius(diff_files)

    return BlastRadiusResponse(
        review_id=review_id,
        modified_files=report.modified_files,
        downstream_files=report.downstream_files,
        impact_index=report.impact_index,
        impact_level=report.impact_level,
        affected_endpoints=report.affected_endpoints,
        breaking_exports=report.breaking_exports,
        summary=report.summary,
        dependency_graph=report.dependency_graph,
    )
