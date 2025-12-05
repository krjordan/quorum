"""
Quality Monitoring Schemas - Pydantic models for conversation quality management
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ContradictionSeverity(str, Enum):
    """Severity levels for detected contradictions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionStatus(str, Enum):
    """Status of contradiction resolution"""
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class LoopType(str, Enum):
    """Types of conversational loops"""
    REPETITIVE_ARGUMENT = "repetitive_argument"
    CIRCULAR_REASONING = "circular_reasoning"
    REDUNDANT_POINTS = "redundant_points"
    STUCK_TOPIC = "stuck_topic"


class QualityEventType(str, Enum):
    """Quality-related SSE event types"""
    CONTRADICTION_DETECTED = "contradiction_detected"
    LOOP_DETECTED = "loop_detected"
    HEALTH_SCORE_UPDATE = "health_score_update"
    CITATION_MISSING = "citation_missing"
    QUALITY_ALERT = "quality_alert"


# Response Models

class ContradictionResponse(BaseModel):
    """Contradiction detection response"""
    id: str = Field(..., description="Unique contradiction identifier")
    conversation_id: str = Field(..., description="Debate/conversation ID")
    statement_1: str = Field(..., description="First contradicting statement")
    statement_2: str = Field(..., description="Second contradicting statement")
    participant_1: str = Field(..., description="Participant who made first statement")
    participant_2: str = Field(..., description="Participant who made second statement")
    round_1: int = Field(..., description="Round number of first statement")
    round_2: int = Field(..., description="Round number of second statement")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Semantic similarity score (0-1)")
    severity: ContradictionSeverity = Field(..., description="Contradiction severity")
    status: ContradictionStatus = Field(default=ContradictionStatus.DETECTED)
    explanation: str = Field(..., description="AI-generated explanation of the contradiction")
    detected_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "contradiction_abc123",
                "conversation_id": "debate_v2_123456",
                "statement_1": "AI should be completely open source",
                "statement_2": "We need strict proprietary controls on AI development",
                "participant_1": "Agent 1",
                "participant_2": "Agent 1",
                "round_1": 1,
                "round_2": 3,
                "similarity_score": 0.89,
                "severity": "high",
                "status": "detected",
                "explanation": "Agent 1 contradicted their initial position on open source AI"
            }
        }


class ConversationLoopResponse(BaseModel):
    """Detected conversational loop response"""
    id: str = Field(..., description="Unique loop identifier")
    conversation_id: str = Field(..., description="Debate/conversation ID")
    loop_type: LoopType = Field(..., description="Type of loop detected")
    start_round: int = Field(..., description="Round where loop started")
    end_round: int = Field(..., description="Round where loop was detected")
    repetition_count: int = Field(..., description="Number of repetitions detected")
    participants_involved: List[str] = Field(..., description="Participants involved in loop")
    pattern_summary: str = Field(..., description="Summary of the repetitive pattern")
    detected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "loop_xyz789",
                "conversation_id": "debate_v2_123456",
                "loop_type": "repetitive_argument",
                "start_round": 2,
                "end_round": 4,
                "repetition_count": 3,
                "participants_involved": ["Agent 1", "Agent 2"],
                "pattern_summary": "Both agents repeatedly stating the same arguments without new evidence"
            }
        }


class HealthScoreBreakdown(BaseModel):
    """Detailed breakdown of health score components"""
    coherence: float = Field(..., ge=0.0, le=100.0, description="Logical coherence score")
    diversity: float = Field(..., ge=0.0, le=100.0, description="Argument diversity score")
    engagement: float = Field(..., ge=0.0, le=100.0, description="Participant engagement score")
    evidence_quality: float = Field(..., ge=0.0, le=100.0, description="Citation and evidence quality")
    progression: float = Field(..., ge=0.0, le=100.0, description="Conversation progression score")


class ConversationQualityResponse(BaseModel):
    """Overall conversation quality metrics"""
    conversation_id: str = Field(..., description="Debate/conversation ID")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall health score (0-100)")
    score_breakdown: HealthScoreBreakdown = Field(..., description="Detailed score breakdown")
    contradictions_count: int = Field(..., description="Number of contradictions detected")
    loops_detected: int = Field(..., description="Number of loops detected")
    total_citations: int = Field(..., description="Total number of citations provided")
    missing_citations: int = Field(..., description="Number of claims missing citations")
    rounds_analyzed: int = Field(..., description="Number of rounds analyzed")
    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "debate_v2_123456",
                "overall_score": 78.5,
                "score_breakdown": {
                    "coherence": 85.0,
                    "diversity": 72.0,
                    "engagement": 90.0,
                    "evidence_quality": 65.0,
                    "progression": 80.0
                },
                "contradictions_count": 2,
                "loops_detected": 1,
                "total_citations": 15,
                "missing_citations": 8,
                "rounds_analyzed": 3
            }
        }


# Request Models

class ContradictionResolution(BaseModel):
    """Request body for resolving a contradiction"""
    resolution_note: str = Field(..., description="Note explaining how contradiction was resolved")
    new_status: ContradictionStatus = Field(..., description="New contradiction status")

    class Config:
        json_schema_extra = {
            "example": {
                "resolution_note": "Participant clarified their position evolved based on new evidence",
                "new_status": "resolved"
            }
        }


# SSE Event Models

class QualityEventData(BaseModel):
    """Base data for quality events"""
    message: str = Field(..., description="Human-readable message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event details")


class ContradictionEventData(QualityEventData):
    """Data for contradiction_detected events"""
    contradiction: ContradictionResponse = Field(..., description="Full contradiction details")


class LoopEventData(QualityEventData):
    """Data for loop_detected events"""
    loop: ConversationLoopResponse = Field(..., description="Full loop details")


class HealthScoreEventData(QualityEventData):
    """Data for health_score_update events"""
    quality_metrics: ConversationQualityResponse = Field(..., description="Updated quality metrics")


class QualityEvent(BaseModel):
    """SSE event for quality monitoring"""
    event_type: QualityEventType = Field(..., description="Quality event type")
    conversation_id: str = Field(..., description="Debate/conversation ID")
    round_number: int = Field(..., description="Current round number")
    data: Dict[str, Any] = Field(..., description="Event-specific data")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "contradiction_detected",
                "conversation_id": "debate_v2_123456",
                "round_number": 3,
                "data": {
                    "message": "Contradiction detected in Agent 1's statements",
                    "contradiction": {
                        "id": "contradiction_abc123",
                        "severity": "high",
                        "statement_1": "AI should be open source",
                        "statement_2": "AI needs proprietary controls"
                    }
                }
            }
        }


# List Response Models

class ContradictionListResponse(BaseModel):
    """List of contradictions with pagination info"""
    conversation_id: str
    contradictions: List[ContradictionResponse]
    total_count: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class LoopListResponse(BaseModel):
    """List of loops with pagination info"""
    conversation_id: str
    loops: List[ConversationLoopResponse]
    total_count: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
