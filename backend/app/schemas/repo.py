from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.config import RepoConfigSchema


class RepositorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    installation_id: str
    github_repo_id: int
    name: str
    full_name: str
    owner_name: str
    private: bool
    default_branch: str
    is_active: bool
    created_at: datetime
    config: Optional[RepoConfigSchema] = None
    total_reviews_count: Optional[int] = 0
