"""Request/response schemas for the PR chatbot API."""
from typing import List
from pydantic import BaseModel, Field

from app.services.chat_service import ChatMessage


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation messages (max 6 kept server-side)"
    )


class ChatResponse(BaseModel):
    reply: str
    history: List[ChatMessage]
