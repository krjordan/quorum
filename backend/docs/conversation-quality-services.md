# Conversation Quality Management Services

## Overview

The conversation quality management system provides real-time detection and intervention for multi-agent conversations. It includes four core services that work together to ensure high-quality discussions.

## Services

### 1. Embedding Service (`embedding_service.py`)

Generates and manages text embeddings for semantic similarity analysis.

**Key Features:**
- OpenAI text-embedding-3-small model (1536 dimensions)
- Batch processing for efficiency
- PostgreSQL + pgvector storage
- Cosine similarity search

**Usage:**

```python
from app.services import embedding_service

# Generate single embedding
embedding = await embedding_service.generate_embedding(
    text="Agent response text",
    model="text-embedding-3-small"  # optional
)

# Batch generate embeddings
embeddings = await embedding_service.batch_generate_embeddings(
    texts=["message 1", "message 2", "message 3"]
)

# Store embedding
await embedding_service.store_embedding(
    db=db_session,
    message_id="msg_123",
    embedding=embedding,
    metadata={"conversation_id": "conv_456", "agent_name": "Agent1"}
)

# Find similar messages
similar = await embedding_service.find_similar_messages(
    db=db_session,
    conversation_id="conv_456",
    query_embedding=embedding,
    threshold=0.85,  # cosine similarity threshold
    limit=10
)
# Returns: [(message_id, similarity_score), ...]
```

### 2. Contradiction Detection Service (`contradiction_service.py`)

Identifies conflicting statements using semantic similarity and LLM analysis.

**Key Features:**
- Semantic similarity detection (threshold: 0.85)
- LLM-based sentiment opposition checking
- Automatic severity classification (high/medium/low)
- Database storage with explanations

**Usage:**

```python
from app.services import contradiction_service

# Detect contradictions for new message
contradictions = await contradiction_service.detect_contradictions(
    db=db_session,
    conversation_id="conv_456",
    new_message={
        "id": "msg_789",
        "content": "The data shows a positive trend",
        "agent_name": "Agent2"
    }
)

# Each contradiction includes:
for c in contradictions:
    print(f"Severity: {c.severity}")  # high/medium/low
    print(f"Score: {c.similarity_score}")
    print(f"Explanation: {c.explanation}")
    print(f"Messages: {c.message_id1} vs {c.message_id2}")

# Check sentiment opposition manually
is_opposite = await contradiction_service.check_sentiment_opposition(
    message1="The economy is improving",
    message2="The economy is declining"
)
# Returns: True
```

**Severity Classification:**
- **High**: Similarity ≥ 0.9 OR strong contradiction indicators
- **Medium**: Similarity 0.85-0.9
- **Low**: Similarity < 0.85

### 3. Loop Detection Service (`loop_detection_service.py`)

Detects repetitive conversation patterns and generates interventions.

**Key Features:**
- Agent sequence pattern matching
- SHA256 pattern fingerprinting
- Automatic intervention text generation
- Configurable repetition thresholds

**Usage:**

```python
from app.services import loop_detection_service

# Detect loops in conversation
loop = await loop_detection_service.detect_loops(
    db=db_session,
    conversation_id="conv_456",
    recent_messages=[
        {"id": "msg_1", "agent_name": "Agent1", "content": "..."},
        {"id": "msg_2", "agent_name": "Agent2", "content": "..."},
        # ... more messages
    ]
)

if loop:
    print(f"Pattern: {loop.pattern}")  # e.g., "Agent1 -> Agent2 -> Agent3"
    print(f"Repetitions: {loop.repetition_count}")
    print(f"Intervention: {loop.intervention_text}")
    print(f"Messages involved: {loop.message_ids}")

# Create pattern fingerprint
fingerprint = loop_detection_service.create_pattern_fingerprint(messages)
# Returns: SHA256 hash string
```

**Configuration:**
```python
# Adjust detection thresholds
loop_detection_service.min_pattern_length = 2  # Minimum messages in pattern
loop_detection_service.min_repetitions = 2     # Minimum repetitions to trigger
loop_detection_service.lookback_window = 20    # Messages to analyze
```

### 4. Health Scoring Service (`health_scoring_service.py`)

Calculates real-time conversation quality metrics.

**Key Features:**
- Composite score (0-100): coherence (40%) + progress (30%) + productivity (30%)
- Status assessment (excellent/good/fair/poor)
- Detailed metric breakdowns
- Database tracking

**Usage:**

