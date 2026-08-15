import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.config import RepoConfig
from app.models.installation import Installation
from app.models.repository import Repository
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse
from app.services.review_service import _filter_findings_by_config, execute_pr_review_pipeline


def test_filter_findings_by_min_severity():
    config = RepoConfig(
        repository_id="fake-repo-id",
        min_severity="suggestion",  # should drop nitpicks
        enabled_categories=["security", "style"],
        max_comments_per_pr=10,
    )
    findings = [
        GeminiFinding(
            file_path="a.py", line_number=1, side="RIGHT",
            severity="nitpick", category="style",
            title="nit", explanation="minor",
        ),
        GeminiFinding(
            file_path="b.py", line_number=2, side="RIGHT",
            severity="suggestion", category="style",
            title="sug", explanation="medium",
        ),
        GeminiFinding(
            file_path="c.py", line_number=3, side="RIGHT",
            severity="blocking", category="security",
            title="block", explanation="critical",
        ),
    ]

    filtered = _filter_findings_by_config(findings, config)
    assert len(filtered) == 2
    severities = [f.severity for f in filtered]
    assert "nitpick" not in severities
    assert "suggestion" in severities
    assert "blocking" in severities


@pytest.mark.asyncio
async def test_execute_pr_review_pipeline_end_to_end():
    async with async_session_factory() as session:
        # Create test installation and repo in DB
        inst = Installation(
            github_installation_id=990011,
            account_name="Giancyril",
            account_type="User",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            installation_id=inst.id,
            github_repo_id=880022,
            name="test-repo",
            full_name="Giancyril/test-repo",
            owner_name="Giancyril",
            private=False,
            default_branch="main",
        )
        session.add(repo)
        await session.flush()

        cfg = RepoConfig(repository_id=repo.id, min_severity="suggestion")
        session.add(cfg)
        await session.commit()

    mock_gemini_review = GeminiReviewResponse(
        summary="Review completed successfully.",
        verdict="REQUEST_CHANGES",
        findings=[
            GeminiFinding(
                file_path="src/login.py",
                line_number=42,
                side="RIGHT",
                severity="blocking",
                category="security",
                title="Timing attack in password check",
                explanation="Use hmac.compare_digest instead of ==.",
                suggested_fix="return hmac.compare_digest(pwd, stored_pwd)",
            )
        ],
    )

    with patch(
        "app.services.review_service.get_installation_access_token",
        new=AsyncMock(return_value="ghs_test_token"),
    ), patch(
        "app.services.review_service.build_pr_context",
        new=AsyncMock(),
    ), patch(
        "app.services.review_service.analyze_pull_request",
        new=AsyncMock(return_value=mock_gemini_review),
    ), patch(
        "app.services.review_service.post_github_review",
        new=AsyncMock(return_value={"id": 98765}),
    ):
        async with async_session_factory() as session:
            review_record = await execute_pr_review_pipeline(
                owner="Giancyril",
                repo_name="test-repo",
                pr_number=12,
                pr_title="feat: add login check",
                pr_author="giancyril",
                pr_body="Adds user login endpoint",
                head_sha="head123456",
                base_sha="base123456",
                installation_id=990011,
                db=session,
            )

            assert review_record.pr_number == 12
            assert review_record.verdict == "REQUEST_CHANGES"
            assert review_record.total_findings == 1
            assert review_record.blocking_count == 1
            assert review_record.repository_id == repo.id
