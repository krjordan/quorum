"""
Debate V2 Models - Sequential turn-based multi-LLM debate orchestration
Phase 2 implementation without AI judge, sequential turn-taking only.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ParticipantConfigV2(BaseModel):
    """Sequential debate participant configuration (V2)"""
    name: str = Field(..., description="Participant name (e.g., 'Agent 1', 'Optimist')")
    model: str = Field(..., description="LLM model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')")
    system_prompt: str = Field(
        default="You are a thoughtful debate participant. Engage with the topic and other participants' arguments carefully and respectfully.",
        description="Editable system prompt for this participant"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Agent 1",
                "model": "gpt-4o",
                "system_prompt": "You are an optimistic debater who sees opportunities and potential benefits.",
                "temperature": 0.8
            }
        }


class DebateConfigV2(BaseModel):
    """Configuration for creating a sequential debate (V2)"""
    topic: str = Field(..., description="Debate topic or question")
    participants: List[ParticipantConfigV2] = Field(..., description="2-4 debate participants")
    max_rounds: int = Field(..., ge=1, le=5, description="Number of rounds (1-5, REQUIRED)")
    context_window_rounds: int = Field(default=10, ge=3, le=20, description="Number of rounds to keep in context")
    cost_warning_threshold: float = Field(default=1.0, ge=0.0, description="Cost warning threshold in USD")

    @field_validator('participants')
    @classmethod
    def validate_participants(cls, v):
        if len(v) < 2:
            raise ValueError("Must have at least 2 participants")
        if len(v) > 4:
            raise ValueError("Cannot have more than 4 participants")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Should AI development be open source?",
                "participants": [
                    {
                        "name": "Agent 1",
                        "model": "gpt-4o",
                        "system_prompt": "You are an advocate for open source AI development."
                    },
                    {
                        "name": "Agent 2",
                        "model": "claude-3-5-sonnet-20241022",
                        "system_prompt": "You are a proponent of controlled AI development for safety."
                    }
                ],
                "max_rounds": 3
            }
        }


class ParticipantResponse(BaseModel):
    """Single participant's response in a turn"""
    participant_name: str = Field(..., description="Participant name")
    participant_index: int = Field(..., description="Participant index (0-based)")
    model: str = Field(..., description="Model used")
    content: str = Field(..., description="Response content")
    tokens_used: int = Field(..., description="Tokens consumed")
    response_time_ms: float = Field(..., description="Response generation time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now)


class DebateRoundV2(BaseModel):
    """Complete debate round with sequential responses"""
    round_number: int = Field(..., description="Round number (1-based)")
    responses: List[ParticipantResponse] = Field(default_factory=list, description="Sequential responses in this round")
    tokens_used: Dict[str, int] = Field(default_factory=dict, description="Tokens per model")
    cost_estimate: float = Field(..., description="Estimated cost in USD for this round")
    timestamp: datetime = Field(default_factory=datetime.now)


class DebateStatusV2(str, Enum):
    """Debate execution status (V2)"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"  # Manual stop
    COMPLETED = "completed"  # Completed all rounds
    ERROR = "error"


class DebateV2(BaseModel):
    """Sequential debate state (V2)"""
    id: str = Field(..., description="Unique debate identifier")
    config: DebateConfigV2
    status: DebateStatusV2 = Field(default=DebateStatusV2.INITIALIZED)
    rounds: List[DebateRoundV2] = Field(default_factory=list)
    current_round: int = Field(default=1, description="Current round number (1-based)")
    current_turn: int = Field(default=0, description="Current participant index within round (0-based)")
    total_tokens: Dict[str, int] = Field(default_factory=dict, description="Total tokens per model")
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    stopped_manually: bool = Field(default=False, description="Was debate stopped manually?")

    def get_current_participant(self) -> ParticipantConfigV2:
        """Get the current participant based on turn index"""
        return self.config.participants[self.current_turn]

    def advance_turn(self):
        """Advance to next participant's turn"""
        self.current_turn += 1
        if self.current_turn >= len(self.config.participants):
            # Completed all participants in this round, advance round
            self.current_turn = 0
            self.current_round += 1

    def is_round_complete(self) -> bool:
        """Check if all participants in current round have responded"""
        if not self.rounds or len(self.rounds) < self.current_round:
            return False
        current_round_obj = self.rounds[self.current_round - 1]
        return len(current_round_obj.responses) == len(self.config.participants)

    def is_debate_complete(self) -> bool:
        """Check if debate has completed all rounds or was stopped"""
        return (
            self.stopped_manually or
            self.current_round > self.config.max_rounds or
            self.status in [DebateStatusV2.COMPLETED, DebateStatusV2.STOPPED, DebateStatusV2.ERROR]
        )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "debate_v2_123456",
                "status": "running",
                "current_round": 2,
                "current_turn": 1,
                "total_cost": 0.08
            }
        }


class SequentialTurnEventType(str, Enum):
    """Event types for sequential debate streaming"""
    DEBATE_START = "debate_start"
    ROUND_START = "round_start"
    PARTICIPANT_START = "participant_start"
    CHUNK = "chunk"
    PARTICIPANT_COMPLETE = "participant_complete"
    ROUND_COMPLETE = "round_complete"
    DEBATE_COMPLETE = "debate_complete"
    DEBATE_STOPPED = "debate_stopped"
    COST_UPDATE = "cost_update"
    QUALITY_UPDATE = "quality_update"  # Phase 3: Health scores, contradictions, loops
    ERROR = "error"


class SequentialTurnEvent(BaseModel):
    """SSE event for sequential debate streaming"""
    event_type: SequentialTurnEventType = Field(..., description="Event type")
    debate_id: str
    round_number: int = Field(..., description="Current round (1-based)")
    turn_index: int = Field(default=0, description="Current participant index (0-based)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "chunk",
                "debate_id": "debate_v2_123456",
                "round_number": 1,
                "turn_index": 0,
                "data": {
                    "text": "I believe that ",
                    "participant_name": "Agent 1"
                }
            }
        }


class ParticipantStats(BaseModel):
    """Statistics for a single participant"""
    name: str
    model: str
    total_tokens: int
    total_cost: float
    average_response_time_ms: float
    response_count: int


class DebateSummary(BaseModel):
    """Debate summary without AI judge (formatted transcript only)"""
    debate_id: str
    topic: str
    status: DebateStatusV2
    rounds_completed: int
    total_rounds: int
    participants: List[str] = Field(..., description="Participant names")
    participant_stats: List[ParticipantStats] = Field(..., description="Statistics per participant")
    total_tokens: Dict[str, int] = Field(..., description="Total tokens per model")
    total_cost: float
    duration_seconds: float
    markdown_transcript: str = Field(..., description="Formatted markdown transcript of entire debate")
    created_at: datetime
    completed_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "debate_id": "debate_v2_123456",
                "topic": "Should AI development be open source?",
                "status": "completed",
                "rounds_completed": 3,
                "total_rounds": 3,
                "participants": ["Agent 1", "Agent 2"],
                "total_cost": 0.15,
                "duration_seconds": 45.2
            }
        }


class DebateExportFormat(str, Enum):
    """Export format options"""
    JSON = "json"
    MARKDOWN = "markdown"
