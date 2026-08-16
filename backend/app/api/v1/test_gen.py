"""
AI Test Generator API endpoints.
POST /api/v1/reviews/{review_id}/generate-tests
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.review import PullRequestReview
from app.models.finding import ReviewFinding
from app.services.test_generator import generate_tests_for_diff
from pydantic import BaseModel
from typing import List

router = APIRouter()


class TestSuiteItem(BaseModel):
    filename: str
    source_file: str
    test_code: str
    functions_covered: List[str]
    coverage_estimate: str


class GenerateTestsResponse(BaseModel):
    review_id: str
    suites: List[TestSuiteItem]
    total_suites: int
    message: str


@router.post("/reviews/{review_id}/generate-tests", response_model=GenerateTestsResponse)
async def generate_tests(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered pytest test suites for all modified files in a PR review."""
    result = await db.execute(
        select(PullRequestReview).where(PullRequestReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    # Get file paths from findings
    findings_result = await db.execute(
        select(ReviewFinding.file_path).where(
            ReviewFinding.review_id == review_id
        ).distinct()
    )
    file_paths = [row[0] for row in findings_result.fetchall() if row[0]]

    diff_files = [{"filename": fp, "patch": ""} for fp in file_paths]
    pr_context = f"{review.pr_title or f'PR #{review.pr_number}'}"
    suites = await generate_tests_for_diff(diff_files, pr_context=pr_context)

    return GenerateTestsResponse(
        review_id=review_id,
        suites=[
            TestSuiteItem(
                filename=s.filename,
                source_file=s.source_file,
                test_code=s.test_code,
                functions_covered=s.functions_covered,
                coverage_estimate=s.coverage_estimate,
            )
            for s in suites
        ],
        total_suites=len(suites),
        message=f"Generated {len(suites)} test suite(s) covering modified Python files.",
    )
