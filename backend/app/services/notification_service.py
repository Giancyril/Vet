"""
Notification dispatch service.
Supports Slack (incoming webhooks) and generic HTTP webhooks.
"""
import asyncio
import httpx
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


def _grade_emoji(grade: str) -> str:
    mapping = {"A+": "🌟", "A": "✅", "B": "🟡", "C": "🟠", "D": "🔴", "F": "💀"}
    return mapping.get(grade, "📊")


def _severity_label(blocking: int, total: int) -> str:
    if blocking > 0:
        return f"🚫 {blocking} blocking | {total} total"
    return f"✅ {total} findings (no blockers)"


async def send_slack_notification(
    pr_title: str,
    pr_number: int,
    repo_full_name: str,
    pr_author: str,
    health_grade: str,
    health_score: float,
    total_findings: int,
    blocking_count: int,
    pr_url: Optional[str] = None,
) -> bool:
    """
    Post a formatted Slack notification for a completed PR review.
    Requires SLACK_WEBHOOK_URL in environment.
    Returns True on success, False otherwise.
    """
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        logger.debug("SLACK_WEBHOOK_URL not set — skipping Slack notification")
        return False

    grade_emoji = _grade_emoji(health_grade)
    severity_label = _severity_label(blocking_count, total_findings)
    pr_link = f"<{pr_url}|#{pr_number}>" if pr_url else f"#{pr_number}"

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{grade_emoji} PR Review Complete — {repo_full_name}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*PR:*\n{pr_link} {pr_title}"},
                    {"type": "mrkdwn", "text": f"*Author:*\n@{pr_author}"},
                    {"type": "mrkdwn", "text": f"*Health Score:*\n`{health_score}/100` ({health_grade})"},
                    {"type": "mrkdwn", "text": f"*Findings:*\n{severity_label}"},
                ],
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 Powered by *Vet* — AI Code Review",
                    }
                ],
            },
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code == 200:
                logger.info(f"Slack notification sent for {repo_full_name}#{pr_number}")
                return True
            else:
                logger.warning(f"Slack notification failed: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Slack notification error: {e}")
        return False


async def send_generic_webhook(
    webhook_url: str,
    payload: dict,
) -> bool:
    """
    POST a JSON payload to a generic webhook URL.
    Used for custom integrations (Teams, Discord, etc.)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            success = response.status_code < 300
            if not success:
                logger.warning(f"Generic webhook failed: {response.status_code}")
            return success
    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        return False


async def dispatch_review_notifications(
    pr_title: str,
    pr_number: int,
    repo_full_name: str,
    pr_author: str,
    health_grade: str,
    health_score: float,
    total_findings: int,
    blocking_count: int,
    pr_url: Optional[str] = None,
) -> None:
    """
    Fire-and-forget all configured notification channels for a completed review.
    Called after review is persisted to DB.
    """
    tasks = []

    # Slack
    tasks.append(
        send_slack_notification(
            pr_title=pr_title,
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            pr_author=pr_author,
            health_grade=health_grade,
            health_score=health_score,
            total_findings=total_findings,
            blocking_count=blocking_count,
            pr_url=pr_url,
        )
    )

    # Generic webhook (if configured)
    if settings.NOTIFICATION_WEBHOOK_URL:
        generic_payload = {
            "event": "review_completed",
            "repo": repo_full_name,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "pr_author": pr_author,
            "health_score": health_score,
            "health_grade": health_grade,
            "total_findings": total_findings,
            "blocking_count": blocking_count,
            "pr_url": pr_url,
        }
        tasks.append(send_generic_webhook(settings.NOTIFICATION_WEBHOOK_URL, generic_payload))

    await asyncio.gather(*tasks, return_exceptions=True)
