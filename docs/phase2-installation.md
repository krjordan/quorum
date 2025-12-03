# Phase 2: Installation and Setup Guide

## Environment Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Key Dependencies:**
- fastapi[standard]==0.115.4
- uvicorn[standard]==0.32.0
- litellm==1.51.3
- tiktoken==0.8.0
- pydantic==2.9.2
- pydantic-settings==2.6.1

### 2. Configure API Keys

Create `.env` file in `backend/` directory:

```bash
# Required API Keys (at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...

# Optional Settings
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DEBUG=True
LOG_LEVEL=INFO
```

### 3. Verify Installation

```bash
cd backend
python verify_phase2.py
```

Expected output:
```
✅ Debate models
✅ Token counter
✅ Context manager
✅ Judge service
✅ Debate service
✅ Debate API routes
```

### 4. Start Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Server will start at: http://localhost:8000

## API Documentation

Once server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing the API

### 1. Create a Debate

```bash
curl -X POST http://localhost:8000/api/v1/debates \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Should AI development be open source?",
    "participants": [
      {
        "model": "gpt-4o",
        "persona": {
          "name": "Open Source Advocate",
          "role": "Argue for the benefits of open source AI",
          "temperature": 0.8
        }
      },
      {
        "model": "claude-3-5-sonnet-20241022",
        "persona": {
          "name": "Safety Researcher",
          "role": "Argue for controlled AI development",
          "temperature": 0.7
        }
      }
    ],
    "format": "structured",
    "judge_model": "gpt-4o",
    "max_rounds": 5,
    "cost_warning_threshold": 1.0
  }'
```

Response:
```json
{
  "id": "debate_abc123",
  "status": "initialized",
  "config": { ... },
  "total_cost": 0.0
}
```

### 2. Stream Debate Execution

```bash
# Using curl with SSE
curl -N http://localhost:8000/api/v1/debates/debate_abc123/stream
```

Or using EventSource in JavaScript:
```javascript
const eventSource = new EventSource('http://localhost:8000/api/v1/debates/debate_abc123/stream');

eventSource.addEventListener('response', (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.participant}: ${data.content}`);
});

eventSource.addEventListener('judge_assessment', (event) => {
  const data = JSON.parse(event.data);
  console.log('Scores:', data.participant_scores);
});

eventSource.addEventListener('debate_end', (event) => {
  const data = JSON.parse(event.data);
  console.log('Winner:', data.winner);
  eventSource.close();
});
```

### 3. Export Debate

```bash
# Export as Markdown
curl -X POST http://localhost:8000/api/v1/debates/debate_abc123/export \
  -H "Content-Type: application/json" \
  -d '{"format": "markdown"}' \
  -o debate.md

# Export as JSON
curl -X POST http://localhost:8000/api/v1/debates/debate_abc123/export \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}' \
  -o debate.json

# Export as HTML
curl -X POST http://localhost:8000/api/v1/debates/debate_abc123/export \
  -H "Content-Type: application/json" \
  -d '{"format": "html"}' \
  -o debate.html
```

## Supported Models

### OpenAI
- gpt-4o (recommended)
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo

### Anthropic
- claude-3-5-sonnet-20241022 (recommended)
- claude-3-5-haiku-20241022
- claude-3-opus-20240229
- claude-3-sonnet-20240229

### Google
- gemini-1.5-pro
- gemini-1.5-flash (cost-effective)

### Mistral
- mistral-large-latest
- mistral-medium-latest
- mistral-small-latest

## Cost Management

### Estimated Costs (per round with 2 participants)

**Budget Option (~$0.01/round):**
- Participants: gpt-4o-mini + gemini-1.5-flash
- Judge: gpt-4o-mini

**Balanced Option (~$0.05/round):**
- Participants: gpt-4o + claude-3-5-haiku
- Judge: gpt-4o

**Premium Option (~$0.15/round):**
- Participants: gpt-4o + claude-3-5-sonnet
- Judge: claude-3-5-sonnet

### Cost Warnings

System will warn at:
- 50% of threshold: Low warning
- 75% of threshold: Medium warning
- 100% of threshold: High warning
- 150% of threshold: Critical warning

## Troubleshooting

### Import Errors

If you see import errors, ensure all dependencies are installed:
```bash
pip install -r requirements.txt --upgrade
```

### API Key Issues

Verify API keys are set:
```bash
python -c "from app.config.settings import settings; print('OpenAI:', bool(settings.openai_api_key)); print('Anthropic:', bool(settings.anthropic_api_key))"
```

### Port Already in Use

Change port in startup command:
```bash
uvicorn app.main:app --reload --port 8001
```

### CORS Errors

Add frontend URL to `.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Performance Tuning

### Concurrent Debates

System can handle multiple concurrent debates. Recommended limits:
- Development: 5 concurrent debates
- Production: 20+ concurrent debates (with proper scaling)

### Token Limits

Default context limit: 100,000 tokens
To change:
```python
# In context_manager.py
self.max_context_tokens = 150_000  # Adjust as needed
```

### Cost Thresholds

Set per-debate in config:
```json
{
  "cost_warning_threshold": 2.0  // Warn at $2.00
}
```

## Monitoring

### Logs

Logs are written to stdout with structured format:
```
[2024-01-01 12:00:00] INFO: Created debate debate_abc123
[2024-01-01 12:00:05] INFO: Starting round 1
[2024-01-01 12:00:12] INFO: Completed round 1 - Cost: $0.0234
```

### Metrics

Track these metrics:
- Round latency (target: 3-8s)
- SSE event latency (target: <100ms)
- Token count per round
- Cost per round
- Debate completion rate

## Next Steps

1. ✅ Complete Phase 2 installation
2. ✅ Test API endpoints
3. ✅ Verify SSE streaming
4. → Start Phase 3: Frontend integration
5. → Add persistence layer
6. → Implement authentication

## Support

For issues or questions:
1. Check `/docs` endpoint for API documentation
2. Review logs for error details
3. Verify all environment variables are set
4. Ensure API keys have sufficient credits
