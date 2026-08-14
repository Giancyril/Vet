import hashlib
import hmac
import json
import pytest
import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.security import verify_github_signature
from app.db.session import async_session_factory
from app.main import app
from app.models.installation import Installation
from app.models.repository import Repository

TEST_SECRET = "test_webhook_secret_key_12345"


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


@pytest.fixture(autouse=True)
def configure_test_secret(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", TEST_SECRET)


def test_verify_github_signature_direct():
    payload = b'{"zen": "Design for failure."}'
    sig = generate_signature(payload, TEST_SECRET)

    assert verify_github_signature(payload, sig, TEST_SECRET) is True
    assert verify_github_signature(payload, sig, "wrong_secret") is False

    tampered_payload = b'{"zen": "Design for success."}'
    assert verify_github_signature(tampered_payload, sig, TEST_SECRET) is False

    assert verify_github_signature(payload, "invalid_header", TEST_SECRET) is False
    assert verify_github_signature(payload, None, TEST_SECRET) is False


@pytest.mark.asyncio
async def test_webhook_ping_event():
    payload = {"zen": "Approachable is better than simple.", "hook_id": 12345}
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = generate_signature(payload_bytes, TEST_SECRET)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["event"] == "ping"
        assert data["zen"] == "Approachable is better than simple."


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected():
    payload = {"action": "opened"}
    payload_bytes = json.dumps(payload).encode("utf-8")
    wrong_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": wrong_sig,
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_missing_signature_rejected():
    payload = {"action": "opened"}
    payload_bytes = json.dumps(payload).encode("utf-8")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 401
        assert "Missing webhook signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_pull_request_opened_persists_repo():
    payload = {
        "action": "opened",
        "number": 101,
        "pull_request": {
            "id": 999901,
            "number": 101,
            "title": "feat: add user authentication",
            "user": {"login": "giancyril", "id": 1001},
            "head": {"sha": "abc12345", "ref": "feat/auth"},
            "base": {"sha": "def67890", "ref": "main"},
            "html_url": "https://github.com/Giancyril/test-repo/pull/101",
        },
        "repository": {
            "id": 888001,
            "name": "test-repo",
            "full_name": "Giancyril/test-repo",
            "private": False,
            "default_branch": "main",
            "owner": {"login": "Giancyril", "id": 1001},
        },
        "installation": {
            "id": 777001,
            "account": {"login": "Giancyril", "type": "User"},
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = generate_signature(payload_bytes, TEST_SECRET)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event"] == "pull_request"
        assert data["action"] == "opened"
        assert data["pr_number"] == 101

    async with async_session_factory() as session:
        inst_stmt = select(Installation).where(
            Installation.github_installation_id == 777001
        )
        inst_res = await session.execute(inst_stmt)
        installation = inst_res.scalar_one_or_none()
        assert installation is not None
        assert installation.account_name == "Giancyril"

        repo_stmt = select(Repository).where(
            Repository.github_repo_id == 888001
        )
        repo_res = await session.execute(repo_stmt)
        repo = repo_res.scalar_one_or_none()
        assert repo is not None
        assert repo.full_name == "Giancyril/test-repo"
        assert repo.installation_id == installation.id
