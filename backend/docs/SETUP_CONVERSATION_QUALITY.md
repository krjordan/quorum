# Conversation Quality Management Setup Guide

## Quick Start

This guide walks through setting up the conversation quality management system for the Quorum backend.

## Prerequisites

- PostgreSQL 12+ with pgvector extension
- Python 3.9+
- OpenAI API key (for embeddings)
- Virtual environment activated

## Installation Steps

### 1. Install Python Dependencies

All required dependencies are already in `requirements.txt`:

```bash
cd /Users/ryanjordan/Projects/quorum/backend

# Activate virtual environment
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

Key dependencies:
- `openai==1.54.3` - OpenAI API client for embeddings
- `sqlalchemy==2.0.36` - Database ORM
- `psycopg2-binary==2.9.9` - PostgreSQL driver
- `pgvector==0.3.5` - Vector similarity search
- `anthropic==0.39.0` - Anthropic API for LLM analysis
- `numpy==1.26.4` - Numerical operations

### 2. Configure Environment Variables

Create or update `/Users/ryanjordan/Projects/quorum/backend/.env`:

```bash
# Required: OpenAI API Key for embeddings
OPENAI_API_KEY=sk-proj-...

# Required: Database URL (PostgreSQL with pgvector)
DATABASE_URL=postgresql://user:password@localhost:5432/quorum

# Optional: Other LLM providers for contradiction/loop detection
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...

# Optional: Debug settings
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Setup PostgreSQL with pgvector

#### Option A: Using Docker (Recommended)

```bash
cd /Users/ryanjordan/Projects/quorum/docker/development

# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Verify pgvector is installed
docker exec -it quorum-postgres psql -U quorum -d quorum -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Option B: Local PostgreSQL Installation

**macOS:**
```bash
brew install postgresql pgvector
brew services start postgresql

# Create database
createdb quorum

# Enable pgvector
psql quorum -c "CREATE EXTENSION vector;"
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install postgresql-14-pgvector

sudo systemctl start postgresql
sudo -u postgres createdb quorum
sudo -u postgres psql quorum -c "CREATE EXTENSION vector;"
```

### 4. Run Database Migrations

```bash
cd /Users/ryanjordan/Projects/quorum/backend

# Run all migrations
alembic upgrade head

# Verify tables were created
psql quorum -c "\dt"
```

Expected tables:
- `messages`
- `message_embeddings`
- `contradictions`
- `conversation_loops`
- `health_scores`

### 5. Verify Installation

```bash
# Test service imports
python -c "
from app.services import (
    embedding_service,
    contradiction_service,
    loop_detection_service,
    health_scoring_service
)
print('✓ All services imported successfully')
"

# Test OpenAI API connection
python -c "
import asyncio
from app.services import embedding_service

async def test():
    emb = await embedding_service.generate_embedding('test')
    print(f'✓ OpenAI API working (embedding dim: {len(emb)})')

asyncio.run(test())
"
```

## Configuration Options

### Embedding Service Configuration

```python
from app.services import embedding_service

# Change default model
embedding_service.default_model = "text-embedding-3-large"  # 3072 dimensions
embedding_service.embedding_dimension = 3072

# Note: If changing model, update migration to match dimension
```

### Contradiction Detection Tuning

```python
from app.services import contradiction_service

# Adjust similarity threshold (default: 0.85)
contradiction_service.similarity_threshold = 0.90  # Stricter

# Adjust opposition threshold (default: 0.3)
contradiction_service.opposition_threshold = 0.25  # More sensitive
```

### Loop Detection Tuning

```python
from app.services import loop_detection_service

# Minimum pattern length (default: 2)
loop_detection_service.min_pattern_length = 3

# Minimum repetitions to trigger (default: 2)
loop_detection_service.min_repetitions = 3

# Lookback window (default: 20)
loop_detection_service.lookback_window = 30  # Analyze more history
```

### Health Scoring Weights

```python
from app.services import health_scoring_service

# Adjust component weights (must sum to 1.0)
health_scoring_service.coherence_weight = 0.5      # 50%
health_scoring_service.progress_weight = 0.3       # 30%
health_scoring_service.productivity_weight = 0.2   # 20%

# Adjust status thresholds
health_scoring_service.excellent_threshold = 90  # Default: 85
health_scoring_service.good_threshold = 75       # Default: 70
health_scoring_service.fair_threshold = 55       # Default: 50
```

## Testing

### Unit Tests

```bash
cd /Users/ryanjordan/Projects/quorum/backend

# Run quality service tests
pytest tests/services/test_embedding_service.py
pytest tests/services/test_contradiction_service.py
pytest tests/services/test_loop_detection_service.py
pytest tests/services/test_health_scoring_service.py

