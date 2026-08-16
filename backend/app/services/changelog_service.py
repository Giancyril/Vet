"""
Gemini-Powered Semantic PR Changelog & Release Note Generator.

Generates:
  - Conventional Commits formatted changelog entries
  - Customer-facing release notes (user-friendly prose)
  - Technical migration guide for breaking changes
  - Executive summary (1-paragraph)
"""
import asyncio
from dataclasses import dataclass
from typing import Optional, List
from google import genai
from app.core.config import settings
from app.core.logging import logger


@dataclass
class ChangelogResult:
    conventional_commits: str      # feat/fix/refactor/breaking entries
    release_notes: str             # Customer-facing prose
    migration_guide: str           # Technical migration steps
    executive_summary: str         # 1-paragraph executive brief
    version_bump: str              # "major" | "minor" | "patch"


_CHANGELOG_SYSTEM_PROMPT = """You are a technical writer and software release engineer.
Given a PR title, description, and unified diff, you produce a complete release changelog.

Output EXACTLY this JSON structure (no markdown wrapper):
{
  "conventional_commits": "\n-separated conventional commit lines (feat:, fix:, refactor:, breaking:)",
  "release_notes": "A polished 2-4 paragraph user-facing release note (no jargon)",
  "migration_guide": "Step-by-step technical migration guide (empty string if no breaking changes)",
  "executive_summary": "One tight paragraph executive summary of business impact",
  "version_bump": "major|minor|patch"
}
"""


async def generate_changelog(
    pr_title: str,
    pr_description: str,
    diff_summary: str,
    findings_summary: Optional[str] = None,
) -> ChangelogResult:
    """
    Use Gemini to generate a comprehensive PR changelog and release notes.
    """
    client = genai.Client(api_key=settings.gemini_api_key)

    user_content = f"""PR Title: {pr_title}

PR Description:
{pr_description or "(no description provided)"}

Diff Summary:
{diff_summary[:4000]}

{f"Review Findings Summary: {findings_summary}" if findings_summary else ""}

Generate the full changelog JSON now."""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_model,
            contents=[
                {"role": "user", "parts": [{"text": _CHANGELOG_SYSTEM_PROMPT}]},
                {"role": "model", "parts": [{"text": "Understood. I will output valid JSON only."}]},
                {"role": "user", "parts": [{"text": user_content}]},
            ],
        )

        import json, re
        text = response.text or ""
        # Strip markdown fences if present
        text = re.sub(r"```json\s*|```\s*", "", text).strip()
        data = json.loads(text)

        return ChangelogResult(
            conventional_commits=data.get("conventional_commits", ""),
            release_notes=data.get("release_notes", ""),
            migration_guide=data.get("migration_guide", ""),
            executive_summary=data.get("executive_summary", ""),
            version_bump=data.get("version_bump", "patch"),
        )

    except Exception as e:
        logger.error(f"[changelog] Generation failed: {e}")
        return ChangelogResult(
            conventional_commits=f"- feat: {pr_title}",
            release_notes=pr_description or pr_title,
            migration_guide="",
            executive_summary=pr_title,
            version_bump="patch",
        )
