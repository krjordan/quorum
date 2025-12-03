# Quorum Backend Architecture - Phase 1

## Overview
FastAPI-based backend for single-LLM streaming with LiteLLM provider abstraction, supporting SSE (Server-Sent Events) for real-time streaming responses.

## Architecture Stack
- **Framework**: FastAPI 0.104+
- **LLM Integration**: LiteLLM 1.0+
- **Primary Provider**: OpenAI (GPT-4, GPT-3.5-turbo)
- **Streaming Protocol**: Server-Sent Events (SSE)
- **Configuration**: Pydantic Settings with environment variables
- **CORS**: Configured for localhost:3000 (React frontend)

---

## 1. API Endpoint Specifications

### 1.1 Chat Completion Endpoint
```
POST /api/v1/chat/completions
Content-Type: application/json
Accept: text/event-stream
```

**Request Schema:**
```json
{
  "messages": [
    {
      "role": "user" | "assistant" | "system",
      "content": "string"
    }
  ],
  "model": "gpt-4" | "gpt-3.5-turbo",
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": true
}
```

**Response (SSE Stream):**
```
event: message
data: {"delta": "Hello", "finish_reason": null}

event: message
data: {"delta": " world", "finish_reason": null}

event: done
data: {"finish_reason": "stop", "total_tokens": 156}
```

### 1.2 Health Check Endpoint
```
GET /health
Response: {"status": "healthy", "version": "1.0.0"}
```

### 1.3 Models List Endpoint
```
GET /api/v1/models
Response: {
  "models": [
    {"id": "gpt-4", "provider": "openai"},
    {"id": "gpt-3.5-turbo", "provider": "openai"}
  ]
}
```

---

## 2. FastAPI Main Application Structure

### 2.1 Directory Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   └── health.py       # Health/status endpoints
│   │   └── dependencies.py     # Dependency injection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chat.py             # Pydantic models for chat
│   │   └── responses.py        # Response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py      # LiteLLM wrapper
│   │   └── streaming.py        # SSE streaming logic
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Environment config
│   └── utils/
│       ├── __init__.py
│       ├── errors.py           # Error handlers
│       └── logging.py          # Logging setup
├── tests/
│   ├── __init__.py
│   ├── test_chat.py
│   └── test_streaming.py
├── .env.example
├── requirements.txt
└── README.md
```

### 2.2 Main Application (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config.settings import settings
from app.api.routes import chat, health
from app.utils.errors import setup_exception_handlers
from app.utils.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    logger.info("Starting Quorum Backend API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"OpenAI API configured: {bool(settings.OPENAI_API_KEY)}")
    yield
    # Shutdown
    logger.info("Shutting down Quorum Backend API")

# Create FastAPI application
app = FastAPI(
    title="Quorum API",
    description="Multi-LLM Debate Platform Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

---

## 3. LiteLLM Integration Pattern

### 3.1 LLM Service (services/llm_service.py)
```python
from typing import AsyncGenerator, Dict, Any, Optional
import litellm
from litellm import acompletion
import logging

from app.config.settings import settings
from app.models.chat import ChatRequest, ChatMessage

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLMs via LiteLLM"""

    def __init__(self):
        # Configure LiteLLM
        litellm.set_verbose = settings.DEBUG

        # Set API keys
        if settings.OPENAI_API_KEY:
            litellm.openai_key = settings.OPENAI_API_KEY

    async def stream_completion(
        self,
        request: ChatRequest
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion responses

        Args:
            request: ChatRequest with messages and parameters

        Yields:
            Dict containing delta text and metadata
        """
        try:
            # Prepare messages for LiteLLM
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]

            # Call LiteLLM with streaming
            response = await acompletion(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
                timeout=settings.LLM_TIMEOUT,
            )

            # Stream chunks
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield {
                        "delta": chunk.choices[0].delta.content,
                        "finish_reason": chunk.choices[0].finish_reason,
                        "model": chunk.model
                    }

        except litellm.exceptions.Timeout as e:
            logger.error(f"LLM timeout error: {e}")
            raise
        except litellm.exceptions.RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            raise

    async def get_completion(
        self,
        request: ChatRequest
    ) -> Dict[str, Any]:
        """
        Get non-streaming completion

        Args:
            request: ChatRequest with messages and parameters

        Returns:
            Complete response dictionary
        """
        try:
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]

            response = await acompletion(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
                timeout=settings.LLM_TIMEOUT,
            )

            return {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"LLM service error: {e}")
            raise

# Singleton instance
llm_service = LLMService()
```

### 3.2 Model Configuration
```python
# Supported models mapping
SUPPORTED_MODELS = {
    "gpt-4": "openai/gpt-4",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "gpt-4-turbo": "openai/gpt-4-turbo-preview",
}

