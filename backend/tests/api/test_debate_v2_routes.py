"""
Tests for Debate V2 API Routes
"""
import pytest
from fastapi.testclient import TestClient


class TestDebateV2Routes:
    """Test suite for debate V2 API endpoints"""

    def test_create_debate(self, client, sample_debate_config):
        """Test POST /api/v1/debates/v2 - Create debate"""
        response = client.post("/api/v1/debates/v2", json=sample_debate_config)

        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("debate_v2_")
        assert data["status"] == "initialized"
        assert data["current_round"] == 1
        assert data["current_turn"] == 0
        assert data["config"]["topic"] == sample_debate_config["topic"]

    def test_create_debate_invalid_config(self, client):
        """Test creating debate with invalid configuration"""
        # Missing required field
        response = client.post("/api/v1/debates/v2", json={
            "topic": "Test",
            "participants": []
        })
        assert response.status_code == 422  # Validation error

    def test_create_debate_too_few_participants(self, client):
        """Test creating debate with too few participants"""
        config = {
            "topic": "Test topic",
            "participants": [
                {"name": "Agent 1", "model": "gpt-4o", "system_prompt": "Test"}
            ],
            "max_rounds": 2
        }
        response = client.post("/api/v1/debates/v2", json=config)
        assert response.status_code == 422  # FastAPI validation error

    def test_create_debate_too_many_rounds(self, client, sample_debate_config):
        """Test creating debate with too many rounds"""
        config = sample_debate_config.copy()
        config["max_rounds"] = 10  # Max is 5
        response = client.post("/api/v1/debates/v2", json=config)
        assert response.status_code == 422

    def test_get_debate(self, client, sample_debate_config):
        """Test GET /api/v1/debates/v2/{debate_id} - Get debate"""
        # Create a debate first
        create_response = client.post("/api/v1/debates/v2", json=sample_debate_config)
        debate_id = create_response.json()["id"]

        # Get the debate
        response = client.get(f"/api/v1/debates/v2/{debate_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == debate_id

    def test_get_nonexistent_debate(self, client):
        """Test getting a debate that doesn't exist"""
        response = client.get("/api/v1/debates/v2/nonexistent_id")
        assert response.status_code == 404

    def test_stop_debate(self, client, sample_debate_config):
        """Test POST /api/v1/debates/v2/{debate_id}/stop - Stop debate"""
        # Create a debate first
        create_response = client.post("/api/v1/debates/v2", json=sample_debate_config)
        debate_id = create_response.json()["id"]

        # Stop the debate
        response = client.post(f"/api/v1/debates/v2/{debate_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["stopped_manually"] is True

    def test_stop_nonexistent_debate(self, client):
        """Test stopping a debate that doesn't exist"""
        response = client.post("/api/v1/debates/v2/nonexistent_id/stop")
        assert response.status_code == 404

    def test_pause_debate(self, client, sample_debate_config):
        """Test POST /api/v1/debates/v2/{debate_id}/pause - Pause debate"""
        # Create a debate first
        create_response = client.post("/api/v1/debates/v2", json=sample_debate_config)
        debate_id = create_response.json()["id"]

        # Pause the debate
        response = client.post(f"/api/v1/debates/v2/{debate_id}/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    def test_resume_debate(self, client, sample_debate_config):
        """Test POST /api/v1/debates/v2/{debate_id}/resume - Resume debate"""
        # Create a debate first
        create_response = client.post("/api/v1/debates/v2", json=sample_debate_config)
        debate_id = create_response.json()["id"]

        # Pause first
        client.post(f"/api/v1/debates/v2/{debate_id}/pause")

        # Resume the debate
        response = client.post(f"/api/v1/debates/v2/{debate_id}/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_resume_non_paused_debate(self, client, sample_debate_config):
        """Test resuming a debate that isn't paused"""
        # Create a debate first
        create_response = client.post("/api/v1/debates/v2", json=sample_debate_config)
        debate_id = create_response.json()["id"]

        # Try to resume without pausing
        response = client.post(f"/api/v1/debates/v2/{debate_id}/resume")
        assert response.status_code == 400

    def test_get_summary(self, client, sample_debate_config):
        """Test GET /api/v1/debates/v2/{debate_id}/summary - Get summary"""
        # Create a debate first
        create_response = client.post("/api/v1/debates/v2", json=sample_debate_config)
        debate_id = create_response.json()["id"]

        # Get summary (even though debate hasn't run)
        response = client.get(f"/api/v1/debates/v2/{debate_id}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["debate_id"] == debate_id
        assert "markdown_transcript" in data

    def test_get_summary_nonexistent_debate(self, client):
        """Test getting summary for nonexistent debate"""
        response = client.get("/api/v1/debates/v2/nonexistent_id/summary")
        assert response.status_code == 404