```python
from app.services import health_scoring_service

# Calculate health score
health_score = await health_scoring_service.calculate_health_score(
    db=db_session,
    conversation_id="conv_456",
    recent_messages=[
        {
            "id": "msg_1",
            "content": "...",
            "agent_name": "Agent1",
            "timestamp": datetime.now()
        },
        # ... more messages
    ]
)

# Access scores
print(f"Overall: {health_score.overall_score}")      # 0-100
print(f"Coherence: {health_score.coherence_score}")  # 0-100
print(f"Progress: {health_score.progress_score}")    # 0-100
print(f"Productivity: {health_score.productivity_score}")  # 0-100
print(f"Status: {health_score.status}")  # excellent/good/fair/poor

# Access detailed metrics
print(health_score.details)
# {
#   "message_count": 15,
#   "unique_agents": 3,
#   "weights": {"coherence": 0.4, "progress": 0.3, "productivity": 0.3}
# }
```

**Score Thresholds:**
- **Excellent**: 85-100
- **Good**: 70-84
- **Fair**: 50-69
- **Poor**: 0-49

## Configuration

### Environment Variables

Add to `/Users/ryanjordan/Projects/quorum/backend/.env`:

```bash
# Required: OpenAI API Key for embeddings
OPENAI_API_KEY=sk-...

# Optional: Override default embedding model
# EMBEDDING_MODEL=text-embedding-3-small

# Optional: API keys for LLM services (for contradiction/loop detection)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...
```

### Database Setup

1. **Install PostgreSQL with pgvector:**

```bash
# macOS
brew install postgresql pgvector

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install postgresql-14-pgvector
```

2. **Run migrations:**

```bash
cd /Users/ryanjordan/Projects/quorum/backend

# Generate migration
alembic upgrade head

# Verify pgvector extension
psql -d your_database -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

3. **Verify tables:**

```bash
psql -d your_database -c "\dt"
# Should show: messages, message_embeddings, contradictions, conversation_loops, health_scores
```

## Database Schema

### `messages`
- `message_id` (PK): Unique message identifier
- `conversation_id`: Conversation identifier
- `agent_name`: Agent name
- `content`: Message text
- `timestamp`: Message timestamp
- `created_at`, `updated_at`: Audit fields

### `message_embeddings`
- `id` (PK): Auto-increment ID
- `message_id` (FK): References messages
- `conversation_id`: For filtering
- `agent_name`: Agent name
- `embedding`: vector(1536) - pgvector type
- `created_at`, `updated_at`: Audit fields

**Indexes:**
- `idx_message_embeddings_vector`: IVFFlat index for fast similarity search

### `contradictions`
- `id` (PK): Auto-increment ID
- `conversation_id`: Conversation identifier
- `message_id1`, `message_id2` (FK): Contradicting messages
- `similarity_score`: Cosine similarity (0-1)
- `severity`: high/medium/low
- `explanation`: LLM-generated explanation
- `detected_at`: Detection timestamp
- `resolved`, `resolved_at`: Resolution tracking

**Indexes:**
- `idx_contradictions_conversation_severity`: (conversation_id, severity)

### `conversation_loops`
- `id` (PK): Auto-increment ID
- `conversation_id`: Conversation identifier
- `pattern`: Agent sequence pattern
- `pattern_fingerprint`: SHA256 hash
- `message_ids`: Array of message IDs
- `repetition_count`: Number of repetitions
- `agents_involved`: Array of agent names
- `intervention_text`: Generated intervention
- `detected_at`: Detection timestamp
- `intervention_applied`, `intervention_applied_at`: Intervention tracking

**Indexes:**
- `idx_loops_conversation_detected`: (conversation_id, detected_at)

### `health_scores`
- `id` (PK): Auto-increment ID
- `conversation_id`: Conversation identifier
- `overall_score`: Composite score (0-100)
- `coherence_score`: Coherence metric (0-100)
- `progress_score`: Progress metric (0-100)
- `productivity_score`: Productivity metric (0-100)
- `status`: excellent/good/fair/poor
- `details`: JSONB with additional metadata
- `calculated_at`: Calculation timestamp

**Indexes:**
- `idx_health_scores_conversation_calculated`: (conversation_id, calculated_at)

## Integration Examples

### FastAPI Endpoint Example

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import (
    embedding_service,
    contradiction_service,
    loop_detection_service,
    health_scoring_service
)
from app.database import get_db

router = APIRouter()

@router.post("/conversations/{conversation_id}/analyze")
async def analyze_conversation(
    conversation_id: str,
    new_message: dict,
    db: AsyncSession = Depends(get_db)
):
    """Analyze conversation quality for new message"""

    # 1. Detect contradictions
    contradictions = await contradiction_service.detect_contradictions(
        db=db,
        conversation_id=conversation_id,
        new_message=new_message
    )

    # 2. Get recent messages for loop detection
    recent_messages = await get_recent_messages(db, conversation_id, limit=20)

    # 3. Detect loops
    loop = await loop_detection_service.detect_loops(
        db=db,
        conversation_id=conversation_id,
        recent_messages=recent_messages
    )

    # 4. Calculate health score
    health_score = await health_scoring_service.calculate_health_score(
        db=db,
        conversation_id=conversation_id,
        recent_messages=recent_messages
    )

    return {
        "contradictions": [c.to_dict() for c in contradictions],
        "loop": loop.to_dict() if loop else None,
        "health_score": health_score.to_dict()
    }
```

