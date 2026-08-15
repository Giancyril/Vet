from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.config import RepoConfig
from app.models.repository import Repository
from app.models.review import PullRequestReview
from app.schemas.repo import RepositorySchema

router = APIRouter()


@router.get("/repos", response_model=List[RepositorySchema], tags=["Repositories"])
async def list_repositories(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lists all monitored GitHub repositories with config and review counts."""
    stmt = select(Repository).options(selectinload(Repository.config)).order_by(Repository.updated_at.desc())
    if is_active is not None:
        stmt = stmt.where(Repository.is_active == is_active)

    res = await db.execute(stmt)
    repos = res.scalars().all()

    # Get review counts per repo
    count_stmt = select(
        PullRequestReview.repository_id, func.count(PullRequestReview.id).label("count")
    ).group_by(PullRequestReview.repository_id)
    count_res = await db.execute(count_stmt)
    counts_map = {row[0]: row[1] for row in count_res.all()}

    output = []
    for r in repos:
        r_dict = {
            "id": r.id,
            "installation_id": r.installation_id,
            "github_repo_id": r.github_repo_id,
            "name": r.name,
            "full_name": r.full_name,
            "owner_name": r.owner_name,
            "private": r.private,
            "default_branch": r.default_branch,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "config": r.config,
            "total_reviews_count": counts_map.get(r.id, 0),
        }
        output.append(RepositorySchema.model_validate(r_dict))

    return output


@router.get("/repos/{repo_id}", response_model=RepositorySchema, tags=["Repositories"])
async def get_repository(repo_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves single repository by ID."""
    stmt = (
        select(Repository)
        .options(selectinload(Repository.config))
        .where(Repository.id == repo_id)
    )
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    count_stmt = select(func.count(PullRequestReview.id)).where(
        PullRequestReview.repository_id == repo.id
    )
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar() or 0

    return RepositorySchema.model_validate({
        "id": repo.id,
        "installation_id": repo.installation_id,
        "github_repo_id": repo.github_repo_id,
        "name": repo.name,
        "full_name": repo.full_name,
        "owner_name": repo.owner_name,
        "private": repo.private,
        "default_branch": repo.default_branch,
        "is_active": repo.is_active,
        "created_at": repo.created_at,
        "config": repo.config,
        "total_reviews_count": total_count,
    })
