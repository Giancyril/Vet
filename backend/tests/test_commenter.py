import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.github.commenter import (
    format_inline_comment,
    format_summary_review,
    post_github_review,
)
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse


def test_format_inline_comment_with_suggested_fix():
    finding = GeminiFinding(
        file_path="src/auth.py",
        line_number=10,
        side="RIGHT",
        severity="blocking",
        category="security",
        title="Hardcoded API Secret",
        explanation="Secret must be retrieved from environment.",
        suggested_fix="API_KEY = os.environ['API_KEY']",
    )
    formatted = format_inline_comment(finding)
    assert "🚨 **Blocking Issue**" in formatted
    assert "🛡️ Security" in formatted
    assert "Hardcoded API Secret" in formatted
    assert "```suggestion" in formatted
    assert "API_KEY = os.environ['API_KEY']" in formatted


def test_format_inline_comment_without_suggested_fix():
    finding = GeminiFinding(
        file_path="src/calc.py",
        line_number=5,
        side="RIGHT",
        severity="nitpick",
        category="style",
        title="Naming convention",
        explanation="Variable should be snake_case.",
        suggested_fix=None,
    )
    formatted = format_inline_comment(finding)
    assert "🔍 **Nitpick**" in formatted
    assert "🎨 Style & Readability" in formatted
    assert "```suggestion" not in formatted


def test_format_summary_review_approved():
    review = GeminiReviewResponse(
        summary="Code looks clean, well structured.",
        verdict="APPROVE",
        findings=[],
    )
    md = format_summary_review(review, processing_duration_ms=1200)
    assert "✅ **Approved**" in md
    assert "1.2s" in md
    assert "Code looks clean" in md
    assert "🚨 **Blocking** | `0`" in md


def test_format_summary_review_changes_requested():
    finding = GeminiFinding(
        file_path="src/db.py",
        line_number=20,
        side="RIGHT",
        severity="blocking",
        category="security",
        title="SQL injection",
        explanation="Use parameterized query.",
    )
    review = GeminiReviewResponse(
        summary="Critical security vulnerability found.",
        verdict="REQUEST_CHANGES",
        findings=[finding],
    )
    md = format_summary_review(review, processing_duration_ms=3500)
    assert "🛑 **Changes Requested**" in md
    assert "🚨 **Blocking** | `1`" in md


@pytest.mark.asyncio
async def test_post_github_review_payload_construction():
    finding = GeminiFinding(
        file_path="src/api.py",
        line_number=15,
        side="RIGHT",
        severity="suggestion",
        category="performance",
        title="Add caching",
        explanation="This query is expensive.",
        suggested_fix="return get_cached(key)",
    )
    review = GeminiReviewResponse(
        summary="Good improvements.",
        verdict="COMMENT",
        findings=[finding],
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": 12345, "state": "COMMENTED"}

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)) as mock_post:
        result = await post_github_review(
            owner="Giancyril",
            repo="test-repo",
            pr_number=7,
            head_sha="abc789",
            review=review,
            installation_token="ghs_mock_token_123",
            processing_duration_ms=1500,
        )

        assert result["id"] == 12345
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        json_payload = call_kwargs["json"]
        assert json_payload["commit_id"] == "abc789"
        assert json_payload["event"] == "COMMENT"
        assert len(json_payload["comments"]) == 1
        assert json_payload["comments"][0]["path"] == "src/api.py"
        assert json_payload["comments"][0]["line"] == 15
        assert "```suggestion" in json_payload["comments"][0]["body"]
