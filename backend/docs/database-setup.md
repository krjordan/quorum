# Database Setup Guide

## Overview

The Conversation Quality Management system uses PostgreSQL with the pgvector extension for semantic similarity search. This guide covers database setup and migration management.

## Database Models

The system includes 7 main tables:

1. **conversations** - Main conversation entity with health tracking
2. **messages** - Individual agent messages with quality scores
3. **message_embeddings** - Vector embeddings for semantic search (1536 dimensions)
4. **conversation_quality** - Time-series quality metrics
5. **contradictions** - Detected conflicting statements
6. **conversation_loops** - Repetitive pattern detection
7. **message_citations** - Citation tracking and verification

## Prerequisites

### PostgreSQL with pgvector

```bash
# macOS (using Homebrew)
brew install postgresql@15
brew install pgvector

# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-15-pgvector

# Docker (recommended for development)
docker run -d \
  --name quorum-postgres \
  -e POSTGRES_USER=quorum_user \
  -e POSTGRES_PASSWORD=quorum_pass \
  -e POSTGRES_DB=quorum_db \
  -p 5432:5432 \
  ankane/pgvector:latest
```

## Initial Setup

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Includes:
- `sqlalchemy==2.0.36` - ORM framework
- `alembic==1.14.0` - Database migration tool
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `pgvector==0.3.5` - pgvector Python bindings

### 2. Configure Database URL

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` and set your database URL:

```bash
# For PostgreSQL (recommended)
DATABASE_URL=postgresql://quorum_user:quorum_pass@localhost:5432/quorum_db

# For SQLite (development only - no vector search)
DATABASE_URL=sqlite:///./data/quorum.db
```

### 3. Verify Database Connection

```bash
# Start PostgreSQL (if using Docker)
docker start quorum-postgres

# Test connection
python -c "from app.config.database import check_db_connection; print(check_db_connection())"

# Check pgvector extension
python -c "from app.config.database import check_pgvector_extension; print(check_pgvector_extension())"
```

## Running Migrations

### Apply All Migrations

```bash
# From backend directory
alembic upgrade head
```

This will:
1. Enable pgvector extension
2. Create all 7 quality management tables
3. Add indexes including HNSW vector index
4. Set up foreign key constraints

### Check Migration Status

```bash
alembic current
alembic history
```

### Rollback Migration

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 001_quality_tables

# Rollback all
alembic downgrade base
```

## Creating New Migrations

### Auto-generate from Model Changes

```bash
# After modifying models in app/models/quality.py
alembic revision --autogenerate -m "describe your changes"

# Review the generated migration file in alembic/versions/
# Edit if necessary, then apply
alembic upgrade head
```

### Manual Migration

```bash
alembic revision -m "describe your changes"
# Edit the generated file in alembic/versions/
alembic upgrade head
```

## Database Schema

### Key Features

#### 1. Vector Embeddings

The `message_embeddings` table uses pgvector's `vector(1536)` type:

```sql
-- HNSW index for fast similarity search
CREATE INDEX idx_embeddings_vector_hnsw
ON message_embeddings
USING hnsw (embedding_vector vector_cosine_ops);
```

Query example (from Python):
```python
from sqlalchemy import text

# Find similar messages
query = text("""
    SELECT m.id, m.content, me.embedding_vector <=> :query_vector AS distance
    FROM messages m
    JOIN message_embeddings me ON m.id = me.message_id
    ORDER BY me.embedding_vector <=> :query_vector
    LIMIT 10
""")
results = session.execute(query, {"query_vector": your_embedding})
```

#### 2. Health Score Tracking

All health scores are constrained to 0-100 range:

```sql
CHECK (health_score >= 0 AND health_score <= 100)
```

#### 3. Cascade Deletes

Deleting a conversation automatically removes:
- All messages
- All embeddings
- All quality metrics
- All contradictions
- All loop detections
- All citations

#### 4. Indexes

Optimized indexes for common queries:
- Conversation lookup by user and date
- Message ordering within conversations
- Health score filtering
- Vector similarity search (HNSW)
- Citation verification status

## Development Workflow

### Using SQLite for Local Development

SQLite works for basic development but lacks:
- Vector similarity search (pgvector)
- Advanced indexing (HNSW)
- Concurrent writes

Set in `.env`:
```bash
DATABASE_URL=sqlite:///./data/quorum.db
```

### Using PostgreSQL for Full Features

Required for:
- Semantic similarity search
- Production deployment
- Performance testing

## Common Issues

### Issue: "extension vector does not exist"

**Solution:**
```bash
# Install pgvector
brew install pgvector  # macOS
sudo apt-get install postgresql-15-pgvector  # Ubuntu

# Or use Docker image with pgvector
docker run -d --name quorum-postgres ankane/pgvector:latest
```

### Issue: Migration fails with "cannot import name 'Base'"

**Solution:**
Ensure you're running from the `backend` directory:
```bash
cd backend
alembic upgrade head
```

### Issue: "relation already exists"

**Solution:**
Database tables already exist. Either:
```bash
# Drop and recreate
alembic downgrade base
alembic upgrade head

# Or skip to latest without running migrations
alembic stamp head
```

## Production Deployment

### Environment Variables

```bash
# Production database
DATABASE_URL=postgresql://user:password@db-host:5432/quorum_prod

# Connection pooling (adjust based on load)
# These are set in app/config/database.py
# pool_size=5
# max_overflow=10
# pool_recycle=3600
```

### Performance Tuning

1. **HNSW Index Parameters** (in migration):
```sql
-- Adjust for your data size
CREATE INDEX idx_embeddings_vector_hnsw
ON message_embeddings
USING hnsw (embedding_vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

2. **PostgreSQL Configuration**:
```ini
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 128MB
```

3. **Connection Pooling**:
```python
# app/config/database.py
engine = create_engine(
    settings.database_url,
    pool_size=10,        # Increase for production
    max_overflow=20,     # Allow burst capacity
    pool_pre_ping=True,  # Verify connections
)
```

## Testing

### Run Database Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/test_database.py -v
```

### Manual Testing

```python
# Python shell
from app.config.database import get_db_context, check_db_connection
from app.models import Conversation, Message

# Test connection
print(check_db_connection())

# Create test data
with get_db_context() as db:
    conversation = Conversation(
        title="Test Conversation",
        topic="Testing database setup"
    )
    db.add(conversation)
    db.commit()
    print(f"Created conversation: {conversation.id}")
```

## Backup and Restore

### Backup

```bash
# PostgreSQL
pg_dump -U quorum_user quorum_db > backup.sql

# With Docker
docker exec quorum-postgres pg_dump -U quorum_user quorum_db > backup.sql
```

### Restore

```bash
# PostgreSQL
psql -U quorum_user quorum_db < backup.sql

# With Docker
docker exec -i quorum-postgres psql -U quorum_user quorum_db < backup.sql
```

## Monitoring

### Check Database Size

```sql
SELECT
    pg_size_pretty(pg_database_size('quorum_db')) as db_size,
    pg_size_pretty(pg_total_relation_size('conversations')) as conversations_size,
    pg_size_pretty(pg_total_relation_size('messages')) as messages_size,
    pg_size_pretty(pg_total_relation_size('message_embeddings')) as embeddings_size;
```

### Check Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## References

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Support

For issues or questions:
1. Check this guide first
2. Review migration files in `alembic/versions/`
3. Check model definitions in `app/models/quality.py`
4. Review database configuration in `app/config/database.py`
