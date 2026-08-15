from app.github.diff_fetcher import PRContext, ChangedFile


_SYSTEM_PROMPT = """You are an expert senior software engineer performing a thorough code review on a GitHub pull request.

Your responsibilities:
1. Identify real bugs, security vulnerabilities, performance issues, and error-handling gaps.
2. Flag style/readability issues only when they meaningfully affect maintainability.
3. Acknowledge good practices where you see them in your summary.
4. Be concise, specific, and actionable — never vague.

Severity definitions:
- **blocking**: Must be fixed before merging. Bugs, security holes, data loss risks.
- **suggestion**: Should be addressed. Clear improvements, but non-blocking.
- **nitpick**: Minor style/naming/formatting. Optional to fix.

Output rules:
- Return ONLY valid JSON matching the provided schema — no markdown fences, no extra prose.
- Only report findings where you are confident. Do not hallucinate line numbers.
- line_number must refer to the NEW file (right side of diff), matching an actual added/changed line.
- If there are no issues, return an empty findings array with verdict APPROVE.
"""


def _format_changed_file(cf: ChangedFile, index: int) -> str:
    parts = [f"### File {index + 1}: `{cf.filename}` (status: {cf.status})"]

    if cf.patch:
        parts.append("**Unified diff (patch):**")
        parts.append("```diff")
        parts.append(cf.patch)
        parts.append("```")
    else:
        parts.append("*(Binary or empty diff — no patch available)*")

    if cf.full_content:
        # Truncate full content if very long, keeping head and tail for context
        content = cf.full_content
        max_chars = 8_000
        if len(content) > max_chars:
            half = max_chars // 2
            content = (
                content[:half]
                + f"\n\n... [truncated {len(cf.full_content) - max_chars} chars] ...\n\n"
                + content[-half:]
            )
        parts.append("**Full file content (new revision):**")
        parts.append(f"```")
        parts.append(content)
        parts.append("```")

    return "\n".join(parts)


def build_review_prompt(context: PRContext, custom_instructions: str = "") -> str:
    """
    Assembles the full prompt sent to Gemini for code review.
    Includes: PR metadata, per-file diffs, full file contents, and instructions.
    """
    header = f"""## Pull Request Review Request

**Repository:** `{context.owner}/{context.repo}`
**PR #{context.pr_number}:** {context.pr_title}
**Author:** @{context.pr_author}
**Head SHA:** `{context.head_sha}`
**Changed files:** {len(context.changed_files)}
**Total changes:** +{context.total_additions} / -{context.total_deletions} lines
"""

    if context.pr_body and context.pr_body.strip():
        header += f"\n**PR Description:**\n{context.pr_body.strip()}\n"

    files_section = "\n\n---\n\n## Changed Files\n\n"
    files_section += "\n\n".join(
        _format_changed_file(cf, i) for i, cf in enumerate(context.changed_files)
    )

    instructions = "\n\n---\n\n## Review Instructions\n\n"
    instructions += _SYSTEM_PROMPT
    if custom_instructions:
        instructions += f"\n\n**Additional project-specific instructions:**\n{custom_instructions}"

    instructions += """\n\nReturn your response as a single JSON object matching this schema exactly:
{
  "summary": "<markdown string — overall assessment of the PR>",
  "verdict": "APPROVE" | "COMMENT" | "REQUEST_CHANGES",
  "findings": [
    {
      "file_path": "<relative file path>",
      "line_number": <integer — line in the NEW file>,
      "side": "RIGHT",
      "severity": "blocking" | "suggestion" | "nitpick",
      "category": "security" | "logic_bug" | "performance" | "error_handling" | "style" | "test_coverage",
      "title": "<short title>",
      "explanation": "<detailed explanation and why it matters>",
      "suggested_fix": "<code snippet or null>"
    }
  ]
}"""

    return header + files_section + instructions
