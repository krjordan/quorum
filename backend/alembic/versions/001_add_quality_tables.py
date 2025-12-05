"""Add conversation quality management tables

Revision ID: 001_quality_tables
Revises:
Create Date: 2024-12-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_quality_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all conversation quality management tables"""

    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('topic', sa.Text(), nullable=True),
        sa.Column('current_health_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('has_contradictions', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_loops', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_intervention', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('current_health_score >= 0 AND current_health_score <= 100', name='check_health_score_range')
    )

    # Create indexes for conversations
    op.create_index('idx_conversations_user_created', 'conversations', ['user_id', 'created_at'])
    op.create_index('idx_conversations_health', 'conversations', ['current_health_score'])
    op.create_index('idx_conversations_intervention', 'conversations', ['requires_intervention'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('agent_model', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='agent'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=True),
        sa.Column('turn_index', sa.Integer(), nullable=True),
        sa.Column('health_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('coherence_score', sa.Float(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('has_citations', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('citations_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('message_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('health_score >= 0 AND health_score <= 100', name='check_message_health_score_range'),
        sa.CheckConstraint('coherence_score IS NULL OR (coherence_score >= 0 AND coherence_score <= 100)', name='check_coherence_score_range'),
        sa.CheckConstraint('relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 100)', name='check_relevance_score_range')
    )

    # Create indexes for messages
    op.create_index('idx_messages_conversation_sequence', 'messages', ['conversation_id', 'sequence_number'])
    op.create_index('idx_messages_agent', 'messages', ['agent_name'])
    op.create_index('idx_messages_health', 'messages', ['health_score'])
    op.create_index('idx_messages_created', 'messages', ['created_at'])
    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])

    # Create message_embeddings table
    op.create_table(
        'message_embeddings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('message_id', sa.String(length=36), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('embedding_model', sa.String(length=255), nullable=False, server_default='text-embedding-3-small'),
        sa.Column('embedding_version', sa.String(length=50), nullable=True),
        sa.Column('embedded_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for message_embeddings
    op.create_index('idx_embeddings_message', 'message_embeddings', ['message_id'])
    op.create_index('idx_embeddings_model', 'message_embeddings', ['embedding_model'])

    # Add pgvector column (using vector type)
    # Note: We use ARRAY initially, then convert to vector type for pgvector operations
    op.execute("""
        ALTER TABLE message_embeddings
        ADD COLUMN embedding_vector vector(1536)
    """)

    # Create HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX idx_embeddings_vector_hnsw
        ON message_embeddings
        USING hnsw (embedding_vector vector_cosine_ops)
    """)

    # Create conversation_quality table
    op.create_table(
        'conversation_quality',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('health_score', sa.Float(), nullable=False),
        sa.Column('coherence_score', sa.Float(), nullable=False),
        sa.Column('contradiction_score', sa.Float(), nullable=False),
        sa.Column('loop_score', sa.Float(), nullable=False),
        sa.Column('citation_score', sa.Float(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('contradiction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('loop_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('analysis_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('health_score >= 0 AND health_score <= 100', name='check_quality_health_score_range'),
        sa.CheckConstraint('coherence_score >= 0 AND coherence_score <= 100', name='check_quality_coherence_score_range'),
        sa.CheckConstraint('contradiction_score >= 0 AND contradiction_score <= 100', name='check_quality_contradiction_score_range'),
        sa.CheckConstraint('loop_score >= 0 AND loop_score <= 100', name='check_quality_loop_score_range'),
        sa.CheckConstraint('citation_score >= 0 AND citation_score <= 100', name='check_quality_citation_score_range')
    )

    # Create indexes for conversation_quality
    op.create_index('idx_quality_conversation_created', 'conversation_quality', ['conversation_id', 'created_at'])
    op.create_index('idx_quality_health', 'conversation_quality', ['health_score'])

    # Create contradictions table
    op.create_table(
        'contradictions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('message_1_id', sa.String(length=36), nullable=False),
        sa.Column('message_2_id', sa.String(length=36), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='contradictionseverity'), nullable=False, server_default='MEDIUM'),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('semantic_similarity', sa.Float(), nullable=False),
        sa.Column('statement_1', sa.Text(), nullable=False),
        sa.Column('statement_2', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('resolution_suggestion', sa.Text(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('detection_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_1_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_2_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_contradiction_confidence_range'),
        sa.CheckConstraint('semantic_similarity >= 0 AND semantic_similarity <= 1', name='check_semantic_similarity_range'),
        sa.CheckConstraint('message_1_id != message_2_id', name='check_different_messages')
    )

    # Create indexes for contradictions
    op.create_index('idx_contradictions_conversation', 'contradictions', ['conversation_id'])
    op.create_index('idx_contradictions_severity', 'contradictions', ['severity'])
    op.create_index('idx_contradictions_resolved', 'contradictions', ['resolved'])
    op.create_index('idx_contradictions_messages', 'contradictions', ['message_1_id', 'message_2_id'])

    # Create conversation_loops table
    op.create_table(
        'conversation_loops',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('pattern_hash', sa.String(length=64), nullable=False),
        sa.Column('pattern_description', sa.Text(), nullable=True),
        sa.Column('loop_size', sa.Integer(), nullable=False),
        sa.Column('repetition_count', sa.Integer(), nullable=False),
        sa.Column('first_occurrence_message_id', sa.String(length=36), nullable=False),
        sa.Column('last_occurrence_message_id', sa.String(length=36), nullable=False),
        sa.Column('intervention_status', sa.Enum('NONE', 'REQUIRED', 'IN_PROGRESS', 'RESOLVED', name='interventionstatus'), nullable=False, server_default='NONE'),
        sa.Column('intervention_message', sa.Text(), nullable=True),
        sa.Column('detection_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['first_occurrence_message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_occurrence_message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('loop_size >= 2', name='check_loop_size_minimum'),
        sa.CheckConstraint('repetition_count >= 2', name='check_repetition_count_minimum')
    )

    # Create indexes for conversation_loops
    op.create_index('idx_loops_conversation', 'conversation_loops', ['conversation_id'])
    op.create_index('idx_loops_pattern', 'conversation_loops', ['pattern_hash'])
    op.create_index('idx_loops_intervention', 'conversation_loops', ['intervention_status'])
    op.create_index('idx_loops_detected', 'conversation_loops', ['detected_at'])

    # Create message_citations table
    op.create_table(
        'message_citations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('message_id', sa.String(length=36), nullable=False),
        sa.Column('citation_text', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=2048), nullable=True),
        sa.Column('source_title', sa.String(length=500), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('start_position', sa.Integer(), nullable=True),
        sa.Column('end_position', sa.Integer(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_method', sa.String(length=100), nullable=True),
        sa.Column('verification_confidence', sa.Float(), nullable=True),
        sa.Column('source_quality_score', sa.Float(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('message_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('verification_confidence IS NULL OR (verification_confidence >= 0 AND verification_confidence <= 1)', name='check_verification_confidence_range'),
        sa.CheckConstraint('source_quality_score IS NULL OR (source_quality_score >= 0 AND source_quality_score <= 100)', name='check_source_quality_range'),
        sa.CheckConstraint('relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 100)', name='check_citation_relevance_range')
    )

    # Create indexes for message_citations
    op.create_index('idx_citations_message', 'message_citations', ['message_id'])
    op.create_index('idx_citations_verified', 'message_citations', ['verified'])
    op.create_index('idx_citations_source_type', 'message_citations', ['source_type'])


def downgrade() -> None:
    """Drop all conversation quality management tables"""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('message_citations')
    op.drop_table('conversation_loops')
    op.drop_table('contradictions')
    op.drop_table('conversation_quality')

    # Drop message_embeddings and its indexes
    op.execute('DROP INDEX IF EXISTS idx_embeddings_vector_hnsw')
    op.drop_table('message_embeddings')

    op.drop_table('messages')
    op.drop_table('conversations')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS interventionstatus')
    op.execute('DROP TYPE IF EXISTS contradictionseverity')

    # Note: We don't drop the vector extension as other parts of the system might use it
