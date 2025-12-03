# Quorum Streaming Analysis - Executive Summary

> **⚠️ UPDATED FOR DOCKER DEPLOYMENT**
>
> This summary has been updated to reflect the Docker Compose deployment model.
> Original research explored Vercel AI SDK, but **final implementation uses:**
> - **Backend:** FastAPI + LiteLLM (handles all LLM orchestration)
> - **Deployment:** Docker Compose (local-first, NOT serverless)
>
> See `FINAL_ARCHITECTURE.md` for complete implementation details.

---

**Date:** 2025-11-29
**Analyst:** ANALYST Agent (Quorum Hive Mind)

---

## Quick Recommendations (UPDATED: Docker-First)

For Quorum MVP, implement:

1. **Architecture:** Docker Compose (Frontend + FastAPI Backend)
2. **Abstraction:** LiteLLM (backend handles all provider normalization)
3. **Streaming:** Backend SSE → Frontend (HTTP/2)
4. **Token Counting:** Backend tiktoken + provider APIs
5. **Error Handling:** Backend exponential backoff with jitter
6. **Cost Tracking:** Backend calculates, frontend displays warnings
7. **Deployment:** docker-compose up (local), cloud as stretch goal

---

## Key Technical Findings

### Provider Streaming Comparison

| Provider | Format | Maturity | Compatibility |
|----------|--------|----------|---------------|
| **OpenAI** | SSE, delta chunks | ⭐⭐⭐⭐⭐ | Industry standard |
| **Anthropic** | SSE, structured events | ⭐⭐⭐⭐⭐ | Most sophisticated |
| **Gemini** | SSE, full chunks | ⭐⭐⭐ | Less mature, some bugs |
| **Mistral** | SSE, OpenAI-compatible | ⭐⭐⭐⭐ | Very compatible |

**Takeaway:** OpenAI and Mistral nearly identical. Anthropic most structured. Gemini least mature.

---

### Browser SSE Limitations

- **HTTP/1.1:** 6 concurrent connections per domain (shared across tabs)
- **HTTP/2:** 100+ concurrent streams (multiplexed over single connection)
- **Impact on Quorum:** 4 debaters + 1 judge = 5 streams → HTTP/2 required
- **Solution:** Deploy on Vercel/Netlify (HTTP/2 by default)

---

### Abstraction Layer Options

**LiteLLM** (CHOSEN - Backend)
- Python-based, production-grade
- Automatic provider normalization
- 100+ providers supported
- Handles 2M+ requests/month in production
- Perfect for FastAPI backend

**Vercel AI SDK** (Alternative - Client-Side)
- React-first design with hooks
- Good for client-side streaming
- Not needed with backend approach

**LangChain** (Not Recommended)
- Overkill for simple streaming
- Heavy dependency tree
- Better for RAG/agents

**Custom** (Not Needed)
- LiteLLM eliminates need for custom implementation

---

### Security: Client-Side vs Backend

**Pure Client-Side:** ❌
- API keys exposed in browser (CRITICAL RISK)
- Browser overhead with multiple SSE streams
- No rate limiting control

**Docker + Backend:** ⭐⭐⭐⭐⭐ (CHOSEN)
- API keys in backend .env file (secure)
- Backend handles all LLM connections
- Zero hosting costs for maintainer
- Users manage their own API usage
- Better performance (backend handles heavy lifting)

**Serverless Hybrid (Future):** ⭐⭐⭐⭐ (Stretch Goal)
- Cloud deployment option for later
- Already containerized, easy migration
- Can add multi-user features

---

### Simultaneous Streaming Strategy

> **Note:** Original research showed client-side approach. **Actual implementation** uses backend orchestration.

**Backend Implementation (FastAPI + LiteLLM):**
```python
# Backend handles multiple LLM streams in parallel
import asyncio
from litellm import acompletion

async def orchestrate_debate_round(debaters, context):
    # Start all debaters simultaneously
    tasks = [
        acompletion(
            model=f"{d.provider}/{d.model}",
            messages=context,
            stream=True
        )
        for d in debaters
    ]

    # Stream all responses to frontend via SSE
    responses = await asyncio.gather(*tasks)
    return responses
```

**Error Recovery:**
- Backend handles retry with exponential backoff
- Frontend receives partial results if some succeed
- Clear error indicators for failed debaters

---

### Token Counting Approach

**OpenAI:**
```typescript
import tiktoken from 'tiktoken';
const enc = tiktoken.get_encoding('cl100k_base'); // GPT-4
const tokens = enc.encode(text);
```

**Anthropic:**
```typescript
const count = await client.messages.countTokens({
  model: 'claude-3-5-sonnet-20241022',
  messages
});
```

**Gemini:**
```typescript
const result = await model.countTokens({ contents: messages });
```

**Mistral:**
```typescript
// Use tiktoken p50k_base for approximation
const enc = tiktoken.get_encoding('p50k_base');
```

---

### Cost Tracking

**Typical Pricing (per 1M tokens):**

| Model | Input | Output | Total (1K output) |
|-------|-------|--------|-------------------|
| GPT-4o | $2.50 | $10.00 | ~$0.01 |
| Claude 3.5 Sonnet | $3.00 | $15.00 | ~$0.015 |
| Gemini 1.5 Flash | $0.075 | $0.30 | ~$0.0003 |

**Implementation:**
- Calculate cost per message
- Display running total
- Warn at thresholds ($0.50, $1.00)
- Estimate before starting debate

---

### Rate Limiting Strategy

**Exponential Backoff Formula:**
```typescript
delay = min(maxDelay, baseDelay * (2 ** attempt)) * (0.5 + random() * 0.5)
```

