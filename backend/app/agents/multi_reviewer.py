"""
Concurrent multi-persona analysis pipeline.
Runs all four specialist agents in parallel, each producing
a focused set of findings for their domain.
"""
import asyncio
import json
from typing import List
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.agents.personas import AgentPersona, ALL_PERSONAS
from app.core.config import settings
from app.core.logging import logger
from app.github.diff_fetcher import PRContext
from app.schemas.gemini import GeminiFinding, GeminiReviewResponse
from app.services.prompt_builder import build_review_prompt


_FINDING_SCHEMA_INLINE = """
Return ONLY a valid JSON object:
{
  "findings": [
    {
      "file_path": "<path>",
      "line_number": <int>,
      "side": "RIGHT",
      "severity": "blocking"|"suggestion"|"nitpick",
      "category": "<category>",
      "title": "<short title>",
      "explanation": "<detailed explanation>",
      "suggested_fix": "<code snippet or null>"
    }
  ]
}
"""


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _build_persona_prompt(persona: AgentPersona, base_prompt: str) -> str:
    return f"""SYSTEM ROLE: {persona.emoji} {persona.name}
{persona.system_prompt}

Focus ONLY on the categories: {", ".join(persona.categories)}.
Severity bias: {persona.severity_bias}. 
DO NOT report issues outside your specialty — leave that to other agents.

---
{base_prompt}
---

{_FINDING_SCHEMA_INLINE}
"""


def _parse_persona_findings(raw: str, persona: AgentPersona) -> List[GeminiFinding]:
    text = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        data = json.loads(text)
        findings = []
        for f in data.get("findings", []):
            # Filter to persona's allowed categories only
            if f.get("category") not in persona.categories:
                continue
            try:
                findings.append(GeminiFinding.model_validate(f))
            except ValidationError:
                continue
        return findings
    except Exception as e:
        logger.warning(f"[{persona.name}] Failed to parse findings: {e}")
        return []


async def _run_single_persona(
    persona: AgentPersona,
    base_prompt: str,
    client: genai.Client,
) -> tuple[AgentPersona, List[GeminiFinding]]:
    prompt = _build_persona_prompt(persona, base_prompt)
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        findings = _parse_persona_findings(response.text, persona)
        logger.info(f"[{persona.emoji} {persona.name}] → {len(findings)} findings")
        return persona, findings
    except Exception as e:
        logger.error(f"[{persona.name}] API error: {e}")
        return persona, []


async def run_multi_agent_analysis(
    context: PRContext,
    custom_instructions: str = "",
) -> dict[str, List[GeminiFinding]]:
    """
    Runs all four personas concurrently and returns their findings per role.
    Returns: {"security": [...], "performance": [...], "style": [...], "testing": [...]}
    """
    if not context.changed_files:
        return {p.role: [] for p in ALL_PERSONAS}

    client = _get_client()
    base_prompt = build_review_prompt(context, custom_instructions)

    tasks = [_run_single_persona(p, base_prompt, client) for p in ALL_PERSONAS]
    results = await asyncio.gather(*tasks)

    return {persona.role: findings for persona, findings in results}
