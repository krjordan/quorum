"""
Debate Models - Data models for multi-LLM debate orchestration
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DebateFormat(str, Enum):
    """Debate format types"""
    FREE_FORM = "free_form"
    STRUCTURED = "structured"
    ROUND_LIMITED = "round_limited"
    CONVERGENCE = "convergence"


class PersonaConfig(BaseModel):
    """LLM persona configuration"""
    name: str = Field(..., description="Persona name (e.g., 'Optimist', 'Skeptic')")
    role: str = Field(..., description="Role description (e.g., 'Argue for the positive aspects')")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt for this persona")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Optimist",
                "role": "Argue for the positive aspects and potential benefits",
                "system_prompt": "You are an optimistic debater who sees opportunities and silver linings.",
                "temperature": 0.8
            }
        }


class ParticipantConfig(BaseModel):
    """Debate participant configuration"""
    model: str = Field(..., description="LLM model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')")
    persona: PersonaConfig

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-4o",
                "persona": {
                    "name": "Optimist",
                    "role": "Argue for the positive aspects",
                    "temperature": 0.8
                }
            }
        }


class DebateConfig(BaseModel):
    """Configuration for creating a debate"""
    topic: str = Field(..., description="Debate topic or question")
    participants: List[ParticipantConfig] = Field(..., description="2-4 debate participants")
    format: DebateFormat = Field(default=DebateFormat.FREE_FORM, description="Debate format")
    judge_model: str = Field(default="gpt-4o", description="Model to use for judging")
    max_rounds: Optional[int] = Field(default=None, ge=1, le=20, description="Maximum debate rounds (None for unlimited)")
    context_window_rounds: int = Field(default=10, ge=3, le=20, description="Number of rounds to keep in context")
    cost_warning_threshold: float = Field(default=1.0, ge=0.0, description="Cost warning threshold in USD")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Should AI development be open source?",
                "participants": [
                    {
                        "model": "gpt-4o",
                        "persona": {
                            "name": "Open Source Advocate",
                            "role": "Argue for open source AI development"
                        }
                    },
                    {
                        "model": "claude-3-5-sonnet-20241022",
                        "persona": {
                            "name": "Safety Researcher",
                            "role": "Argue for controlled AI development"
                        }
                    }
                ],
                "format": "structured",
                "judge_model": "gpt-4o",
                "max_rounds": 5
            }
        }


class DebaterResponse(BaseModel):
    """Single debater's response in a round"""
    participant_name: str = Field(..., description="Participant persona name")
    model: str = Field(..., description="Model used")
    content: str = Field(..., description="Response content")
    tokens_used: int = Field(..., description="Tokens consumed")
    response_time_ms: float = Field(..., description="Response generation time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now)


class JudgeAssessment(BaseModel):
    """Judge's assessment of a debate round"""
    round_number: int
    rubric_scores: Dict[str, float] = Field(
        ...,
        description="Scores for each rubric dimension (0-10)"
    )
    participant_scores: Dict[str, float] = Field(
        ...,
        description="Overall scores per participant"
    )
    analysis: str = Field(..., description="Judge's analysis of the round")
    should_continue: bool = Field(..., description="Whether debate should continue")
    stopping_reason: Optional[str] = Field(None, description="Reason for stopping if should_continue is False")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "round_number": 1,
                "rubric_scores": {
                    "argumentation": 8.5,
                    "evidence": 7.0,
                    "coherence": 9.0,
                    "engagement": 8.0,
                    "novelty": 6.5,
                    "persuasiveness": 7.5
                },
                "participant_scores": {
                    "Open Source Advocate": 8.0,
                    "Safety Researcher": 7.5
                },
                "analysis": "Both participants presented strong opening arguments...",
                "should_continue": True,
                "stopping_reason": None
            }
        }


class DebateRound(BaseModel):
    """Complete debate round with responses and assessment"""
    round_number: int
    responses: List[DebaterResponse]
    judge_assessment: Optional[JudgeAssessment] = None
    tokens_used: Dict[str, int] = Field(..., description="Tokens per model")
    cost_estimate: float = Field(..., description="Estimated cost in USD")
    timestamp: datetime = Field(default_factory=datetime.now)


class DebateStatus(str, Enum):
    """Debate execution status"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class Debate(BaseModel):
    """Complete debate state"""
    id: str = Field(..., description="Unique debate identifier")
    config: DebateConfig
    status: DebateStatus = Field(default=DebateStatus.INITIALIZED)
    rounds: List[DebateRound] = Field(default_factory=list)
    current_round: int = Field(default=0)
    total_tokens: Dict[str, int] = Field(default_factory=dict, description="Total tokens per model")
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    winner: Optional[str] = Field(None, description="Winner if debate is completed")
    final_verdict: Optional[str] = Field(None, description="Judge's final verdict")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "debate_123456",
                "status": "running",
                "current_round": 2,
                "total_cost": 0.15
            }
        }


class DebateStreamEvent(BaseModel):
    """SSE event for debate streaming"""
    event_type: str = Field(..., description="Event type: round_start, response, judge_assessment, round_end, debate_end, error")
    debate_id: str
    round_number: int
    data: Dict[str, Any] = Field(..., description="Event-specific data")
    timestamp: datetime = Field(default_factory=datetime.now)


class DebateExportFormat(str, Enum):
    """Export format options"""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class DebateExportRequest(BaseModel):
    """Request to export debate"""
    format: DebateExportFormat = Field(default=DebateExportFormat.MARKDOWN)
    include_timestamps: bool = Field(default=True)
    include_metrics: bool = Field(default=True)
