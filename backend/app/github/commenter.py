from typing import Any, Dict, List, Optional
import httpx

from app.core.logging import logger
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse


SEVERITY_BADGES = {
    "blocking": "🚨 **Blocking Issue**",
    "suggestion": "💡 **Suggestion**",
    "nitpick": "🔍 **Nitpick**",
}

CATEGORY_LABELS = {
    "security": "🛡️ Security",
    "logic_bug": "🐛 Logic Bug",
    "performance": "⚡ Performance",
    "error_handling": "⚠️ Error Handling",
    "style": "🎨 Style & Readability",
    "test_coverage": "🧪 Test Coverage",
}


def format_inline_comment(finding: GeminiFinding) -> str:
    """
    Formats a single finding into GitHub PR inline comment markdown.
    If suggested_fix is present, renders GitHub's native ```suggestion block
    so developers can apply it directly with one click.
    """
    severity_badge = SEVERITY_BADGES.get(finding.severity, finding.severity.upper())
    category_label = CATEGORY_LABELS.get(finding.category, finding.category)

    body = f"{severity_badge} | `{category_label}`\n\n"
    body += f"### {finding.title}\n\n"
    body += f"{finding.explanation}\n"

    if finding.suggested_fix and finding.suggested_fix.strip():
        fix = finding.suggested_fix.strip()
        body += f"\n```suggestion\n{fix}\n```\n"

    return body


def format_summary_review(
    review: GeminiReviewResponse,
    processing_duration_ms: int = 0,
) -> str:
    """
    Formats the top-level PR review summary comment.
    Includes status badges, executive summary, findings metrics breakdown table,
    and a clean footer.
    """
    blocking_count = sum(1 for f in review.findings if f.severity == "blocking")
    suggestion_count = sum(1 for f in review.findings if f.severity == "suggestion")
    nitpick_count = sum(1 for f in review.findings if f.severity == "nitpick")
    total = len(review.findings)

    if review.verdict == "APPROVE":
        verdict_badge = "✅ **Approved**"
    elif review.verdict == "REQUEST_CHANGES":
        verdict_badge = "🛑 **Changes Requested**"
    else:
        verdict_badge = "💬 **Commented**"

    duration_str = f"{processing_duration_ms / 1000:.1f}s" if processing_duration_ms > 0 else "< 1s"

    summary_md = f"""## 🤖 AI Code Review Summary

{verdict_badge} &nbsp;|&nbsp; ⏱️ Review completed in **{duration_str}**

---

### Executive Summary
{review.summary}

---

### Findings Overview

| Severity | Count | Action Required |
| :--- | :---: | :--- |
| 🚨 **Blocking** | `{blocking_count}` | Must resolve before merging |
| 💡 **Suggestion** | `{suggestion_count}` | Recommended improvements |
| 🔍 **Nitpick** | `{nitpick_count}` | Minor style/polish |
| **Total** | `{total}` | |

---
*Reviewed with **Google Gemini** • Automated Pull Request Guard*
"""
    return summary_md.strip()


async def post_github_review(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    review: GeminiReviewResponse,
    installation_token: str,
    processing_duration_ms: int = 0,
) -> Dict[str, Any]:
    """
    Posts an atomic Pull Request Review to GitHub via the REST API.
    Combines top-level review summary and line-specific inline comments in one request.
    Endpoint: POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews
    """
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

    # Map Gemini verdict to GitHub Review Event
    # GitHub allows: APPROVE, REQUEST_CHANGES, COMMENT
    event = review.verdict
    if event not in ("APPROVE", "REQUEST_CHANGES", "COMMENT"):
        event = "COMMENT"

    # Build inline comments array
    comments_payload = []
    for finding in review.findings:
        comments_payload.append({
            "path": finding.file_path,
            "line": finding.line_number,
            "side": finding.side or "RIGHT",
            "body": format_inline_comment(finding),
        })

    summary_body = format_summary_review(review, processing_duration_ms)

    payload = {
        "commit_id": head_sha,
        "body": summary_body,
        "event": event,
        "comments": comments_payload,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code not in (200, 201):
            logger.error(
                f"Failed to post GitHub review for {owner}/{repo}#{pr_number}: "
                f"{response.status_code} {response.text}"
            )
            # If posting batch review fails (e.g. invalid line number in diff),
            # fallback to posting summary comment as a standard issue comment
            fallback_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
            fb_resp = await client.post(fallback_url, headers=headers, json={"body": summary_body})
            logger.info(f"Fallback summary comment posted: {fb_resp.status_code}")
            return {
                "id": None,
                "status": "fallback_summary_posted",
                "status_code": response.status_code,
                "error": response.text,
            }

        data = response.json()
        logger.info(
            f"Successfully posted GitHub review {data.get('id')} to {owner}/{repo}#{pr_number} "
            f"with {len(comments_payload)} inline comments"
        )
        return data
