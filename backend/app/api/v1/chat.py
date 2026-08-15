"""
PR Chatbot API router.
POST /api/v1/reviews/{review_id}/chat
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.finding import ReviewFinding
from app.models.review import PullRequestReview
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatContext, chat_with_review

router = APIRouter()


@router.post(
    "/reviews/{review_id}/chat",
    response_model=ChatResponse,
    summary="Chat with the AI about a PR review",
)
async def chat_about_review(
    review_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask the AI questions about a specific PR review.
    Maintains conversation history (client sends back history each turn).
    """
    # Fetch review
    stmt = select(PullRequestReview).where(PullRequestReview.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Fetch findings for context
    findings_stmt = select(ReviewFinding).where(ReviewFinding.review_id == review_id)
    findings_result = await db.execute(findings_stmt)
    findings = findings_result.scalars().all()

    # Build findings text
    if findings:
        findings_lines = []
        for f in findings:
            findings_lines.append(
                f"- [{f.severity.upper()}] {f.file_path}:{f.line_number} — **{f.title}**: {f.explanation}"
            )
        findings_text = "\n".join(findings_lines)
    else:
        findings_text = "No specific findings — the PR looks clean!"

    # Get repo full name from review
    repo_full_name = "unknown/repo"
    if review.repository_id:
        from app.models.repository import Repository
        repo_stmt = select(Repository).where(Repository.id == review.repository_id)
        repo_res = await db.execute(repo_stmt)
        repo = repo_res.scalar_one_or_none()
        if repo:
            repo_full_name = repo.full_name

    context = ChatContext(
        review_summary=review.summary_markdown,
        findings_text=findings_text,
        pr_title=review.pr_title,
        pr_author=review.pr_author,
        repo_full_name=repo_full_name,
    )

    reply, updated_history = await chat_with_review(
        user_message=request.message,
        context=context,
        history=request.history,
    )

    return ChatResponse(reply=reply, history=updated_history)
