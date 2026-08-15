from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.config import RepoConfig
from app.models.repository import Repository
from app.models.review import PullRequestReview
from app.schemas.config import RepoConfigSchema, RepoConfigUpdate
from app.schemas.repo import RepositorySchema

router = APIRouter()


@router.get("/repos", response_model=List[RepositorySchema], tags=["Repositories"])
async def list_repositories(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lists all monitored GitHub repositories with config and review counts."""
    stmt = (
        select(Repository)
        .options(selectinload(Repository.config))
        .order_by(Repository.updated_at.desc())
    )
    if is_active is not None:
        stmt = stmt.where(Repository.is_active == is_active)

    res = await db.execute(stmt)
    repos = res.scalars().all()

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


@router.put(
    "/repos/{repo_id}/config",
    response_model=RepoConfigSchema,
    tags=["Repositories"],
)
async def update_repository_config(
    repo_id: str,
    update_data: RepoConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Updates reviewer settings for a specific repository."""
    # Find repo
    repo_stmt = select(Repository).where(Repository.id == repo_id)
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    # Find or create config
    cfg_stmt = select(RepoConfig).where(RepoConfig.repository_id == repo_id)
    cfg_res = await db.execute(cfg_stmt)
    config = cfg_res.scalar_one_or_none()

    if not config:
        config = RepoConfig(repository_id=repo_id)
        db.add(config)

    # Apply updates
    if update_data.min_severity is not None:
        if update_data.min_severity not in ("blocking", "suggestion", "nitpick"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_severity must be 'blocking', 'suggestion', or 'nitpick'",
            )
        config.min_severity = update_data.min_severity

    if update_data.auto_request_changes is not None:
        config.auto_request_changes = update_data.auto_request_changes

    if update_data.enabled_categories is not None:
        config.enabled_categories = update_data.enabled_categories

    if update_data.max_comments_per_pr is not None:
        config.max_comments_per_pr = max(1, min(50, update_data.max_comments_per_pr))

    if update_data.custom_instructions is not None:
        config.custom_instructions = update_data.custom_instructions

    await db.commit()
    await db.refresh(config)
    return config


@router.patch("/repos/{repo_id}/toggle", tags=["Repositories"])
async def toggle_repository_active(
    repo_id: str,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
):
    """Enables or disables automatic AI code reviews for a repository."""
    stmt = select(Repository).where(Repository.id == repo_id)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    repo.is_active = is_active
    await db.commit()
    await db.refresh(repo)
    return {"id": repo.id, "full_name": repo.full_name, "is_active": repo.is_active}