# Default model fallback
DEFAULT_MODEL = "gpt-3.5-turbo"
```

---

## 4. SSE Streaming Implementation

### 4.1 Streaming Service (services/streaming.py)
```python
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class SSEStreamingService:
    """Service for Server-Sent Events streaming"""

    @staticmethod
    def format_sse(data: dict, event: str = "message") -> str:
        """
        Format data as SSE event

        Args:
            data: Dictionary to send
            event: Event type name

        Returns:
            Formatted SSE string
        """
        json_data = json.dumps(data)
        return f"event: {event}\ndata: {json_data}\n\n"

    @staticmethod
    async def create_stream(
        generator: AsyncGenerator
    ) -> StreamingResponse:
        """
        Create SSE StreamingResponse from async generator

        Args:
            generator: Async generator yielding chat chunks

        Returns:
            StreamingResponse configured for SSE
        """
        async def event_generator():
            try:
                async for chunk in generator:
                    # Send message event
                    yield SSEStreamingService.format_sse(chunk, "message")

                    # Small delay to prevent overwhelming client
                    await asyncio.sleep(0.01)

                # Send completion event
                yield SSEStreamingService.format_sse(
                    {"finish_reason": "stop"},
                    "done"
                )

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                # Send error event
                yield SSEStreamingService.format_sse(
                    {"error": str(e)},
                    "error"
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for nginx
            }
        )

# Singleton instance
sse_service = SSEStreamingService()
```

### 4.2 Chat Route Implementation (api/routes/chat.py)
```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging

