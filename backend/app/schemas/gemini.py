from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class GeminiFinding(BaseModel):
    file_path: str = Field(..., description="Target file path relative to repo root")
    line_number: int = Field(..., description="Target line number in the NEW revision")
    side: Literal["RIGHT", "LEFT"] = Field(
        default="RIGHT", description="Side of the diff: RIGHT for new additions/modifications"
    )
    severity: Literal["blocking", "suggestion", "nitpick"] = Field(
        ..., description="Severity level: blocking, suggestion, or nitpick"
    )
    category: Literal[
        "security",
        "logic_bug",
        "performance",
        "error_handling",
        "style",
        "test_coverage",
    ] = Field(..., description="Categorization of the code review finding")
    title: str = Field(..., description="Short concise summary of the issue")
    explanation: str = Field(
        ..., description="Detailed technical explanation of why this is problematic and how to resolve it"
    )
    suggested_fix: Optional[str] = Field(
        default=None, description="Concrete code replacement or snippet fix"
    )


class GeminiReviewResponse(BaseModel):
    summary: str = Field(
        ..., description="High-level markdown summary of the PR review and architectural overview"
    )
    verdict: Literal["APPROVE", "COMMENT", "REQUEST_CHANGES"] = Field(
        default="COMMENT", description="Overall review verdict"
    )
    findings: List[GeminiFinding] = Field(
        default_factory=list, description="List of granular code review findings"
    )
