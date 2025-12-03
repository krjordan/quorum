from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatCompletionRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = None
    model: Optional[str] = None
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    id: str
    content: str
    model: str
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamChunk(BaseModel):
    id: str
    content: str
    done: bool = False
