import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository

DEFAULT_CATEGORIES = [
    "security",
    "logic_bug",
    "performance",
    "error_handling",
    "style",
    "test_coverage",
]


class RepoConfig(Base):
    __tablename__ = "repo_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    min_severity: Mapped[str] = mapped_column(String(50), default="suggestion")
    auto_request_changes: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled_categories: Mapped[List[str]] = mapped_column(JSON, default=DEFAULT_CATEGORIES)
    max_comments_per_pr: Mapped[int] = mapped_column(Integer, default=15)
    custom_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="config"
    )
