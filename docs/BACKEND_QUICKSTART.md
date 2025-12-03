# Backend Quick Start Guide

## Overview
FastAPI backend for Quorum - Phase 1: Single-LLM Streaming with SSE

## Prerequisites
- Python 3.11+
- pip or pipenv
- OpenAI API key

## Installation

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-actual-key-here
```

## Running the Server

### Development Mode (with auto-reload)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Alternative: Run via Python
```bash
python -m app.main
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### List Available Models
```bash
curl http://localhost:8000/api/v1/models
```

### Chat Completion (Streaming)
```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "model": "gpt-3.5-turbo",
    "stream": true
  }' \
  --no-buffer
```

### Chat Completion (Non-Streaming)
```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "model": "gpt-3.5-turbo",
    "stream": false
  }'
```

## Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Run Tests
```bash
pytest

# With coverage
pytest --cov=app tests/

# Verbose mode
pytest -v
```

### Manual Testing with SSE
Use the provided test script:
```bash
# Create test script
cat > test_sse.py << 'EOF'
import httpx
import json

async def test_streaming():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'POST',
            'http://localhost:8000/api/v1/chat/completions',
            json={
                'messages': [{'role': 'user', 'content': 'Count to 5'}],
                'model': 'gpt-3.5-turbo',
                'stream': True
            },
            timeout=30.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(data)

import asyncio
asyncio.run(test_streaming())
EOF

python test_sse.py
```

## Directory Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   └── health.py       # Health checks
│   ├── models/
│   │   ├── chat.py             # Request/response models
│   │   └── responses.py        # API response schemas
│   ├── services/
│   │   ├── llm_service.py      # LiteLLM integration
│   │   └── streaming.py        # SSE streaming
│   ├── config/
│   │   └── settings.py         # Environment config
│   └── utils/
│       ├── errors.py           # Error handlers
│       └── logging.py          # Logging setup
├── tests/                      # Test files
├── .env.example               # Environment template
├── requirements.txt           # Dependencies
└── requirements-dev.txt       # Dev dependencies
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `ENVIRONMENT` | No | development | Environment name |
| `DEBUG` | No | true | Debug mode |
| `VERSION` | No | 1.0.0 | API version |
| `LLM_TIMEOUT` | No | 60 | LLM request timeout (seconds) |
| `DEFAULT_MODEL` | No | gpt-3.5-turbo | Default LLM model |
| `MAX_TOKENS_LIMIT` | No | 4096 | Max tokens per request |
| `CORS_ORIGINS` | No | localhost:3000 | Allowed CORS origins |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |
| `LOG_LEVEL` | No | INFO | Logging level |

## Common Issues

### 1. Import Errors
If you get `ModuleNotFoundError`:
```bash
# Make sure you're in the backend directory
cd backend
# Activate virtual environment
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

### 2. OpenAI API Key Not Found
```bash
# Check .env file exists
ls -la .env

# Verify OPENAI_API_KEY is set
grep OPENAI_API_KEY .env

# If missing, add it:
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### 3. Port Already in Use
```bash
# Use different port
uvicorn app.main:app --reload --port 8001

# Or kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### 4. CORS Errors from Frontend
Check that `CORS_ORIGINS` in `.env` includes your frontend URL:
```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Development Workflow

### 1. Add New Endpoint
```python
# In app/api/routes/your_route.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/your-endpoint")
async def your_endpoint():
    return {"message": "Hello"}
```

### 2. Include Router in Main App
```python
# In app/main.py
from app.api.routes import your_route

app.include_router(your_route.router, prefix="/api/v1", tags=["your-tag"])
```

### 3. Add Request/Response Models
```python
# In app/models/your_model.py
from pydantic import BaseModel

class YourRequest(BaseModel):
    field: str
```

## Production Deployment

### Using Gunicorn + Uvicorn Workers
```bash
pip install gunicorn

gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Using Docker
```bash
# Build image
docker build -t quorum-backend .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  quorum-backend
```

## Monitoring

### View Logs
```bash
# Tail logs in real-time
tail -f app.log

# View last 100 lines
tail -100 app.log
```

### Health Check
```bash
# Automated health monitoring
watch -n 5 curl http://localhost:8000/health
```

## Next Steps

1. **Frontend Integration**: Connect React frontend to `/api/v1/chat/completions`
2. **Add Models**: Extend to support more LLM providers via LiteLLM
3. **Authentication**: Add API key authentication
4. **Rate Limiting**: Implement request rate limiting
5. **Database**: Add conversation persistence
6. **Metrics**: Add Prometheus metrics
7. **Phase 2**: Multi-LLM debate coordination

## Support

For issues or questions:
- Check architecture docs: `/docs/architecture/backend-architecture.md`
- Review API docs: http://localhost:8000/docs
- Check logs: `app.log`

---

**Architecture Design**: Complete ✅
**Implementation Ready**: Yes ✅
**Documentation**: Complete ✅
