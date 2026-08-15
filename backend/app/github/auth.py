import time
from typing import Optional
import httpx
import jwt

from app.core.config import settings
from app.core.logging import logger


def _get_private_key() -> str:
    """
    Returns the RSA private key PEM string.
    Supports both inline PEM and \\n-escaped newlines (common in .env files).
    """
    key = settings.GITHUB_APP_PRIVATE_KEY or ""
    key = key.replace("\\n", "\n")
    return key


def generate_app_jwt() -> str:
    """
    Generates a short-lived JWT signed with the GitHub App RSA-256 private key.
    - iat: now - 60s  (handles clock drift)
    - exp: now + 9 min (GitHub max is 10 min)
    """
    private_key = _get_private_key()
    if not private_key or not settings.GITHUB_APP_ID:
        raise ValueError(
            "GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY must be set in environment."
        )

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": settings.GITHUB_APP_ID,
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


async def get_installation_access_token(installation_id: int) -> str:
    """
    Exchanges an App JWT for a short-lived installation access token.
    Valid for ~1 hour. Used to act as the installed GitHub App on a repo.
    """
    app_jwt = generate_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers)
        if response.status_code != 201:
            logger.error(
                f"Failed to get installation token for installation {installation_id}: "
                f"{response.status_code} {response.text}"
            )
            raise RuntimeError(
                f"GitHub API error {response.status_code}: {response.text}"
            )
        data = response.json()
        token = data.get("token")
        if not token:
            raise RuntimeError("GitHub API returned no token in response")

        logger.info(
            f"Obtained installation access token for installation {installation_id} "
            f"(expires: {data.get('expires_at')})"
        )
        return token
