import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.github.diff_fetcher import PRContext, ChangedFile
from app.schemas.gemini import GeminiReviewResponse, GeminiFinding
from app.services.prompt_builder import build_review_prompt
from app.services.gemini_reviewer import _parse_gemini_response, analyze_pull_request


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_context(**kwargs) -> PRContext:
    defaults = dict(
        owner="Giancyril",
        repo="test-repo",
        pr_number=42,
        head_sha="abc123",
        base_sha="def456",
        pr_title="feat: add JWT auth",
        pr_author="giancyril",
        pr_body="Adds JWT-based authentication flow.",
        changed_files=[
            ChangedFile(
                filename="src/auth.py",
                status="modified",
                patch="@@ -1,3 +1,5 @@\n+import jwt\n+SECRET = \"hard_coded_secret\"",
                full_content="import jwt\nSECRET = \"hard_coded_secret\"\n",
                additions=2,
                deletions=0,
            )
        ],
        total_additions=2,
        total_deletions=0,
    )
    defaults.update(kwargs)
    return PRContext(**defaults)


# ─── Prompt builder tests ─────────────────────────────────────────────────────

def test_build_review_prompt_contains_pr_metadata():
    ctx = _make_context()
    prompt = build_review_prompt(ctx)
    assert "Giancyril/test-repo" in prompt
    assert "feat: add JWT auth" in prompt
    assert "@giancyril" in prompt
    assert "abc123" in prompt


def test_build_review_prompt_contains_diff():
    ctx = _make_context()
    prompt = build_review_prompt(ctx)
    assert "src/auth.py" in prompt
    assert "hard_coded_secret" in prompt
    assert "import jwt" in prompt


def test_build_review_prompt_contains_custom_instructions():
    ctx = _make_context()
    prompt = build_review_prompt(ctx, custom_instructions="Always enforce type hints.")
    assert "Always enforce type hints." in prompt


def test_build_review_prompt_no_files_returns_prompt():
    ctx = _make_context(changed_files=[], total_additions=0, total_deletions=0)
    prompt = build_review_prompt(ctx)
    assert "Changed Files" in prompt


# ─── Gemini parser tests ──────────────────────────────────────────────────────

def test_parse_valid_gemini_json():
    payload = {
        "summary": "Good PR overall.",
        "verdict": "COMMENT",
        "findings": [
            {
                "file_path": "src/auth.py",
                "line_number": 2,
                "side": "RIGHT",
                "severity": "blocking",
                "category": "security",
                "title": "Hardcoded secret",
                "explanation": "Never hardcode secrets in source code.",
                "suggested_fix": "SECRET = os.getenv(\'JWT_SECRET\')",
            }
        ],
    }
    result = _parse_gemini_response(json.dumps(payload))
    assert result.verdict == "COMMENT"
    assert len(result.findings) == 1
    assert result.findings[0].severity == "blocking"
    assert result.findings[0].category == "security"


def test_parse_gemini_json_with_markdown_fence():
    payload = {"summary": "LGTM.", "verdict": "APPROVE", "findings": []}
    raw = f"```json\n{json.dumps(payload)}\n```"
    result = _parse_gemini_response(raw)
    assert result.verdict == "APPROVE"
    assert result.findings == []


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="invalid JSON"):
        _parse_gemini_response("this is not json")


def test_parse_invalid_schema_raises():
    bad_payload = {"summary": "X", "verdict": "UNKNOWN_VERDICT", "findings": []}
    with pytest.raises(ValueError, match="schema validation"):
        _parse_gemini_response(json.dumps(bad_payload))


# ─── analyze_pull_request tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_pull_request_empty_files_returns_approve():
    ctx = _make_context(changed_files=[], total_additions=0, total_deletions=0)
    result = await analyze_pull_request(ctx)
    assert result.verdict == "APPROVE"
    assert result.findings == []


@pytest.mark.asyncio
async def test_analyze_pull_request_calls_gemini_and_returns_findings():
    """
    Integration test for analyze_pull_request.
    Mocks _parse_gemini_response and the Gemini client to avoid real API calls.
    """
    ctx = _make_context()

    expected_review = GeminiReviewResponse(
        summary="Found a hardcoded secret.",
        verdict="REQUEST_CHANGES",
        findings=[
            GeminiFinding(
                file_path="src/auth.py",
                line_number=2,
                side="RIGHT",
                severity="blocking",
                category="security",
                title="Hardcoded secret",
                explanation="JWT secret must come from environment variables.",
                suggested_fix="SECRET = os.getenv(\'JWT_SECRET\')",
            )
        ],
    )

    # Patch at the gemini_reviewer module level to intercept the client call
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="fake-json")

    with patch("app.services.gemini_reviewer._get_gemini_client", return_value=mock_client),          patch("app.services.gemini_reviewer._parse_gemini_response", return_value=expected_review):
        result = await analyze_pull_request(ctx)

    assert result.verdict == "REQUEST_CHANGES"
    assert len(result.findings) == 1
    assert result.findings[0].severity == "blocking"
    assert result.findings[0].category == "security"


@pytest.mark.asyncio
async def test_analyze_pull_request_caps_findings_by_priority():
    ctx = _make_context()

    # Build 15 findings: 5 nitpick + 5 suggestion + 5 blocking
    findings = []
    for i in range(5):
        findings.append(GeminiFinding(
            file_path="src/auth.py", line_number=i + 1,
            side="RIGHT", severity="nitpick", category="style",
            title=f"nitpick {i}", explanation="minor",
        ))
    for i in range(5):
        findings.append(GeminiFinding(
            file_path="src/auth.py", line_number=i + 10,
            side="RIGHT", severity="suggestion", category="performance",
            title=f"suggestion {i}", explanation="improve this",
        ))
    for i in range(5):
        findings.append(GeminiFinding(
            file_path="src/auth.py", line_number=i + 20,
            side="RIGHT", severity="blocking", category="security",
            title=f"blocking {i}", explanation="fix this now",
        ))

    big_review = GeminiReviewResponse(
        summary="Many issues.", verdict="REQUEST_CHANGES", findings=findings
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="fake-json")

    with patch("app.services.gemini_reviewer._get_gemini_client", return_value=mock_client),          patch("app.services.gemini_reviewer._parse_gemini_response", return_value=big_review):
        result = await analyze_pull_request(ctx, max_findings=8)

    assert len(result.findings) == 8
    # First 5 must be blocking (highest priority)
    for f in result.findings[:5]:
        assert f.severity == "blocking"
    # Next 3 must be suggestions
    for f in result.findings[5:]:
        assert f.severity == "suggestion"
