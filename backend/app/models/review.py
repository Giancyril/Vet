import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.finding import ReviewFinding


class PullRequestReview(Base):
    __tablename__ = "pull_request_reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    pr_title: Mapped[str] = mapped_column(String(512), nullable=False)
    pr_author: Mapped[str] = mapped_column(String(255), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)

    verdict: Mapped[str] = mapped_column(String(50), default="COMMENT")
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")

    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    blocking_count: Mapped[int] = mapped_column(Integer, default=0)
    suggestion_count: Mapped[int] = mapped_column(Integer, default=0)
    nitpick_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="reviews"
    )
    findings: Mapped[List["ReviewFinding"]] = relationship(
        "ReviewFinding", back_populates="review", cascade="all, delete-orphan"
    )
