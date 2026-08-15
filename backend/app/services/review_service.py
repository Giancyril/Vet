import asyncio
import time
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.health_score import HealthScore, calculate_health_score
from app.agents.multi_reviewer import run_multi_agent_analysis
from app.analysis.ast_analyzer import analyze_python_file
from app.core.logging import logger
from app.github.auth import get_installation_access_token
from app.github.commenter import post_github_review
from app.github.diff_fetcher import build_pr_context
from app.models.config import RepoConfig
from app.models.finding import ReviewFinding
from app.models.repository import Repository
from app.models.review import PullRequestReview
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse
from app.security.owasp_rules import classify_owasp
from app.security.secret_scanner import scan_diff_for_secrets
from app.services.notification_service import dispatch_review_notifications


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
        f_rank = severity_rank.get(f.severity, 1)
        if f_rank < min_rank:
            continue
        if config.enabled_categories and f.category not in config.enabled_categories:
            continue
        filtered.append(f)

    return filtered[: config.max_comments_per_pr]


def _scan_secrets_in_diff(context) -> list[GeminiFinding]:
    """Run regex and entropy-based secret scanning across all changed file diffs."""
    secret_findings = []
    for file in context.changed_files:
        if not file.patch:
            continue
        leaks = scan_diff_for_secrets(file.filename, file.patch)
        for leak in leaks:
            secret_findings.append(
                GeminiFinding(
                    file_path=leak.file_path,
                    line_number=leak.line_number,
                    side="RIGHT",
                    severity="blocking",
                    category="security",
                    title=f"🚨 Secret Leak: {leak.secret_type}",
                    explanation=(
                        f"{leak.description} Found pattern: `{leak.masked_secret}`. "
                        f"Immediately revoke, invalidate, and rotate this secret. "
                        f"Never commit credentials directly into source repositories."
                    ),
                    suggested_fix="os.environ.get('SECRET_KEY_NAME')",
                )
            )
    return secret_findings