### SSE Streaming Example

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

@router.get("/conversations/{conversation_id}/stream")
async def stream_quality_updates(conversation_id: str):
    """Stream real-time quality updates"""

    async def event_generator():
        while True:
            # Calculate health score
            health_score = await health_scoring_service.calculate_health_score(
                db=db,
                conversation_id=conversation_id,
                recent_messages=await get_recent_messages(db, conversation_id)
            )

            # Send SSE event
            yield f"event: health_update\n"
            yield f"data: {json.dumps(health_score.to_dict())}\n\n"

            await asyncio.sleep(5)  # Update every 5 seconds

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Performance Optimization

### Embedding Caching

```python
# Use batch processing for multiple messages
texts = [msg["content"] for msg in messages]
embeddings = await embedding_service.batch_generate_embeddings(texts)

# Store all at once
for msg, emb in zip(messages, embeddings):
    await embedding_service.store_embedding(
        db=db,
        message_id=msg["id"],
        embedding=emb,
        metadata={"conversation_id": conversation_id}
    )
```

### pgvector Index Tuning

```sql
-- Adjust IVFFlat lists parameter based on data size
-- Rule of thumb: lists = sqrt(total_rows)
CREATE INDEX idx_message_embeddings_vector
ON message_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);  -- Increase for larger datasets

-- Monitor query performance
EXPLAIN ANALYZE
SELECT message_id, 1 - (embedding <=> '[...]'::vector) / 2 AS similarity
FROM message_embeddings
WHERE conversation_id = 'conv_456'
ORDER BY embedding <=> '[...]'::vector
LIMIT 10;
```

## Testing

### Unit Tests

```python
import pytest
from app.services import embedding_service

@pytest.mark.asyncio
async def test_generate_embedding():
    embedding = await embedding_service.generate_embedding("Test text")
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.asyncio
async def test_detect_contradictions(db_session):
    contradictions = await contradiction_service.detect_contradictions(
        db=db_session,
        conversation_id="test_conv",
        new_message={
            "id": "msg_1",
            "content": "The sky is blue",
            "agent_name": "Agent1"
        }
    )
    assert isinstance(contradictions, list)
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_quality_pipeline(db_session):
    """Test complete quality analysis pipeline"""

    # Create conversation
    messages = [
        {"id": "msg_1", "content": "Initial argument", "agent_name": "A1"},
        {"id": "msg_2", "content": "Counter argument", "agent_name": "A2"},
        # ... more messages
    ]

    # Run full analysis
    contradictions = await contradiction_service.detect_contradictions(...)
    loop = await loop_detection_service.detect_loops(...)
    health = await health_scoring_service.calculate_health_score(...)

    # Verify results
    assert health.overall_score > 0
    assert isinstance(contradictions, list)
```

## Monitoring and Logging

All services use Python's `logging` module with detailed debug output:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Service-specific loggers
logger = logging.getLogger("app.services.embedding_service")
logger.setLevel(logging.DEBUG)
```

## Error Handling

All services follow consistent error handling:

- **OpenAI API errors**: Logged and re-raised
- **Database errors**: Logged, rolled back, re-raised
- **LLM errors**: Logged with fallback defaults
- **Invalid input**: Validated with clear error messages

## Troubleshooting

### Common Issues

1. **"No module named 'pgvector'"**
   ```bash
   pip install pgvector
   ```

2. **"Extension 'vector' does not exist"**
   ```bash
   psql -d your_database -c "CREATE EXTENSION vector;"
   ```

3. **"OpenAI API key not found"**
   - Add `OPENAI_API_KEY` to `.env` file
   - Restart backend service

4. **Slow similarity searches**
   - Increase `lists` parameter in IVFFlat index
   - Consider upgrading to HNSW index for PostgreSQL 15+

5. **High memory usage**
   - Reduce `lookback_window` in loop detection
   - Implement batch processing for embeddings
   - Add pagination for large conversations

## Future Enhancements

- [ ] Support for other embedding models (Cohere, Voyage AI)
- [ ] Real-time streaming quality updates
- [ ] Citation tracking and validation
- [ ] Evidence grounding system
- [ ] Custom contradiction detection rules
- [ ] Multi-language support
- [ ] Advanced pattern detection (semantic loops)
- [ ] Quality trend analysis over time

## References

- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [FastAPI Async Support](https://fastapi.tiangolo.com/async/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