# Run all tests
pytest tests/services/
```

### Integration Test

```bash
# Test full pipeline
pytest tests/integration/test_conversation_quality_pipeline.py
```

## API Integration

### Basic Usage Example

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import (
    contradiction_service,
    loop_detection_service,
    health_scoring_service
)
from app.database import get_db

router = APIRouter(prefix="/api/quality", tags=["quality"])

@router.post("/conversations/{conv_id}/analyze")
async def analyze_quality(
    conv_id: str,
    new_message: dict,
    db: AsyncSession = Depends(get_db)
):
    """Analyze conversation quality"""

    # Detect contradictions
    contradictions = await contradiction_service.detect_contradictions(
        db=db,
        conversation_id=conv_id,
        new_message=new_message
    )

    # Get recent messages
    recent_messages = await get_recent_messages(db, conv_id, limit=20)

    # Detect loops
    loop = await loop_detection_service.detect_loops(
        db=db,
        conversation_id=conv_id,
        recent_messages=recent_messages
    )

    # Calculate health score
    health = await health_scoring_service.calculate_health_score(
        db=db,
        conversation_id=conv_id,
        recent_messages=recent_messages
    )

    return {
        "conversation_id": conv_id,
        "contradictions": [c.to_dict() for c in contradictions],
        "loop": loop.to_dict() if loop else None,
        "health_score": health.to_dict(),
        "alerts": {
            "has_contradictions": len(contradictions) > 0,
            "has_loop": loop is not None,
            "health_status": health.status
        }
    }
```

## Monitoring

### Database Performance

```sql
-- Monitor embedding vector index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname LIKE 'idx_message_embeddings%';

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('messages', 'message_embeddings', 'contradictions', 'conversation_loops', 'health_scores')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Service Logging

```python
import logging

# Enable detailed logging for quality services
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Service-specific loggers
logging.getLogger('app.services.embedding_service').setLevel(logging.DEBUG)
logging.getLogger('app.services.contradiction_service').setLevel(logging.INFO)
```

## Troubleshooting

### Issue: "Extension 'vector' not found"

**Solution:**
```bash
# Install pgvector
brew install pgvector  # macOS
# OR
sudo apt-get install postgresql-14-pgvector  # Ubuntu

# Enable in database
psql quorum -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Issue: "OpenAI API rate limit exceeded"

**Solution:**
```python
# Use batch processing to reduce API calls
from app.services import embedding_service

# Instead of:
# for text in texts:
#     await embedding_service.generate_embedding(text)

# Use batch:
embeddings = await embedding_service.batch_generate_embeddings(texts)
```

### Issue: Slow similarity searches

**Solution:**
```sql
-- Rebuild vector index with more lists
DROP INDEX idx_message_embeddings_vector;
CREATE INDEX idx_message_embeddings_vector
ON message_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);  -- Increase based on data size

-- Analyze table for query planner
ANALYZE message_embeddings;
```

### Issue: High memory usage

**Solution:**
```python
# Reduce lookback window
loop_detection_service.lookback_window = 10  # Default: 20

# Limit health score analysis
recent_messages = recent_messages[-15:]  # Only last 15 messages
```

## Production Checklist

- [ ] PostgreSQL with pgvector installed and configured
- [ ] All migrations run successfully
- [ ] OpenAI API key configured in `.env`
- [ ] Database indexes created and optimized
- [ ] Service logging configured
- [ ] API endpoints integrated
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Monitoring dashboards set up
- [ ] Alert thresholds configured

## Next Steps

1. **Integrate with frontend**: Add SSE streaming for real-time quality updates
2. **Add caching**: Use Redis to cache embeddings and health scores
3. **Implement interventions**: Auto-inject loop breaking messages
4. **Create dashboard**: Visualize health metrics over time
5. **Add analytics**: Track quality trends and patterns

## Support

For issues or questions:
- Review full documentation: `/Users/ryanjordan/Projects/quorum/backend/docs/conversation-quality-services.md`
- Check architecture docs: `/Users/ryanjordan/Projects/quorum/docs/architecture/mvp-conversation-quality-architecture.md`
- Review service code: `/Users/ryanjordan/Projects/quorum/backend/app/services/`

## API Cost Estimates

### OpenAI Embeddings
- Model: `text-embedding-3-small`
- Cost: $0.00002 per 1K tokens (~750 words)
- Average message: ~200 tokens = $0.000004
- 1000 messages: ~$0.004

### LLM Analysis (Contradiction/Loop Detection)
- Model: `gpt-4o-mini` (fallback: claude-3-haiku)
- Cost: ~$0.0015 per analysis
- Only triggered when patterns detected
- Estimated: <10 analyses per conversation

**Total estimated cost per conversation: < $0.02**
