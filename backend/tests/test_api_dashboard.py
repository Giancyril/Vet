import pytest
import httpx
from app.db.session import async_session_factory
from app.main import app
from app.models.finding import ReviewFinding
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.review import PullRequestReview


@pytest.mark.asyncio
async def test_list_repos_and_get_repo():
    async with async_session_factory() as session:
        inst = Installation(
            github_installation_id=123123,
            account_name="Giancyril",
            account_type="User",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            installation_id=inst.id,
            github_repo_id=456456,
            name="cool-project",
            full_name="Giancyril/cool-project",
            owner_name="Giancyril",
            private=False,
            default_branch="main",
        )
        session.add(repo)
        await session.commit()
        repo_id = repo.id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # List repos
        resp = await client.get("/api/v1/repos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["full_name"] == "Giancyril/cool-project"

        # Get single repo
        resp_single = await client.get(f"/api/v1/repos/{repo_id}")
        assert resp_single.status_code == 200
        assert resp_single.json()["name"] == "cool-project"


@pytest.mark.asyncio
async def test_list_reviews_and_review_detail():
    async with async_session_factory() as session:
        inst = Installation(
            github_installation_id=111222,
            account_name="Giancyril",
            account_type="User",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            installation_id=inst.id,
            github_repo_id=333444,
            name="reviewer-test",
            full_name="Giancyril/reviewer-test",
            owner_name="Giancyril",
            private=False,
        )
        session.add(repo)
        await session.flush()

        rev = PullRequestReview(
            repository_id=repo.id,
            pr_number=42,
            pr_title="feat: awesome feature",
            pr_author="giancyril",
            head_sha="head_abc_123",
            base_sha="base_def_456",
            verdict="REQUEST_CHANGES",
            summary_markdown="Needs a few fixes.",
            total_findings=1,
            blocking_count=1,
            suggestion_count=0,
            nitpick_count=0,
            processing_duration_ms=1800,
        )
        session.add(rev)
        await session.flush()

        finding = ReviewFinding(
            review_id=rev.id,
            file_path="src/index.ts",
            line_number=12,
            side="RIGHT",
            severity="blocking",
            category="security",
            title="Unsanitized user input",
            explanation="Risk of XSS vulnerability.",
            suggested_fix="escapeHtml(input)",
        )
        session.add(finding)
        await session.commit()
        rev_id = rev.id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. List reviews
        resp = await client.get("/api/v1/reviews")
        assert resp.status_code == 200
        revs = resp.json()
        assert len(revs) >= 1
        assert revs[0]["pr_number"] == 42
        assert revs[0]["verdict"] == "REQUEST_CHANGES"
        assert revs[0]["metrics"]["blocking_count"] == 1

        # 2. Get review detail with findings
        resp_detail = await client.get(f"/api/v1/reviews/{rev_id}")
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["pr_title"] == "feat: awesome feature"
        assert len(detail["findings"]) == 1
        assert detail["findings"][0]["title"] == "Unsanitized user input"
        assert detail["findings"][0]["suggested_fix"] == "escapeHtml(input)"

        # 3. Stats endpoint
        resp_stats = await client.get("/api/v1/stats")
        assert resp_stats.status_code == 200
        stats = resp_stats.json()
        assert stats["total_reviews"] >= 1
        assert stats["total_blocking_prevented"] >= 1
        assert stats["active_repositories_count"] >= 1
