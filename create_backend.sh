#!/bin/bash

# LLM Service
cat > backend/app/services/llm_service.py << 'EOF'
import asyncio
from typing import AsyncGenerator, List, Dict, Any
import litellm
from litellm import acompletion
from app.config.settings import settings

# Configure LiteLLM
litellm.set_verbose = settings.debug
litellm.telemetry = settings.litellm_telemetry


class LLMService:
    def __init__(self):
        self.default_model = "gpt-4o"

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        model_to_use = model or self.default_model

        try:
            response = await acompletion(
                model=model_to_use,
                messages=messages,
                stream=True,
                api_key=self._get_api_key(model_to_use),
            )

            async for chunk in response:
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content

        except Exception as e:
            print(f"LLM streaming error: {str(e)}")
            raise

    async def get_completion(
        self,
        messages: List[Dict[str, str]],
        model: str | None = None,
    ) -> str:
        model_to_use = model or self.default_model

        try:
            response = await acompletion(
                model=model_to_use,
                messages=messages,
                stream=False,
                api_key=self._get_api_key(model_to_use),
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"LLM completion error: {str(e)}")
            raise

    def _get_api_key(self, model: str) -> str:
        model_lower = model.lower()

        if "gpt" in model_lower or "openai" in model_lower:
            return settings.openai_api_key
        elif "claude" in model_lower or "anthropic" in model_lower:
            return settings.anthropic_api_key
        elif "gemini" in model_lower or "google" in model_lower:
            return settings.google_api_key
        elif "mistral" in model_lower:
            return settings.mistral_api_key
        else:
            return settings.openai_api_key


llm_service = LLMService()
EOF

# Models
cat > backend/app/models/chat.py << 'EOF'
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
EOF

# Chat routes
cat > backend/app/api/routes/chat.py << 'EOF'
import uuid
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from app.models.chat import ChatCompletionRequest, ChatCompletionResponse, StreamChunk
from app.services.llm_service import llm_service

router = APIRouter()


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    try:
        messages = []
        if request.conversation_history:
            messages.extend([
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ])
        messages.append({"role": "user", "content": request.message})

        response_content = await llm_service.get_completion(
            messages=messages,
            model=request.model,
        )

        return ChatCompletionResponse(
            id=str(uuid.uuid4()),
            content=response_content,
            model=request.model or llm_service.default_model,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def stream_chat_completion(message: str, model: str | None = None):
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            messages = [{"role": "user", "content": message}]
            chunk_id = str(uuid.uuid4())

            async for content_chunk in llm_service.stream_completion(
                messages=messages,
                model=model,
            ):
                chunk = StreamChunk(
                    id=chunk_id,
                    content=content_chunk,
                    done=False,
                )
                yield f"data: {chunk.model_dump_json()}\n\n"

            final_chunk = StreamChunk(
                id=chunk_id,
                content="",
                done=True,
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"

        except Exception as e:
            error_chunk = {
                "id": str(uuid.uuid4()),
                "content": f"Error: {str(e)}",
                "done": True,
                "error": True,
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
EOF

# Health routes
cat > backend/app/api/routes/health.py << 'EOF'
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/")
async def root():
    return {
        "message": "Quorum API",
        "version": "0.1.0",
        "docs": "/docs",
    }
EOF

# Main app
cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.api.routes import chat, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.app_name}")
    print(f"📝 Environment: {settings.environment}")
    print(f"🔐 CORS origins: {settings.cors_origins}")

    if settings.openai_api_key:
        print("✅ OpenAI API key configured")
    if settings.anthropic_api_key:
        print("✅ Anthropic API key configured")

    yield
    print("👋 Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Backend API for Quorum AI Debate Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
EOF

echo "✅ Backend files created successfully"
