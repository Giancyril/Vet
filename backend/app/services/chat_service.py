"""
PR Chatbot service — answers developer questions about a specific review.
Maintains short-term conversation context (sliding window of last 6 messages).
"""
from typing import List
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger


class ChatMessage(BaseModel):
    role: str    # "user" | "assistant"
    content: str


class ChatContext(BaseModel):
    review_summary: str
    findings_text: str
    pr_title: str
    pr_author: str
    repo_full_name: str


_SYSTEM_PROMPT = """You are Vet, an expert AI code review assistant embedded in a GitHub PR review workflow.
You have access to a detailed code review report for a specific pull request.
Your job is to help the developer understand the findings, suggest how to fix issues,
explain WHY certain patterns are flagged, and provide code examples.

Rules:
- Stay focused on the PR/code review at hand
- Be concise but technically precise
- When suggesting fixes, provide real code examples
- Use markdown formatting for code blocks
- If a question is outside the PR scope, politely redirect
- Never fabricate file paths or line numbers not in the review
"""

_MAX_HISTORY = 6  # keep last 3 exchanges (6 messages)


def _build_context_block(ctx: ChatContext) -> str:
    return f"""## Pull Request: {ctx.pr_title}
**Repository**: {ctx.repo_full_name}
**Author**: {ctx.pr_author}

### AI Review Summary
{ctx.review_summary}

### Findings
{ctx.findings_text}
"""


def _trim_history(history: List[ChatMessage]) -> List[ChatMessage]:
    if len(history) > _MAX_HISTORY:
        return history[-_MAX_HISTORY:]
    return history


async def chat_with_review(
    user_message: str,
    context: ChatContext,
    history: List[ChatMessage],
) -> tuple[str, List[ChatMessage]]:
    """
    Send a message to the PR chatbot and get a response.

    Returns:
        (assistant_reply, updated_history)
    """
    trimmed = _trim_history(history)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    context_block = _build_context_block(context)

    # Build conversation contents
    contents = []
    # Inject context as the first user turn
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=f"{_SYSTEM_PROMPT}\n\n{context_block}")]
        )
    )
    contents.append(
        types.Content(
            role="model",
            parts=[types.Part(text="Understood. I've reviewed the PR findings and I'm ready to help. What would you like to know?")]
        )
    )

    # Add conversation history
    for msg in trimmed:
        role = "user" if msg.role == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=msg.content)])
        )

    # Add the new user message
    contents.append(
        types.Content(role="user", parts=[types.Part(text=user_message)])
    )

    try:
        import asyncio
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.25,
                max_output_tokens=2048,
            ),
        )
        reply = response.text.strip()
    except Exception as e:
        logger.error(f"Chat service error: {e}")
        reply = "I encountered an error processing your question. Please try again."

    updated_history = trimmed + [
        ChatMessage(role="user", content=user_message),
        ChatMessage(role="assistant", content=reply),
    ]

    return reply, updated_history