from app.models.chat import ChatRequest, ChatResponse
from app.services.llm_service import llm_service
from app.services.streaming import sse_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    Handle chat completion requests with streaming support

    Args:
        request: ChatRequest containing messages and parameters

    Returns:
        StreamingResponse with SSE events or JSON response
    """
    try:
        # Validate model
        if request.model not in ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model: {request.model}"
            )

        # Stream response
        if request.stream:
            generator = llm_service.stream_completion(request)
            return await sse_service.create_stream(generator)

        # Non-streaming response
        else:
            result = await llm_service.get_completion(request)
            return ChatResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models():
    """List available models"""
    return {
        "models": [
            {"id": "gpt-4", "provider": "openai", "streaming": True},
            {"id": "gpt-3.5-turbo", "provider": "openai", "streaming": True},
            {"id": "gpt-4-turbo", "provider": "openai", "streaming": True}
        ]
    }
```

---

## 5. Error Handling and Retry Logic

### 5.1 Error Handlers (utils/errors.py)
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import litellm
import logging

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )

    @app.exception_handler(litellm.exceptions.RateLimitError)
    async def rate_limit_handler(request: Request, exc: litellm.exceptions.RateLimitError):
        logger.warning(f"Rate limit hit: {exc}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )

    @app.exception_handler(litellm.exceptions.Timeout)
    async def timeout_handler(request: Request, exc: litellm.exceptions.Timeout):
        logger.error(f"Request timeout: {exc}")
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timeout. Please try again."}
        )

    @app.exception_handler(litellm.exceptions.AuthenticationError)
    async def auth_error_handler(request: Request, exc: litellm.exceptions.AuthenticationError):
        logger.error(f"Authentication error: {exc}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key or authentication failed."}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
```

### 5.2 Retry Logic with Tenacity
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import litellm

# Retry decorator for rate limits
@retry(
    retry=retry_if_exception_type(litellm.exceptions.RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_llm_with_retry(model, messages, **kwargs):
    """Call LLM with automatic retry on rate limits"""
    return await litellm.acompletion(
        model=model,
        messages=messages,
        **kwargs
    )
```

---

## 6. API Request/Response Schemas

### 6.1 Chat Models (models/chat.py)
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal

class ChatMessage(BaseModel):
    """Single chat message"""
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    """Chat completion request"""
    messages: List[ChatMessage] = Field(..., min_items=1)
    model: str = Field(default="gpt-3.5-turbo")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=4096)
    stream: bool = Field(default=True)

    @validator("messages")
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message is required")
        return v

class ChatResponse(BaseModel):
    """Non-streaming chat response"""
    content: str
    finish_reason: str
    model: str
    usage: dict

class StreamChunk(BaseModel):
    """Single streaming chunk"""
    delta: str
    finish_reason: Optional[str] = None
    model: Optional[str] = None
```

### 6.2 Response Models (models/responses.py)
```python
from pydantic import BaseModel
from typing import List, Optional

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    openai_configured: bool

class ModelInfo(BaseModel):
    """Model information"""
    id: str
    provider: str
    streaming: bool = True

class ModelsResponse(BaseModel):
    """Available models response"""
    models: List[ModelInfo]

class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None
```

---

## 7. Environment Variable Schema

### 7.1 Settings Configuration (config/settings.py)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    VERSION: str = "1.0.0"

    # API Keys
    OPENAI_API_KEY: str

    # LLM Configuration
    LLM_TIMEOUT: int = 60  # seconds
    DEFAULT_MODEL: str = "gpt-3.5-turbo"
    MAX_TOKENS_LIMIT: int = 4096

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

# Create settings instance
settings = Settings()
```

### 7.2 Environment File Template (.env.example)
```bash
# Application
ENVIRONMENT=development
DEBUG=true
VERSION=1.0.0

# API Keys (REQUIRED)
OPENAI_API_KEY=sk-your-openai-key-here

# LLM Configuration
LLM_TIMEOUT=60
DEFAULT_MODEL=gpt-3.5-turbo
MAX_TOKENS_LIMIT=4096

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Server
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
```

---

## 8. CORS Configuration

### 8.1 CORS Middleware Setup
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers to client
)
```

### 8.2 CORS Configuration for Production
```python
# For production, use specific origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://yourdomain.com"
]

# More restrictive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    max_age=3600  # Cache preflight requests
)
```

---

## 9. Dependencies and Requirements

### 9.1 requirements.txt
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
litellm==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
tenacity==8.2.3
python-multipart==0.0.6
```

### 9.2 Development Dependencies (requirements-dev.txt)
```txt
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
black==23.11.0
ruff==0.1.6
mypy==1.7.0
```

---

## 10. Implementation Checklist

### Phase 1 - Core Setup
- [ ] Initialize FastAPI project structure
- [ ] Configure environment variables and settings
- [ ] Setup logging infrastructure
- [ ] Implement CORS middleware
- [ ] Create health check endpoint

### Phase 2 - LiteLLM Integration
- [ ] Install and configure LiteLLM
- [ ] Implement LLMService class
- [ ] Add OpenAI API key configuration
- [ ] Create model validation
- [ ] Test basic completion (non-streaming)

### Phase 3 - SSE Streaming
- [ ] Implement SSEStreamingService
- [ ] Create streaming endpoint
- [ ] Format SSE events properly
- [ ] Handle connection lifecycle
- [ ] Test streaming with frontend

### Phase 4 - Error Handling
- [ ] Setup global exception handlers
- [ ] Implement retry logic with tenacity
- [ ] Add rate limit handling
- [ ] Create error response models
- [ ] Add request validation

### Phase 5 - Testing & Documentation
- [ ] Write unit tests for LLM service
- [ ] Test SSE streaming
- [ ] Test error scenarios
- [ ] Create API documentation
- [ ] Add usage examples

---

## 11. Testing Strategy

### 11.1 Unit Tests
```python
import pytest
from app.services.llm_service import llm_service
from app.models.chat import ChatRequest, ChatMessage

@pytest.mark.asyncio
async def test_stream_completion():
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="Hello")],
        model="gpt-3.5-turbo",
        stream=True
    )

    chunks = []
    async for chunk in llm_service.stream_completion(request):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert "delta" in chunks[0]
```

### 11.2 Integration Tests
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_streaming():
    response = client.post(
        "/api/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Test"}],
            "stream": True
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
```

---

## 12. Performance Considerations

### 12.1 Streaming Optimizations
- Use `asyncio.sleep(0.01)` to prevent client overwhelming
- Disable nginx buffering with `X-Accel-Buffering: no`
- Set proper cache-control headers
- Use connection keep-alive

### 12.2 Connection Management
- Implement timeout handling (60s default)
- Graceful connection close on errors
- Monitor active connections
- Rate limiting per client

### 12.3 Resource Management
- Async/await for non-blocking I/O
- Connection pooling for LiteLLM
- Memory-efficient streaming (yield chunks)
- Proper error cleanup

---

## 13. Security Considerations

### 13.1 API Key Protection
- Never expose API keys in responses
- Use environment variables only
- Rotate keys regularly
- Implement key validation on startup

### 13.2 Input Validation
- Validate all request parameters
- Sanitize message content
- Limit message length
- Prevent prompt injection

### 13.3 Rate Limiting
- Implement per-client rate limits
- Use retry with exponential backoff
- Handle provider rate limits gracefully
- Log excessive usage

---

## 14. Monitoring and Logging

### 14.1 Logging Setup (utils/logging.py)
```python
import logging
import sys

def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log")
        ]
    )

    # Set LiteLLM logging
    litellm_logger = logging.getLogger("litellm")
    litellm_logger.setLevel(logging.WARNING)
```

### 14.2 Key Metrics to Track
- Request count per endpoint
- Average response time
- Token usage per request
- Error rates by type
- Active streaming connections

---

## 15. Deployment Notes

### 15.1 Running the Server
```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 15.2 Docker Support
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Summary

This architecture provides:

✅ **FastAPI** with modern async/await patterns
✅ **LiteLLM** integration for provider abstraction
✅ **SSE streaming** for real-time responses
✅ **Comprehensive error handling** with retries
✅ **Type-safe** Pydantic models
✅ **CORS** configured for React frontend
✅ **Environment-based** configuration
✅ **Production-ready** logging and monitoring
✅ **Extensible** for Phase 2 multi-LLM support

The architecture is designed to be modular, testable, and ready for scaling to multi-LLM coordination in Phase 2.
