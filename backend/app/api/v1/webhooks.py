import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_github_signature
from app.db.session import get_db
from app.models.config import RepoConfig
from app.models.installation import Installation
from app.models.repository import Repository

router = APIRouter()


@router.post("/webhooks/github", status_code=status.HTTP_200_OK, tags=["Webhooks"])
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Receives and authenticates incoming GitHub Webhook events.
    Verifies HMAC-SHA256 signature in constant time.
    """
    raw_body = await request.body()

    # 1. Verify HMAC Signature
    if settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            logger.warning("Missing X-Hub-Signature-256 header on incoming webhook")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature",
            )

        if not verify_github_signature(
            raw_body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET
        ):
            logger.warning("Invalid HMAC-SHA256 signature on incoming webhook")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    else:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GITHUB_WEBHOOK_SECRET is not configured on server",
            )
        logger.warning(
            "GITHUB_WEBHOOK_SECRET is empty — skipping signature verification in development mode"
        )

    # 2. Parse JSON Payload
    try:
        payload_dict = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    logger.info(
        f"Received GitHub Webhook | Event: {x_github_event} | Delivery: {x_github_delivery}"
    )

    # 3. Handle Ping Event
    if x_github_event == "ping":
        zen = payload_dict.get("zen", "Keep it logically awesome.")
        logger.info(f"GitHub ping acknowledged: {zen}")
        return {"status": "ok", "event": "ping", "zen": zen}

    # 4. Handle Installation Events
    if x_github_event == "installation":
        action = payload_dict.get("action")
        inst_data = payload_dict.get("installation", {})
        inst_id = inst_data.get("id")
        account = inst_data.get("account", {})

        if action in ("created", "added") and inst_id:
            stmt = select(Installation).where(
                Installation.github_installation_id == inst_id
            )
            result = await db.execute(stmt)
            installation = result.scalar_one_or_none()

            if not installation:
                installation = Installation(
                    github_installation_id=inst_id,
                    account_name=account.get("login", "unknown"),
                    account_type=account.get("type", "User"),
                    account_avatar_url=account.get("avatar_url"),
                )
                db.add(installation)
                await db.commit()
                await db.refresh(installation)
                logger.info(
                    f"Created installation record for {installation.account_name} (ID: {inst_id})"
                )

        return {"status": "processed", "event": "installation", "action": action}

    # 5. Handle Pull Request Events
    if x_github_event == "pull_request":
        action = payload_dict.get("action")
        pr_data = payload_dict.get("pull_request", {})
        repo_data = payload_dict.get("repository", {})
        inst_data = payload_dict.get("installation", {})

        pr_number = pr_data.get("number")
        pr_title = pr_data.get("title")
        repo_id = repo_data.get("id")
        repo_full_name = repo_data.get("full_name")
        inst_id = inst_data.get("id")

        logger.info(
            f"Pull Request Event | Repo: {repo_full_name} | PR #{pr_number}: '{pr_title}' | Action: {action}"
        )

        if action in ("opened", "synchronize", "reopened"):
            if inst_id and repo_id:
                inst_stmt = select(Installation).where(
                    Installation.github_installation_id == inst_id
                )
                inst_res = await db.execute(inst_stmt)
                installation = inst_res.scalar_one_or_none()

                if not installation:
                    account = inst_data.get("account", {})
                    installation = Installation(
                        github_installation_id=inst_id,
                        account_name=account.get("login", repo_data.get("owner", {}).get("login", "unknown")),
                        account_type=account.get("type", "User"),
                        account_avatar_url=account.get("avatar_url"),
                    )
                    db.add(installation)
                    await db.flush()

                repo_stmt = select(Repository).where(
                    Repository.github_repo_id == repo_id
                )
                repo_res = await db.execute(repo_stmt)
                repository = repo_res.scalar_one_or_none()

                if not repository:
                    repository = Repository(
                        installation_id=installation.id,
                        github_repo_id=repo_id,
                        name=repo_data.get("name", "unknown"),
                        full_name=repo_full_name or "unknown",
                        owner_name=repo_data.get("owner", {}).get("login", "unknown"),
                        private=repo_data.get("private", False),
                        default_branch=repo_data.get("default_branch", "main"),
                    )
                    db.add(repository)
                    await db.flush()

                    config = RepoConfig(repository_id=repository.id)
                    db.add(config)

                await db.commit()

            return {
                "status": "received",
                "event": "pull_request",
                "action": action,
                "repository": repo_full_name,
                "pr_number": pr_number,
                "message": f"PR #{pr_number} event '{action}' queued for review analysis",
            }

    return {
        "status": "ignored",
        "event": x_github_event,
        "action": payload_dict.get("action"),
    }
