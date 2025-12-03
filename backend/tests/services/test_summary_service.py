"""
Tests for SummaryService
"""
import pytest
from app.services.summary_service import summary_service
from app.services.sequential_debate_service import sequential_debate_service
from app.models.debate_v2 import (
    DebateConfigV2,
    ParticipantConfigV2,
    DebateRoundV2,
    ParticipantResponse
)


class TestSummaryService:
    """Test suite for SummaryService"""

    def test_generate_summary_empty_debate(self, sample_debate_config):
        """Test generating summary for a debate with no rounds"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        summary = summary_service.generate_summary(debate)

        assert summary.debate_id == debate.id
        assert summary.topic == config.topic
        assert summary.rounds_completed == 1  # One empty round created
        assert summary.total_rounds == config.max_rounds
        assert len(summary.participants) == len(config.participants)
        assert summary.total_cost == 0.0
        assert "markdown_transcript" in summary.model_dump()

    def test_generate_summary_with_responses(self, sample_debate_config):
        """Test generating summary with actual responses"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Add a mock response
        response = ParticipantResponse(
            participant_name="Agent 1",
            participant_index=0,
            model="gpt-4o",
            content="This is a test response.",
            tokens_used=100,
            response_time_ms=500.0
        )

        debate.rounds[0].responses.append(response)
        debate.rounds[0].cost_estimate = 0.001
        debate.total_cost = 0.001
        debate.total_tokens["gpt-4o"] = 100

        summary = summary_service.generate_summary(debate)

        assert len(summary.participant_stats) == 2
        assert summary.total_cost == 0.001
        assert "test response" in summary.markdown_transcript.lower()

    def test_calculate_participant_stats(self, sample_debate_config):
        """Test participant statistics calculation"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Add multiple responses
        for i in range(2):
            response = ParticipantResponse(
                participant_name=f"Agent {i + 1}",
                participant_index=i,
                model=config.participants[i].model,
                content=f"Response from agent {i + 1}",
                tokens_used=100,
                response_time_ms=500.0
            )
            debate.rounds[0].responses.append(response)

        debate.total_tokens["gpt-4o"] = 100
        debate.total_tokens["claude-3-5-sonnet-20241022"] = 100
        debate.total_cost = 0.002

        stats = summary_service._calculate_participant_stats(debate)

        assert len(stats) == 2
        assert all(stat.response_count == 1 for stat in stats)
        assert all(stat.total_tokens == 100 for stat in stats)

    def test_generate_markdown_transcript(self, sample_debate_config):
        """Test markdown transcript generation"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Add a response
        response = ParticipantResponse(
            participant_name="Agent 1",
            participant_index=0,
            model="gpt-4o",
            content="Test response content.",
            tokens_used=100,
            response_time_ms=500.0
        )
        debate.rounds[0].responses.append(response)

        markdown = summary_service._generate_markdown_transcript(debate)

        assert "# Debate Transcript" in markdown
        assert config.topic in markdown
        assert "Agent 1" in markdown
        assert "Test response content" in markdown
        assert "Round 1" in markdown

    def test_markdown_formatting(self, sample_debate_config):
        """Test that markdown is properly formatted"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        markdown = summary_service._generate_markdown_transcript(debate)

        # Check for markdown headers
        assert markdown.startswith("# Debate Transcript")
        assert "## Round" in markdown
        assert "## Statistics" in markdown
        assert "### Participant Performance" in markdown

    def test_participant_stats_with_no_responses(self, sample_debate_config):
        """Test participant stats when no responses exist"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        stats = summary_service._calculate_participant_stats(debate)

        assert len(stats) == 2
        assert all(stat.response_count == 0 for stat in stats)
        assert all(stat.total_tokens == 0 for stat in stats)
        assert all(stat.average_response_time_ms == 0.0 for stat in stats)

    def test_cost_distribution(self, sample_debate_config):
        """Test that costs are properly distributed among participants"""
        config = DebateConfigV2(**sample_debate_config)
        debate = sequential_debate_service.create_debate(config)

        # Add responses with different token counts
        response1 = ParticipantResponse(
            participant_name="Agent 1",
            participant_index=0,
            model="gpt-4o",
            content="Short response",
            tokens_used=100,
            response_time_ms=500.0
        )
        response2 = ParticipantResponse(
            participant_name="Agent 2",
            participant_index=1,
            model="claude-3-5-sonnet-20241022",
            content="Much longer response with more tokens",
            tokens_used=300,
            response_time_ms=1000.0
        )

        debate.rounds[0].responses.extend([response1, response2])
        debate.total_tokens["gpt-4o"] = 100
        debate.total_tokens["claude-3-5-sonnet-20241022"] = 300
        debate.total_cost = 0.004

        stats = summary_service._calculate_participant_stats(debate)

        # Agent 2 should have higher cost due to more tokens
        agent1_stats = next(s for s in stats if s.name == "Agent 1")
        agent2_stats = next(s for s in stats if s.name == "Agent 2")

        assert agent2_stats.total_cost > agent1_stats.total_cost
