"""
Pytest Fixtures and Configuration for Backend Testing

This module provides shared fixtures for:
- FastAPI test client
- Mock LLM providers (Anthropic, OpenRouter)
- Database fixtures
- SSE streaming mocks
- Authentication fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json
from datetime import datetime, timedelta
import jwt

# FastAPI app fixture
@pytest.fixture
def app():
    """Create FastAPI application instance for testing."""
    from src.main import app
    return app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with SSE support."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing async endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Mock LLM Provider Fixtures
@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API streaming response."""
    def create_response(content: str, chunks: int = 3):
        """Create mock SSE chunks simulating Anthropic streaming."""
        chunk_size = len(content) // chunks
        responses = []

        for i in range(chunks):
            start = i * chunk_size
            end = start + chunk_size if i < chunks - 1 else len(content)
            chunk_content = content[start:end]

            responses.append({
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": chunk_content
                }
            })

        # Add final message_stop event
        responses.append({
            "type": "message_stop"
        })

        return responses

    return create_response


@pytest.fixture
def mock_openrouter_response():
    """Mock OpenRouter API streaming response."""
    def create_response(content: str, chunks: int = 3):
        """Create mock SSE chunks simulating OpenRouter streaming."""
        chunk_size = len(content) // chunks
        responses = []

        for i in range(chunks):
            start = i * chunk_size
            end = start + chunk_size if i < chunks - 1 else len(content)
            chunk_content = content[start:end]

            responses.append({
                "choices": [{
                    "delta": {
                        "content": chunk_content
                    },
                    "index": 0,
                    "finish_reason": None
                }]
            })

        # Add final chunk with finish_reason
        responses.append({
            "choices": [{
                "delta": {},
                "index": 0,
                "finish_reason": "stop"
            }]
        })

        return responses

    return create_response


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without API calls."""
    mock_client = AsyncMock()

    async def mock_stream(*args, **kwargs):
        """Mock streaming response."""
        test_response = "This is a test response from the mock LLM."
        chunks = ["This is ", "a test ", "response ", "from the ", "mock LLM."]

        for chunk in chunks:
            yield {
                "type": "content_block_delta",
                "delta": {"text": chunk}
            }

    mock_client.stream = mock_stream
    return mock_client


# Database Fixtures
@pytest.fixture
async def db_session():
    """Create test database session with automatic rollback."""
    # This will be implemented when database is added
    # For now, return a mock
    mock_db = MagicMock()
    yield mock_db
    # Cleanup/rollback would happen here


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "id": "conv-123",
        "messages": [
            {
                "role": "user",
                "content": "What is the capital of France?",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "role": "assistant",
                "content": "The capital of France is Paris.",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


# SSE Streaming Fixtures
@pytest.fixture
def sse_event_parser():
    """Parser for Server-Sent Events format."""
    def parse_sse(data: str) -> list:
        """Parse SSE stream into events."""
        events = []
        current_event = {}

        for line in data.split('\n'):
            if line.startswith('data: '):
                event_data = line[6:]  # Remove 'data: ' prefix
                if event_data.strip() and event_data != '[DONE]':
                    try:
                        current_event = json.loads(event_data)
                        events.append(current_event)
                    except json.JSONDecodeError:
                        pass
            elif line == '':
                if current_event:
                    current_event = {}

        return events

    return parse_sse


# Authentication Fixtures
@pytest.fixture
def auth_token():
    """Generate valid JWT token for testing."""
    secret_key = "test-secret-key"
    payload = {
        "sub": "test-user-123",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


@pytest.fixture
def auth_headers(auth_token):
    """Generate authentication headers."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# Mock Environment Variables
@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "JWT_SECRET": "test-jwt-secret",
        "DATABASE_URL": "sqlite:///:memory:",
        "ENVIRONMENT": "test"
    }

    with patch.dict('os.environ', env_vars):
        yield env_vars


# Async test setup
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Request/Response Helpers
@pytest.fixture
def sample_chat_request():
    """Sample chat request payload."""
    return {
        "message": "What is quantum computing?",
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "conversation_id": None,
        "stream": True
    }


@pytest.fixture
def sample_system_prompt():
    """Sample system prompt for testing."""
    return "You are a helpful AI assistant specialized in technical topics."


# Cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup resources after each test."""
    yield
    # Add cleanup logic here
    pass
