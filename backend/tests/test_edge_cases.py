import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.github.commenter import post_github_review
from app.github.diff_fetcher import ChangedFile, PRContext, _should_skip_file
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse
from app.services.gemini_reviewer import analyze_pull_request
from app.services.prompt_builder import _format_changed_file, build_review_prompt


# ─── 1. File Truncation & Large Content ──────────────────────────────────────

def test_large_file_content_truncation():
    large_content = "def test_fn():\n" + ("    print('line')\n" * 1000)
    cf = ChangedFile(
        filename="big_module.py",
        status="modified",
        patch="@@ -1,5 +1,10 @@\n+line",
        full_content=large_content,
    )
    formatted = _format_changed_file(cf, 0)
    assert "truncated" in formatted
    assert "big_module.py" in formatted


def test_binary_or_empty_diff_handling():
    cf = ChangedFile(
        filename="assets/logo.png",
        status="added",
        patch=None,
        full_content=None,
    )
    formatted = _format_changed_file(cf, 1)
    assert "No patch available" in formatted or "no patch available" in formatted
    assert "assets/logo.png" in formatted


# ─── 2. All Lockfiles PR & Zero Reviewable Files ─────────────────────────────

@pytest.mark.asyncio
async def test_pr_with_only_lockfiles_auto_approves():
    context = PRContext(
        owner="Giancyril",
        repo="test-project",
        pr_number=99,
        head_sha="sha_99",
        base_sha="sha_00",
        pr_title="chore(deps): update lockfiles",
        pr_author="dependabot[bot]",
        pr_body="Bumps dependency versions",
        changed_files=[],
        total_additions=500,
        total_deletions=200,
    )
    review = await analyze_pull_request(context)
    assert review.verdict == "APPROVE"
    assert len(review.findings) == 0
    assert "lockfiles" in review.summary.lower()


# ─── 3. GitHub Review Fallback on Invalid Line Numbers (422) ──────────────────

@pytest.mark.asyncio
async def test_post_github_review_fallback_on_422():
    finding = GeminiFinding(
        file_path="src/index.ts",
        line_number=9999,  # line not in diff hunk
        side="RIGHT",
        severity="blocking",
        category="security",
        title="Flaw at invalid line",
        explanation="Explanation",
    )
    review = GeminiReviewResponse(
        summary="Found 1 blocker.",
        verdict="REQUEST_CHANGES",
        findings=[finding],
    )

    # Mock review endpoint returning 422 Unprocessable Entity
    mock_review_fail = MagicMock()
    mock_review_fail.status_code = 422
    mock_review_fail.text = '{"message": "Validation Failed: line must be part of diff"}'

    # Mock fallback issue comment endpoint returning 201 Created
    mock_fallback_ok = MagicMock()
    mock_fallback_ok.status_code = 201
    mock_fallback_ok.json.return_value = {"id": 998877, "body": "Summary comment"}

    async def mock_post_side_effect(url, **kwargs):
        if "reviews" in url:
            return mock_review_fail
        return mock_fallback_ok

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post_side_effect)):
        result = await post_github_review(
            owner="Giancyril",
            repo="test-project",
            pr_number=99,
            head_sha="sha_99",
            review=review,
            installation_token="ghs_mock",
        )

        assert result["status"] == "fallback_summary_posted"
        assert result["status_code"] == 422


# ─── 4. Unicode & Special Character Handling ─────────────────────────────────

def test_prompt_builder_with_unicode_and_emojis():
    cf = ChangedFile(
        filename="src/i18n/日本語.ts",
        status="modified",
        patch="@@ -1,2 +1,3 @@\n+// こんにちは世界 🚀\n+const greeting = '你好';",
        full_content="// こんにちは世界 🚀\nconst greeting = '你好';\n",
    )
    ctx = PRContext(
        owner="Giancyril",
        repo="i18n-repo",
        pr_number=5,
        head_sha="sha_utf8",
        base_sha="sha_base",
        pr_title="feat: add 多言語 support 🎉",
        pr_author="giancyril",
        pr_body="Adds Japanese and Chinese greetings",
        changed_files=[cf],
    )
    prompt = build_review_prompt(ctx)
    assert "日本語.ts" in prompt
    assert "こんにちは世界" in prompt
    assert "多言語 support" in prompt
