"""Schemas for auto-remediation endpoints."""
from typing import List, Optional
from pydantic import BaseModel


class PatchPreviewSchema(BaseModel):
    file_path: str
    diff: str
    findings_fixed: List[str]


class RemediationPlanSchema(BaseModel):
    review_id: str
    branch_name: str
    total_fixes: int
    patches: List[PatchPreviewSchema]


class CompanionPRResponseSchema(BaseModel):
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    branch_name: Optional[str] = None
    total_fixes: int = 0
    message: str
