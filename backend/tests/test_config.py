import pytest
import httpx
from app.db.session import async_session_factory
from app.main import app
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.config import RepoConfig


@pytest.mark.asyncio
async def test_update_repo_config_and_toggle_active():
    async with async_session_factory() as session:
        inst = Installation(
            github_installation_id=555666,
            account_name="Giancyril",
            account_type="User",
        )
        session.add(inst)
        await session.flush()

        repo = Repository(
            installation_id=inst.id,
            github_repo_id=777888,
            name="config-test-repo",
            full_name="Giancyril/config-test-repo",
            owner_name="Giancyril",
            private=False,
        )
        session.add(repo)
        await session.flush()

        cfg = RepoConfig(
            repository_id=repo.id,
            min_severity="suggestion",
            auto_request_changes=True,
            enabled_categories=["security", "logic_bug"],
            max_comments_per_pr=10,
        )
        session.add(cfg)
        await session.commit()
        repo_id = repo.id

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Update config
        update_payload = {
            "min_severity": "blocking",
            "auto_request_changes": False,
            "enabled_categories": ["security", "performance"],
            "max_comments_per_pr": 5,
            "custom_instructions": "Check for SQL injection and N+1 queries strictly.",
        }
        put_resp = await client.put(f"/api/v1/repos/{repo_id}/config", json=update_payload)
        assert put_resp.status_code == 200
        data = put_resp.json()
        assert data["min_severity"] == "blocking"
        assert data["auto_request_changes"] is False
        assert data["enabled_categories"] == ["security", "performance"]
        assert data["max_comments_per_pr"] == 5
        assert "SQL injection" in data["custom_instructions"]

        # 2. Test invalid severity rejection
        bad_resp = await client.put(
            f"/api/v1/repos/{repo_id}/config",
            json={"min_severity": "invalid_severity"},
        )
        assert bad_resp.status_code == 400

        # 3. Test toggle active
        toggle_resp = await client.patch(
            f"/api/v1/repos/{repo_id}/toggle?is_active=false"
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["is_active"] is False