**Parameters:**
- Base delay: 1000ms
- Max delay: 10000ms
- Max retries: 3
- Jitter: 50-100% of delay

**Honor Retry-After headers** when provided.

---

### Context Window Management

**Limits:**
- GPT-4 Turbo: 128K tokens
- Claude 3.5: 200K tokens
- Gemini 1.5 Pro: 2M tokens

**Strategy:**
- Track tokens per message
- Reserve 25% for responses
- Truncate oldest messages when approaching limit
- (Future) Summarize middle portions

---

## Recommended Tech Stack (UPDATED)

**Frontend (UI Layer):**
- Next.js 15 + React 19 with TypeScript
- Zustand + TanStack Query
- Tailwind CSS + shadcn/ui
- Port 3000

**Backend (LLM Orchestration):**
- FastAPI (Python 3.11+)
- LiteLLM (100+ provider support)
- SSE streaming to frontend
- Port 8000

**Development:**
- Docker Compose (single command setup)
- pnpm/npm
- ESLint + Prettier
- Vitest (unit tests)
- Playwright (E2E tests)

**Deployment:**
- Docker Compose (local MVP)
- Future Cloud: Vercel + Railway, Fly.io, or DigitalOcean
- Custom domain with HTTPS (for HTTP/2)

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| API key exposure | CRITICAL | Serverless proxy, env vars |
| Rate limiting | HIGH | Exponential backoff |
| Context overflow | MEDIUM | Token counting, truncation |
| High costs | MEDIUM | Real-time tracking, warnings |
| Stream failures | MEDIUM | Retry logic, partial success |

---

## Implementation Timeline

**Week 1: Foundation**
- Set up React + TypeScript
- Install Vercel AI SDK
- Create streaming API endpoint
- Test with single debater

**Week 2: Core Debate**
- Parallel streaming component
- Context management
- Judge agent
- Error handling

**Week 3: Features**
- Cost tracking
- Round management
- Persona assignment
- Export functionality

**Week 4: Polish**
- E2E testing
- Security audit
- Deploy to production
- Performance optimization

---

## Code Examples

### FastAPI Backend Streaming Endpoint

> **Note:** This replaces the original Vercel Edge Function approach.

```python
# backend/app/api/debate.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from litellm import acompletion
import asyncio
import json

app = FastAPI()

@app.post("/api/debate/stream")
async def stream_debate(config: DebateConfig):
    async def event_generator():
        # Orchestrate multiple debaters in parallel
        tasks = [
            stream_debater_response(d, config.context)
            for d in config.debaters
        ]

        # Stream each response to frontend
        async for debater_id, chunk in merge_streams(tasks):
            yield f"data: {json.dumps({
                'debater_id': debater_id,
                'chunk': chunk
            })}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

async def stream_debater_response(debater, context):
    response = await acompletion(
        model=f"{debater.provider}/{debater.model}",
        messages=context,
        stream=True
    )

    async for chunk in response:
        yield chunk['choices'][0]['delta']['content']
```

### React Frontend (Consumes Backend SSE)

```typescript
function SimultaneousDebate({ topic, debaters }) {
  const [responses, setResponses] = useState({});

  const startRound = async () => {
    const eventSource = new EventSource('/api/debate/stream');

    eventSource.onmessage = (event) => {
      const { debater_id, chunk } = JSON.parse(event.data);
      setResponses(prev => ({
        ...prev,
        [debater_id]: (prev[debater_id] || '') + chunk
      }));
    };
  };

  return (
    <div>
      {debaters.map(debater => (
        <DebaterPanel
          key={debater.id}
          name={debater.name}
          response={responses[debater.id]}
        />
      ))}
      <button onClick={startRound}>Start Round</button>
    </div>
  );
}
```

---

## Key Resources

**Provider Docs:**
- [OpenAI Streaming](https://cookbook.openai.com/examples/how_to_stream_completions)
- [Anthropic Streaming](https://docs.anthropic.com/en/docs/build-with-claude/streaming)
- [Gemini Streaming](https://cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-gemini-chat-completions-streaming)
- [Mistral API](https://docs.mistral.ai/api)

**Tools:**
- [Vercel AI SDK](https://ai-sdk.dev/docs/introduction)
- [tiktoken](https://github.com/openai/tiktoken)
- [LiteLLM](https://docs.litellm.ai/docs/)

**Articles:**
- [Multiple Parallel Streams](https://mikecavaliere.com/posts/multiple-parallel-streams-vercel-ai-sdk)
- [Rate Limiting Guide](https://cookbook.openai.com/examples/how_to_handle_rate_limits)
- [Token Counting Guide](https://winder.ai/calculating-token-counts-llm-context-windows-practical-guide/)

---

## Bottom Line (UPDATED)

**For Quorum MVP:**
1. Use **Docker Compose** for local-first deployment
2. **FastAPI + LiteLLM backend** handles all LLM orchestration
3. **Next.js frontend** consumes backend SSE stream
4. **Backend handles** parallel streaming, token counting, rate limiting
5. **Zero hosting costs** - users run locally with their own API keys
6. **Future-proof** - already containerized for cloud deployment later

**User Setup:**
```bash
git clone https://github.com/you/quorum.git
cd quorum
cp .env.example .env  # Add API keys
docker-compose up      # Everything runs!
```

**Timeline:** 4 weeks to functional multi-LLM debate platform.

**MVP Complexity:** Medium (LiteLLM handles 80% of provider complexity).

See `FINAL_ARCHITECTURE.md` for complete Docker setup and deployment guide.
