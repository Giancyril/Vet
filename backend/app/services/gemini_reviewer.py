import json
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.github.diff_fetcher import PRContext
from app.schemas.gemini import GeminiReviewResponse
from app.services.prompt_builder import build_review_prompt


def _get_gemini_client() -> genai.Client:
    """Initialises and returns a google-genai Client."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_gemini_response(raw_text: str) -> GeminiReviewResponse:
    """
    Parses raw Gemini response text into a validated GeminiReviewResponse.
    Strips accidental markdown fences if present, then validates with Pydantic.
    """
    text = raw_text.strip()

    # Strip markdown fences if model wraps JSON despite mime_type setting
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}\nRaw output:\n{raw_text[:500]}")
        raise ValueError(f"Gemini returned invalid JSON: {e}") from e

    try:
        return GeminiReviewResponse.model_validate(data)
    except ValidationError as e:
        logger.error(f"Gemini JSON failed schema validation: {e}")
        raise ValueError(f"Gemini response failed schema validation: {e}") from e


async def analyze_pull_request(
    context: PRContext,
    custom_instructions: str = "",
    max_findings: int = 15,
) -> GeminiReviewResponse:
    """
    Sends the PR context to Gemini for analysis and returns structured findings.

    Args:
        context: The PRContext built from the GitHub diff fetcher.
        custom_instructions: Optional per-repo reviewer instructions.
        max_findings: Cap on findings returned (applied post-parse).

    Returns:
        A validated GeminiReviewResponse with summary, verdict, and findings.
    """
    if not context.changed_files:
        logger.info("No reviewable files in PR — returning auto-APPROVE")
        return GeminiReviewResponse(
            summary="No reviewable changed files detected (all changes were in lockfiles or auto-generated code).",
            verdict="APPROVE",
            findings=[],
        )

    prompt = build_review_prompt(context, custom_instructions)
    logger.info(
        f"Sending PR {context.owner}/{context.repo}#{context.pr_number} to Gemini "
        f"({settings.GEMINI_MODEL}) — prompt length: {len(prompt)} chars"
    )

    client = _get_gemini_client()

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )
        raw_text = response.text
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise RuntimeError(f"Gemini API call failed: {e}") from e

    review = _parse_gemini_response(raw_text)

    # Enforce max findings cap — prioritise blocking > suggestion > nitpick
    if len(review.findings) > max_findings:
        logger.info(f"Capping findings from {len(review.findings)} to {max_findings}")
        priority = {"blocking": 0, "suggestion": 1, "nitpick": 2}
        sorted_findings = sorted(review.findings, key=lambda f: priority.get(f.severity, 99))
        review = GeminiReviewResponse(
            summary=review.summary,
            verdict=review.verdict,
            findings=sorted_findings[:max_findings],
        )

    logger.info(
        f"Gemini review complete: verdict={review.verdict}, "
        f"findings={len(review.findings)} "
        f"(blocking={sum(1 for f in review.findings if f.severity == 'blocking')}, "
        f"suggestion={sum(1 for f in review.findings if f.severity == 'suggestion')}, "
        f"nitpick={sum(1 for f in review.findings if f.severity == 'nitpick')})"
    )

    return review
