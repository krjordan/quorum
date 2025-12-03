"""
Tests for SequentialDebateService
"""
import pytest
from app.services.sequential_debate_service import sequential_debate_service
from app.models.debate_v2 import DebateConfigV2, ParticipantConfigV2, DebateStatusV2


class TestSequentialDebateService:
    """Test suite for SequentialDebateService"""

    def test_create_debate(self, sample_debate_config):
        """Test creating a new debate"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        assert debate.id.startswith("debate_v2_")
        assert debate.status == DebateStatusV2.INITIALIZED
        assert debate.current_round == 1
        assert debate.current_turn == 0
        assert len(debate.rounds) == 1
        assert debate.total_cost == 0.0
        assert debate.config == config

    def test_get_debate(self, sample_debate_config):
        """Test retrieving a debate by ID"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        retrieved = sequential_debate_service.get_debate(debate.id)
        assert retrieved is not None
        assert retrieved.id == debate.id

    def test_get_nonexistent_debate(self):
        """Test retrieving a debate that doesn't exist"""
        result = sequential_debate_service.get_debate("nonexistent_id")
        assert result is None

    def test_stop_debate(self, sample_debate_config):
        """Test manually stopping a debate"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        stopped = sequential_debate_service.stop_debate(debate.id)
        assert stopped.status == DebateStatusV2.STOPPED
        assert stopped.stopped_manually is True

    def test_stop_nonexistent_debate(self):
        """Test stopping a debate that doesn't exist"""
        with pytest.raises(ValueError, match="not found"):
            sequential_debate_service.stop_debate("nonexistent_id")

    def test_pause_debate(self, sample_debate_config):
        """Test pausing a debate"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        paused = sequential_debate_service.pause_debate(debate.id)
        assert paused.status == DebateStatusV2.PAUSED

    def test_resume_debate(self, sample_debate_config):
        """Test resuming a paused debate"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Pause first
        sequential_debate_service.pause_debate(debate.id)

        # Then resume
        resumed = sequential_debate_service.resume_debate(debate.id)
        assert resumed.status == DebateStatusV2.RUNNING

    def test_resume_non_paused_debate(self, sample_debate_config):
        """Test resuming a debate that isn't paused"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        with pytest.raises(ValueError, match="not paused"):
            sequential_debate_service.resume_debate(debate.id)

    def test_get_current_participant(self, sample_debate_config):
        """Test getting the current participant"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        participant = debate.get_current_participant()
        assert participant.name == "Agent 1"
        assert participant.model == "gpt-4o"

    def test_advance_turn(self, sample_debate_config):
        """Test advancing to next participant's turn"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Initial state
        assert debate.current_turn == 0
        assert debate.current_round == 1

        # Advance to agent 2
        debate.advance_turn()
        assert debate.current_turn == 1
        assert debate.current_round == 1

        # Advance to next round (back to agent 1)
        debate.advance_turn()
        assert debate.current_turn == 0
        assert debate.current_round == 2

    def test_is_round_complete(self, sample_debate_config):
        """Test checking if round is complete"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Initially not complete (no responses yet)
        assert debate.is_round_complete() is False

    def test_is_debate_complete(self, sample_debate_config):
        """Test checking if debate is complete"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Initially not complete
        assert debate.is_debate_complete() is False

        # Mark as stopped
        stopped = sequential_debate_service.stop_debate(debate.id)
        assert stopped.is_debate_complete() is True

    def test_participant_config_validation(self):
        """Test participant configuration validation"""
        # Too few participants
        with pytest.raises(ValueError, match="at least 2"):
            DebateConfigV2(
                topic="Test topic",
                participants=[
                    ParticipantConfigV2(name="Agent 1", model="gpt-4o", system_prompt="Test")
                ],
                max_rounds=2
            )

        # Too many participants
        with pytest.raises(ValueError, match="more than 4"):
            DebateConfigV2(
                topic="Test topic",
                participants=[
                    ParticipantConfigV2(name=f"Agent {i}", model="gpt-4o", system_prompt="Test")
                    for i in range(5)
                ],
                max_rounds=2
            )

    def test_max_rounds_validation(self):
        """Test max_rounds validation"""
        # Too few rounds
        with pytest.raises(ValueError):
            DebateConfigV2(
                topic="Test topic",
                participants=[
                    ParticipantConfigV2(name="Agent 1", model="gpt-4o", system_prompt="Test"),
                    ParticipantConfigV2(name="Agent 2", model="gpt-4o", system_prompt="Test")
                ],
                max_rounds=0
            )

        # Too many rounds
        with pytest.raises(ValueError):
            DebateConfigV2(
                topic="Test topic",
                participants=[
                    ParticipantConfigV2(name="Agent 1", model="gpt-4o", system_prompt="Test"),
                    ParticipantConfigV2(name="Agent 2", model="gpt-4o", system_prompt="Test")
                ],
                max_rounds=6
            )
