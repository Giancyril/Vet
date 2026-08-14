from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RepoConfigBase(BaseModel):
    min_severity: str = Field(
        default="suggestion", description="Minimum severity level: blocking, suggestion, or nitpick"
    )
    auto_request_changes: bool = Field(
        default=True, description="Automatically submit REQUEST_CHANGES if blocking findings exist"
    )
    enabled_categories: List[str] = Field(
        default=[
            "security",
            "logic_bug",
            "performance",
            "error_handling",
            "style",
            "test_coverage",
        ]
    )
    max_comments_per_pr: int = Field(default=15, ge=1, le=50)
    custom_instructions: Optional[str] = Field(
        default=None, description="Custom prompt instructions appended to the AI reviewer"
    )


class RepoConfigUpdate(BaseModel):
    min_severity: Optional[str] = None
    auto_request_changes: Optional[bool] = None
    enabled_categories: Optional[List[str]] = None
    max_comments_per_pr: Optional[int] = None
    custom_instructions: Optional[str] = None


class RepoConfigSchema(RepoConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
