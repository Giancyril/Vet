import time
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.github.auth import get_installation_access_token
from app.github.commenter import post_github_review
from app.github.diff_fetcher import build_pr_context
from app.models.config import RepoConfig
from app.models.finding import ReviewFinding
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.review import PullRequestReview
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse
from app.services.gemini_reviewer import analyze_pull_request


def _filter_findings_by_config(
    findings: list[GeminiFinding],
    config: Optional[RepoConfig],
) -> list[GeminiFinding]:
    """Filters findings according to repository severity and category settings."""
    if not config:
        return findings

    severity_rank = {"blocking": 3, "suggestion": 2, "nitpick": 1}
    min_rank = severity_rank.get(config.min_severity, 2)

    filtered = []
    for f in findings:
        # Check severity threshold
        f_rank = severity_rank.get(f.severity, 1)
        if f_rank < min_rank:
            continue

        # Check enabled categories
        if config.enabled_categories and f.category not in config.enabled_categories:
            continue

        filtered.append(f)

    # Apply max comments per PR
    return filtered[: config.max_comments_per_pr]


async def execute_pr_review_pipeline(
    owner: str,
    repo_name: str,
    pr_number: int,
    pr_title: str,
    pr_author: str,
    pr_body: str,
    head_sha: str,
    base_sha: str,
    installation_id: int,
    db: AsyncSession,
) -> PullRequestReview:
    """
    Full automated PR Review Execution Pipeline:
    1. Authenticate with GitHub App and get installation token
    2. Build context: fetch changed files, unified diffs, and file contents
    3. Load repository config (min severity, custom instructions, category filters)
    4. Run Gemini AI code review analysis
    5. Filter findings per repository configuration
    6. Post review back to GitHub (inline comments + summary review)
    7. Persist PullRequestReview and ReviewFindings in database
    """
    start_time = time.time()
    logger.info(f"Starting review pipeline for {owner}/{repo_name}#{pr_number} (head: {head_sha[:7]})")

    # 1. Get Installation Token
    token = await get_installation_access_token(installation_id)

    # 2. Build PR Context
    context = await build_pr_context(
        owner=owner,
        repo=repo_name,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_author=pr_author,
        pr_body=pr_body or "",
        head_sha=head_sha,
        base_sha=base_sha,
        installation_token=token,
    )

    # 3. Load Repository & Config from DB
    full_name = f"{owner}/{repo_name}"
    repo_stmt = select(Repository).where(Repository.full_name == full_name)
    repo_res = await db.execute(repo_stmt)
    repository = repo_res.scalar_one_or_none()

    config = None
    if repository:
        cfg_stmt = select(RepoConfig).where(RepoConfig.repository_id == repository.id)
        cfg_res = await db.execute(cfg_stmt)
        config = cfg_res.scalar_one_or_none()

    custom_instructions = config.custom_instructions if config else ""
    max_comments = config.max_comments_per_pr if config else 15

    # 4. Analyze with Gemini
    gemini_result = await analyze_pull_request(
        context=context,
        custom_instructions=custom_instructions or "",
        max_findings=max_comments,
    )

    # 5. Filter findings based on repo config
    filtered_findings = _filter_findings_by_config(gemini_result.findings, config)

    # Adjust verdict if auto_request_changes is enabled
    has_blocking = any(f.severity == "blocking" for f in filtered_findings)
    if config and config.auto_request_changes and has_blocking:
        verdict = "REQUEST_CHANGES"
    elif not filtered_findings:
        verdict = "APPROVE"
    else:
        verdict = gemini_result.verdict

    final_review = GeminiReviewResponse(
        summary=gemini_result.summary,
        verdict=verdict,
        findings=filtered_findings,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    # 6. Post Review to GitHub
    await post_github_review(
        owner=owner,
        repo=repo_name,
        pr_number=pr_number,
        head_sha=head_sha,
        review=final_review,
        installation_token=token,
        processing_duration_ms=duration_ms,
    )

    # 7. Persist Review and Findings to Database
    blocking_cnt = sum(1 for f in filtered_findings if f.severity == "blocking")
    suggestion_cnt = sum(1 for f in filtered_findings if f.severity == "suggestion")
    nitpick_cnt = sum(1 for f in filtered_findings if f.severity == "nitpick")

    review_record = PullRequestReview(
        repository_id=repository.id if repository else "untracked",
        pr_number=pr_number,
        pr_title=pr_title,
        pr_author=pr_author,
        head_sha=head_sha,
        base_sha=base_sha,
        verdict=verdict,
        summary_markdown=final_review.summary,
        total_findings=len(filtered_findings),
        blocking_count=blocking_cnt,
        suggestion_count=suggestion_cnt,
        nitpick_count=nitpick_cnt,
        processing_duration_ms=duration_ms,
    )

    if repository:
        db.add(review_record)
        await db.flush()

        for f in filtered_findings:
            finding_record = ReviewFinding(
                review_id=review_record.id,
                file_path=f.file_path,
                line_number=f.line_number,
                side=f.side or "RIGHT",
                severity=f.severity,
                category=f.category,
                title=f.title,
                explanation=f.explanation,
                suggested_fix=f.suggested_fix,
            )
            db.add(finding_record)

        await db.commit()
        await db.refresh(review_record)

    logger.info(
        f"Completed review pipeline for {owner}/{repo_name}#{pr_number} in {duration_ms}ms "
        f"— {len(filtered_findings)} findings persisted"
    )
    return review_record
