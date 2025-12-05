# Database Migration Quick Start

## TL;DR - Get Running in 3 Steps

### 1. Start PostgreSQL with pgvector

```bash
docker run -d \
  --name quorum-postgres \
  -e POSTGRES_USER=quorum_user \
  -e POSTGRES_PASSWORD=quorum_pass \
  -e POSTGRES_DB=quorum_db \
  -p 5432:5432 \
  ankane/pgvector:latest
```

### 2. Configure Database URL

```bash
cd backend
cp .env.example .env
# Edit .env and set:
# DATABASE_URL=postgresql://quorum_user:quorum_pass@localhost:5432/quorum_db
```

### 3. Run Migrations

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Apply migrations
alembic upgrade head
```

Done! Your database now has all 7 quality management tables with pgvector support.

## Verify Setup

```bash
# Check database connection
python -c "from app.config.database import check_db_connection, check_pgvector_extension; print('DB:', check_db_connection()); print('pgvector:', check_pgvector_extension())"

# Check migration status
alembic current

# Should show:
# 001_quality_tables (head)
```

## What Was Created?

- **7 Tables**: conversations, messages, message_embeddings, conversation_quality, contradictions, conversation_loops, message_citations
- **20+ Indexes**: Including HNSW vector index for fast similarity search
- **pgvector Extension**: Enabled for semantic search
- **Constraints**: Health score ranges, foreign keys, cascade deletes

## Common Commands

```bash
# View migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback all
alembic downgrade base

# Create new migration after model changes
alembic revision --autogenerate -m "description"
```

## Troubleshooting

### "extension vector does not exist"
Use the Docker image: `ankane/pgvector:latest`

### "cannot import name Base"
Run from backend directory: `cd backend && alembic upgrade head`

### "relation already exists"
Drop and recreate: `alembic downgrade base && alembic upgrade head`

## Next Steps

See `/Users/ryanjordan/Projects/quorum/backend/docs/database-setup.md` for:
- Detailed schema documentation
- Production deployment guide
- Performance tuning
- Backup/restore procedures
- Testing instructions
