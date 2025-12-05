"""
Conversation Quality Management Models
SQLAlchemy 2.0 models for tracking conversation health, contradictions, loops, and citations
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey,
    Index, CheckConstraint, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

from app.config.database import Base


class ContradictionSeverity(str, Enum):
    """Severity levels for contradictions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionStatus(str, Enum):
    """Status of loop intervention"""
    NONE = "none"
    REQUIRED = "required"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class Conversation(Base):
    """
    Main conversation entity for multi-agent discussions.
    Tracks overall conversation health and metadata.
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Health scoring
    current_health_score: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False
    )

    # Status flags
    has_contradictions: Mapped[bool] = mapped_column(Boolean, default=False)
    has_loops: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_intervention: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    quality_metrics: Mapped[List["ConversationQuality"]] = relationship(
        "ConversationQuality",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    contradictions: Mapped[List["Contradiction"]] = relationship(
        "Contradiction",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    loops: Mapped[List["ConversationLoop"]] = relationship(
        "ConversationLoop",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'current_health_score >= 0 AND current_health_score <= 100',
            name='check_health_score_range'
        ),
        Index('idx_conversations_user_created', 'user_id', 'created_at'),
        Index('idx_conversations_health', 'current_health_score'),
        Index('idx_conversations_intervention', 'requires_intervention'),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, health={self.current_health_score})>"


class Message(Base):
    """
    Individual message in a conversation from an agent or user.
    Includes health scoring and citation tracking.
    """
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Message metadata
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50),
        default="agent",
        nullable=False
    )  # 'agent', 'user', 'system'

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Ordering
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turn_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Quality metrics
    health_score: Mapped[float] = mapped_column(
        Float,
        default=100.0,
        nullable=False
    )
    coherence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Citation tracking
    has_citations: Mapped[bool] = mapped_column(Boolean, default=False)
    citations_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    message_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )
    embeddings: Mapped[List["MessageEmbedding"]] = relationship(
        "MessageEmbedding",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    citations: Mapped[List["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'health_score >= 0 AND health_score <= 100',
            name='check_message_health_score_range'
        ),
        CheckConstraint(
            'coherence_score IS NULL OR (coherence_score >= 0 AND coherence_score <= 100)',
            name='check_coherence_score_range'
        ),
        CheckConstraint(
            'relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 100)',
            name='check_relevance_score_range'
        ),
        Index('idx_messages_conversation_sequence', 'conversation_id', 'sequence_number'),
        Index('idx_messages_agent', 'agent_name'),
        Index('idx_messages_health', 'health_score'),
        Index('idx_messages_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, agent={self.agent_name}, seq={self.sequence_number})>"


class MessageEmbedding(Base):
    """
    Vector embeddings for messages to enable semantic similarity search.
    Supports contradiction detection and context retrieval.
    """
    __tablename__ = "message_embeddings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Vector embedding (1536 dimensions for OpenAI ada-002 / text-embedding-3-small)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

    # Embedding metadata
    embedding_model: Mapped[str] = mapped_column(
        String(255),
        default="text-embedding-3-small",
        nullable=False
    )
    embedding_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Text that was embedded (may be summarized/chunked)
    embedded_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="embeddings"
    )

    # Constraints
    __table_args__ = (
        Index('idx_embeddings_message', 'message_id'),
        Index('idx_embeddings_model', 'embedding_model'),
        # HNSW index for vector similarity search (created in migration)
    )

    def __repr__(self):
        return f"<MessageEmbedding(id={self.id}, message_id={self.message_id}, model={self.embedding_model})>"


class ConversationQuality(Base):
    """
    Time-series quality metrics for conversations.
    Tracks health score evolution and component scores.
    """
    __tablename__ = "conversation_quality"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Overall health score (0-100)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Component scores (0-100)
    coherence_score: Mapped[float] = mapped_column(Float, nullable=False)
    contradiction_score: Mapped[float] = mapped_column(Float, nullable=False)
    loop_score: Mapped[float] = mapped_column(Float, nullable=False)
    citation_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Counts
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, default=0)
    loop_count: Mapped[int] = mapped_column(Integer, default=0)

    # Analysis metadata
    analysis_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="quality_metrics"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'health_score >= 0 AND health_score <= 100',
            name='check_quality_health_score_range'
        ),
        CheckConstraint(
            'coherence_score >= 0 AND coherence_score <= 100',
            name='check_quality_coherence_score_range'
        ),
        CheckConstraint(
            'contradiction_score >= 0 AND contradiction_score <= 100',
            name='check_quality_contradiction_score_range'
        ),
        CheckConstraint(
            'loop_score >= 0 AND loop_score <= 100',
            name='check_quality_loop_score_range'
        ),
        CheckConstraint(
            'citation_score >= 0 AND citation_score <= 100',
            name='check_quality_citation_score_range'
        ),
        Index('idx_quality_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_quality_health', 'health_score'),
    )

    def __repr__(self):
        return f"<ConversationQuality(id={self.id}, conversation_id={self.conversation_id}, health={self.health_score})>"


class Contradiction(Base):
    """
    Detected contradictions between messages in a conversation.
    Uses semantic similarity to identify conflicting statements.
    """
    __tablename__ = "contradictions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Messages involved
    message_1_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )
    message_2_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )

    # Contradiction details
    severity: Mapped[str] = mapped_column(
        SQLEnum(ContradictionSeverity),
        default=ContradictionSeverity.MEDIUM,
        nullable=False,
        index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    # Similarity metrics
    semantic_similarity: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    # Extracted contradicting statements
    statement_1: Mapped[str] = mapped_column(Text, nullable=False)
    statement_2: Mapped[str] = mapped_column(Text, nullable=False)

    # Analysis
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    detection_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="contradictions"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'confidence >= 0 AND confidence <= 1',
            name='check_contradiction_confidence_range'
        ),
        CheckConstraint(
            'semantic_similarity >= 0 AND semantic_similarity <= 1',
            name='check_semantic_similarity_range'
        ),
        CheckConstraint(
            'message_1_id != message_2_id',
            name='check_different_messages'
        ),
        Index('idx_contradictions_conversation', 'conversation_id'),
        Index('idx_contradictions_severity', 'severity'),
        Index('idx_contradictions_resolved', 'resolved'),
        Index('idx_contradictions_messages', 'message_1_id', 'message_2_id'),
    )

    def __repr__(self):
        return f"<Contradiction(id={self.id}, severity={self.severity}, confidence={self.confidence})>"


class ConversationLoop(Base):
    """
    Detected repetitive patterns in conversations (loops).
    Tracks when conversations are going in circles.
    """
    __tablename__ = "conversation_loops"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Pattern identification
    pattern_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True
    )  # Hash of the repeating pattern
    pattern_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Loop details
    loop_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Number of messages in pattern
    repetition_count: Mapped[int] = mapped_column(Integer, nullable=False)  # How many times pattern repeated

    # Message range
    first_occurrence_message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )
    last_occurrence_message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )

    # Intervention
    intervention_status: Mapped[str] = mapped_column(
        SQLEnum(InterventionStatus),
        default=InterventionStatus.NONE,
        nullable=False,
        index=True
    )
    intervention_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    detection_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="loops"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'loop_size >= 2',
            name='check_loop_size_minimum'
        ),
        CheckConstraint(
            'repetition_count >= 2',
            name='check_repetition_count_minimum'
        ),
        Index('idx_loops_conversation', 'conversation_id'),
        Index('idx_loops_pattern', 'pattern_hash'),
        Index('idx_loops_intervention', 'intervention_status'),
        Index('idx_loops_detected', 'detected_at'),
    )

    def __repr__(self):
        return f"<ConversationLoop(id={self.id}, size={self.loop_size}, reps={self.repetition_count})>"


class MessageCitation(Base):
    """
    Citations and evidence sources referenced in messages.
    Tracks verification status and source quality.
    """
    __tablename__ = "message_citations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Citation content
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )  # 'web', 'paper', 'book', 'documentation', etc.

    # Position in message
    start_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Verification
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1

    # Quality
    source_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    message_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="citations"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'verification_confidence IS NULL OR (verification_confidence >= 0 AND verification_confidence <= 1)',
            name='check_verification_confidence_range'
        ),
        CheckConstraint(
            'source_quality_score IS NULL OR (source_quality_score >= 0 AND source_quality_score <= 100)',
            name='check_source_quality_range'
        ),
        CheckConstraint(
            'relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 100)',
            name='check_citation_relevance_range'
        ),
        Index('idx_citations_message', 'message_id'),
        Index('idx_citations_verified', 'verified'),
        Index('idx_citations_source_type', 'source_type'),
    )

    def __repr__(self):
        return f"<MessageCitation(id={self.id}, message_id={self.message_id}, verified={self.verified})>"
