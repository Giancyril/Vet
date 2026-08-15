"""Unit tests for chat service and notification dispatch."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.chat_service import ChatMessage, ChatContext, _trim_history, _build_context_block
from app.services.notification_service import (
    _grade_emoji,
    _severity_label,
    send_slack_notification,
    send_generic_webhook,
)


# ─── Chat service tests ───────────────────────────────────────────────────────

class TestChatService:
    def test_trim_history_keeps_last_6(self):
        history = [ChatMessage(role="user", content=f"msg {i}") for i in range(10)]
        trimmed = _trim_history(history)
        assert len(trimmed) == 6
        assert trimmed[0].content == "msg 4"

    def test_trim_history_no_op_when_short(self):
        history = [ChatMessage(role="user", content="hi")]
        trimmed = _trim_history(history)
        assert len(trimmed) == 1

    def test_trim_history_empty(self):
        assert _trim_history([]) == []

    def test_build_context_block_contains_pr_title(self):
        ctx = ChatContext(
            review_summary="LGTM",
            findings_text="No issues",
            pr_title="Fix login bug",
            pr_author="alice",
            repo_full_name="org/repo",
        )
        block = _build_context_block(ctx)
        assert "Fix login bug" in block
        assert "alice" in block
        assert "org/repo" in block
        assert "LGTM" in block

    def test_chat_message_roles(self):
        user_msg = ChatMessage(role="user", content="hello")
        asst_msg = ChatMessage(role="assistant", content="hi there")
        assert user_msg.role == "user"
        assert asst_msg.role == "assistant"


# ─── Notification service tests ───────────────────────────────────────────────

class TestNotificationService:
    def test_grade_emoji_excellent(self):
        assert _grade_emoji("A+") == "🌟"
        assert _grade_emoji("A") == "✅"

    def test_grade_emoji_failing(self):
        assert _grade_emoji("F") == "💀"
        assert _grade_emoji("D") == "🔴"

    def test_grade_emoji_unknown_defaults(self):
        result = _grade_emoji("Z")
        assert result == "📊"

    def test_severity_label_no_blockers(self):
        label = _severity_label(0, 5)
        assert "✅" in label
        assert "5" in label
        assert "no blockers" in label.lower()

    def test_severity_label_with_blockers(self):
        label = _severity_label(2, 7)
        assert "🚫" in label
        assert "2" in label

    @pytest.mark.asyncio
    async def test_slack_notification_skips_when_no_url(self):
        """Should return False gracefully when SLACK_WEBHOOK_URL is not set."""
        from app.core.config import settings
        original = settings.SLACK_WEBHOOK_URL
        try:
            settings.SLACK_WEBHOOK_URL = None
            result = await send_slack_notification(
                pr_title="Test PR",
                pr_number=1,
                repo_full_name="org/repo",
                pr_author="alice",
                health_grade="A",
                health_score=92.0,
                total_findings=2,
                blocking_count=0,
            )
            assert result is False
        finally:
            settings.SLACK_WEBHOOK_URL = original

    @pytest.mark.asyncio
    async def test_generic_webhook_handles_connection_error(self):
        """Should return False when webhook URL is unreachable."""
        result = await send_generic_webhook(
            "http://localhost:9999/nonexistent",
            {"event": "test"},
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_slack_notification_posts_payload(self):
        """Mock httpx to verify Slack payload structure."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
            mock_settings.NOTIFICATION_WEBHOOK_URL = None

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await send_slack_notification(
                    pr_title="Add auth",
                    pr_number=42,
                    repo_full_name="org/repo",
                    pr_author="bob",
                    health_grade="B",
                    health_score=83.0,
                    total_findings=3,
                    blocking_count=0,
                )
                assert result is True
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args.kwargs["json"]["blocks"] is not None
