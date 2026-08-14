from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FindingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_id: str
    file_path: str
    line_number: int
    side: str
    severity: str
    category: str
    title: str
    explanation: str
    suggested_fix: Optional[str] = None
    github_comment_id: Optional[int] = None
    is_resolved: bool
    created_at: datetime


class ReviewMetrics(BaseModel):
    total_findings: int
    blocking_count: int
    suggestion_count: int
    nitpick_count: int
    processing_duration_ms: int


class ReviewSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    repo_full_name: Optional[str] = None
    pr_number: int
    pr_title: str
    pr_author: str
    head_sha: str
    base_sha: str
    verdict: str
    summary_markdown: str
    metrics: ReviewMetrics
    created_at: datetime


class ReviewDetailSchema(ReviewSummarySchema):
    model_config = ConfigDict(from_attributes=True)

    findings: List[FindingSchema] = Field(default_factory=list)
