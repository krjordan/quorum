"""
Pytest configuration and fixtures for backend tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_debate_config():
    """Sample debate configuration for testing"""
    return {
        "topic": "Should AI development be open source?",
        "participants": [
            {
                "name": "Agent 1",
                "model": "gpt-4o",
                "system_prompt": "You are an advocate for open source AI.",
                "temperature": 0.7
            },
            {
                "name": "Agent 2",
                "model": "claude-3-5-sonnet-20241022",
                "system_prompt": "You are a proponent of controlled AI development.",
                "temperature": 0.7
            }
        ],
        "max_rounds": 2,
        "context_window_rounds": 10,
        "cost_warning_threshold": 1.0
    }


@pytest.fixture
def sample_participant_config():
    """Sample participant configuration"""
    return {
        "name": "Test Agent",
        "model": "gpt-4o",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7
    }