def _run_ast_analysis_on_files(context) -> list[GeminiFinding]:
    """Run AST static analysis on changed Python files and generate structured findings."""
    static_findings = []
    for file in context.changed_files:
        if not file.filename.endswith(".py"):
            continue
        if not file.file_content:
            continue

        ast_res = analyze_python_file(
            after_source=file.file_content,
            file_path=file.filename,
            before_source=file.before_content if hasattr(file, "before_content") else None,
        )

        for bc in ast_res.breaking_changes:
            static_findings.append(
                GeminiFinding(
                    file_path=bc.file_path,
                    line_number=1,
                    side="RIGHT",
                    severity=bc.severity,
                    category="logic_bug",
                    title=f"Breaking API Change: {bc.kind.replace('_', ' ').title()}",
                    explanation=bc.detail,
                    suggested_fix=None,
                )
            )

        for cv in ast_res.complexity_violations:
            static_findings.append(
                GeminiFinding(
                    file_path=cv.file_path,
                    line_number=cv.line,
                    side="RIGHT",
                    severity="suggestion" if cv.cyclomatic_complexity > 15 else "nitpick",
                    category="performance" if cv.is_too_long else "style",
                    title=f"High Cyclomatic Complexity ({cv.cyclomatic_complexity}) in `{cv.function_name}`",
                    explanation=(
                        f"Function `{cv.function_name}` has a cyclomatic complexity of {cv.cyclomatic_complexity} "
                        f"(threshold is 10) and spans {cv.lines_of_code} lines. "
                        f"Consider refactoring into smaller, single-responsibility helper functions."
                    ),
                    suggested_fix=None,
                )
            )
    return static_findings


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
    3. Load repository config
    4. Run pre-LLM secret scanner (zero latency secret detection)
    5. Run AST static analysis (breaking changes + cyclomatic complexity)
    6. Run multi-agent concurrent analysis (4 specialist personas)
    7. Tag findings with OWASP Top 10 classifications
    8. Calculate PR Health Score
    9. Merge, deduplicate, and filter findings
    10. Post review to GitHub
    11. Persist to database
    12. Fire-and-forget: dispatch Slack/webhook notifications
    """
    start_time = time.time()
    logger.info(
        f"Starting multi-agent review pipeline for {owner}/{repo_name}#{pr_number} "
        f"(head: {head_sha[:7]})"
    )

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

    # 4. Pre-LLM Secret Scanning
    secret_findings = _scan_secrets_in_diff(context)

    # 5. AST Static Analysis
    static_findings = _run_ast_analysis_on_files(context)

    # 6. Multi-Agent Concurrent Analysis
    findings_by_role = await run_multi_agent_analysis(
        context=context,
        custom_instructions=custom_instructions or "",
    )

    # Combine into findings_by_role
    if secret_findings:
        findings_by_role.setdefault("security", []).extend(secret_findings)

    if static_findings:
        findings_by_role.setdefault("style", []).extend(
            [f for f in static_findings if f.category == "style"]
        )
        findings_by_role.setdefault("performance", []).extend(
            [f for f in static_findings if f.category == "performance"]
        )
        findings_by_role.setdefault("security", []).extend(
            [f for f in static_findings if f.category not in ["style", "performance"]]
        )

    # 7. Calculate PR Health Score
    health_score: HealthScore = calculate_health_score(findings_by_role)
    logger.info(
        f"Health score for {owner}/{repo_name}#{pr_number}: "
        f"{health_score.total}/100 ({health_score.grade}) — "
        f"{health_score.total_findings} findings, "
        f"{health_score.total_blocking} blocking"
    )

    # 8. Merge, deduplicate, and annotate OWASP
    all_findings: list[GeminiFinding] = []
    for role_findings in findings_by_role.values():
        all_findings.extend(role_findings)

    seen = set()
    unique_findings = []
    for f in all_findings:
        key = (f.file_path, f.line_number, f.title[:60])
        if key not in seen:
            seen.add(key)
            # Annotate with OWASP rule if security finding
            owasp = classify_owasp(f.title, f.explanation)
            if owasp and "OWASP" not in f.explanation:
                f.explanation += f"\n\n🛡️ **OWASP Top 10**: `{owasp.code}` ({owasp.name})"
            unique_findings.append(f)

    severity_order = {"blocking": 0, "suggestion": 1, "nitpick": 2}
    unique_findings.sort(key=lambda f: severity_order.get(f.severity, 3))
    filtered_findings = _filter_findings_by_config(unique_findings, config)

    # Build verdict
    has_blocking = any(f.severity == "blocking" for f in filtered_findings)
    if config and config.auto_request_changes and has_blocking:
        verdict = "REQUEST_CHANGES"
    elif health_score.total >= 90 and not filtered_findings:
        verdict = "APPROVE"
    elif not filtered_findings:
        verdict = "APPROVE"
    else:
        verdict = "COMMENT"

    # Build health score summary block
    health_badge = (
        f"## 🏥 PR Health Score: **{health_score.total}/100** ({health_score.grade})\n\n"
        f"{health_score.recommendation}\n\n"
        "| Dimension | Score | Findings |\n"
        "|-----------|-------|----------|\n"
    )
    for dim in health_score.dimensions:
        health_badge += (
            f"| {dim.emoji} {dim.dimension.title()} "
            f"| {dim.score:.0f}/100 "
            f"| {dim.finding_count} ({dim.blocking_count} blocking) |\n"
        )

    final_review = GeminiReviewResponse(
        summary=health_badge,
        verdict=verdict,
        findings=filtered_findings,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    # 9. Post Review to GitHub
    await post_github_review(
        owner=owner,
        repo=repo_name,
        pr_number=pr_number,
        head_sha=head_sha,
        review=final_review,
        installation_token=token,
        processing_duration_ms=duration_ms,
    )

    # 10. Persist Review and Findings to Database
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

    # 11. Fire-and-forget: Slack + webhook notifications
    pr_url = f"https://github.com/{full_name}/pull/{pr_number}"
    asyncio.create_task(
        dispatch_review_notifications(
            pr_title=pr_title,
            pr_number=pr_number,
            repo_full_name=full_name,
            pr_author=pr_author,
            health_grade=health_score.grade,
            health_score=health_score.total,
            total_findings=len(filtered_findings),
            blocking_count=blocking_cnt,
            pr_url=pr_url,
        )
    )

    logger.info(
        f"Completed multi-agent review for {owner}/{repo_name}#{pr_number} "
        f"in {duration_ms}ms → {len(filtered_findings)} findings persisted "
        f"| Health: {health_score.grade} ({health_score.total}/100)"
    )
    return review_record
