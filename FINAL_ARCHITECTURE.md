# Quorum: Final Architecture (Docker-Based, Local-First)

**Date:** November 30, 2025
**Deployment Model:** Docker Compose for local deployment, cloud deployment as stretch goal
**Performance:** Backend proxy handles heavy lifting, better browser performance

---

## TL;DR - The Best of Both Worlds

You're absolutely right - **keeping the backend is better for performance**:

✅ **Frontend:** Next.js 15 + React 19 (UI only)
✅ **Backend:** Python + FastAPI + LiteLLM (handles all LLM calls)
✅ **Deployment:** Docker Compose (one command: `docker-compose up`)
✅ **Now:** Users run locally, zero hosting costs for you
✅ **Later:** Easy to deploy to cloud (Vercel + Railway/Fly.io)

---

## Why Backend Is Better

### Performance Benefits:
1. **Less browser overhead** - Backend handles multiple concurrent streams
2. **Better connection pooling** - Backend maintains persistent connections
3. **Efficient token counting** - Server-side processing
4. **Robust rate limiting** - Backend handles retries and backoff
5. **Context management** - Server can cache and optimize context

### User Experience Benefits:
1. **Faster response times** - Backend can pre-fetch/optimize
2. **Better error handling** - Backend gracefully manages failures
3. **Progress indicators** - Backend can send fine-grained updates
4. **Lower memory usage** - Browser doesn't hold multiple SSE connections

### Developer Benefits:
1. **Cleaner separation** - Frontend = UI, Backend = LLM orchestration
2. **Easier testing** - Mock backend API instead of LLM providers
3. **Future-proof** - Ready to deploy when you want
4. **Better debugging** - Backend logs all LLM interactions

---

## Final Tech Stack

```yaml
# FRONTEND (UI Layer)
Framework: Next.js 15 (App Router)
UI Library: React 19
Language: TypeScript (strict)
State: Zustand + TanStack Query
Styling: Tailwind CSS + shadcn/ui
Port: 3000

# BACKEND (LLM Orchestration Layer)
Framework: FastAPI (Python 3.11+)
LLM SDK: LiteLLM (100+ providers, auto-normalization)
Streaming: SSE via FastAPI StreamingResponse
Rate Limiting: In-memory (MVP) or Redis (optional)
Token Counting: tiktoken + provider APIs
Port: 8000

# ORCHESTRATION (Shared Logic)
State Machine: XState (debate lifecycle FSM)
Context Management: Hybrid (sliding window + summarization)
Judge System: Structured JSON output

# STORAGE
API Keys: Backend environment variables (.env file)
Debate History: SQLite (local file) or PostgreSQL (optional)
Export: Backend generates files, frontend downloads

# DEPLOYMENT (Local-First)
Development: docker-compose up
Production: docker-compose -f docker-compose.prod.yml up
Future: Vercel (frontend) + Railway/Fly.io (backend)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                 User's Browser (localhost:3000)              │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           Next.js React App (UI Only)                    ││
│  │                                                           ││
│  │  ┌──────────┐  ┌─────────────┐  ┌──────────────────┐   ││
│  │  │ Zustand  │  │  TanStack   │  │  UI Components   │   ││
│  │  │ UI State │  │  Query      │  │  (shadcn/ui)     │   ││
│  │  └──────────┘  └─────────────┘  └──────────────────┘   ││
│  │                                                           ││
│  │  Makes HTTP/SSE requests to local backend                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                   HTTP/SSE (localhost:8000)
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│          User's Local Backend (localhost:8000)               │
│                   Docker Container                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │         FastAPI + LiteLLM (Orchestration)                ││
│  │                                                           ││
│  │  ┌──────────────────────────────────────────────────┐   ││
│  │  │  LiteLLM Proxy Layer                              │   ││
│  │  │  - Automatic provider normalization               │   ││
│  │  │  - Streaming SSE → Frontend                       │   ││
│  │  │  - Token counting & cost tracking                 │   ││
│  │  │  - Rate limiting & retry logic                    │   ││
│  │  │  - Context window management                      │   ││
│  │  └──────────────────────────────────────────────────┘   ││
│  │                                                           ││
│  │  ┌──────────────────────────────────────────────────┐   ││
│  │  │  Debate Engine (XState FSM)                       │   ││
│  │  │  - State management (11 states)                   │   ││
│  │  │  - Round orchestration                            │   ││
│  │  │  - Judge integration                              │   ││
│  │  └──────────────────────────────────────────────────┘   ││
│  │                                                           ││
│  │  ┌──────────────────────────────────────────────────┐   ││
│  │  │  Storage                                          │   ││
│  │  │  - API keys (.env file)                           │   ││
│  │  │  - Debate history (SQLite)                        │   ││
│  │  └──────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                   Direct API Calls (HTTPS)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Anthropic │    │  OpenAI  │    │  Google  │
    │ API      │    │  API     │    │  API     │
    └──────────┘    └──────────┘    └──────────┘

    User's API keys (in backend .env) → User pays for usage
```

---

## Docker Compose Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
    volumes:
      - ./backend:/app
      - ./data:/app/data  # SQLite database
```

### .env.example

```bash
# User copies this to .env and adds their keys

# Required: At least one LLM provider
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...

# Optional: Additional providers
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...

# Optional: Advanced settings
DATABASE_URL=sqlite:///data/quorum.db
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## User Setup Experience

### Step 1: Clone Repo
```bash
git clone https://github.com/you/quorum.git
cd quorum
```

### Step 2: Add API Keys
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Step 3: Run with Docker
```bash
docker-compose up
```

**That's it!** Both frontend and backend start automatically.

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend Docs: http://localhost:8000/docs (FastAPI auto-generated)

---

## Backend API Design

### Endpoints

```python
# POST /api/debate/start
# Start a new debate
{
  "topic": "Should AI be regulated?",
  "debaters": [
    {"provider": "anthropic", "model": "claude-sonnet-4-5", "persona": "auto"},
    {"provider": "openai", "model": "gpt-4", "persona": "auto"}
  ],
  "judge": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
  "format": "free-form"
}

# Response: debate_id

# GET /api/debate/{debate_id}/stream (SSE)
# Stream debate responses in real-time
# Frontend connects to this SSE endpoint

# POST /api/debate/{debate_id}/stop
# Stop debate early

# GET /api/debate/{debate_id}/export
# Export debate as Markdown or JSON

# GET /api/debate/history
# Get list of past debates

# GET /api/providers
# Get available providers based on configured API keys
```

### FastAPI Implementation (Example)

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from litellm import completion
import asyncio

app = FastAPI()

@app.post("/api/debate/start")
async def start_debate(config: DebateConfig):
    debate_id = create_debate(config)
    return {"debate_id": debate_id}

@app.get("/api/debate/{debate_id}/stream")
async def stream_debate(debate_id: str):
    async def event_stream():
        debate = get_debate(debate_id)

        # Orchestrate debate rounds
        for round_num in range(debate.max_rounds):
            # Get responses from all debaters in parallel
            tasks = [
                get_debater_response(debater, debate.context)
                for debater in debate.debaters
            ]

            responses = await asyncio.gather(*tasks)

            # Stream each response to frontend
            for debater_id, response in enumerate(responses):
                async for chunk in response:
                    yield f"data: {json.dumps({
                        'type': 'debater_response',
                        'debater_id': debater_id,
                        'chunk': chunk
                    })}\n\n"

            # Get judge assessment
            judge_response = await get_judge_assessment(debate)
            yield f"data: {json.dumps({
                'type': 'judge_assessment',
                'assessment': judge_response
            })}\n\n"

            # Check if should stop
            if judge_response['should_conclude']:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")

async def get_debater_response(debater, context):
    # LiteLLM handles all provider differences automatically
    response = await completion(
        model=f"{debater.provider}/{debater.model}",
        messages=context,
        stream=True
    )

    async for chunk in response:
        yield chunk['choices'][0]['delta']['content']
```

---

## Performance Comparison

### Client-Side Approach (Browser Heavy):
- ❌ Browser manages 4+ SSE connections simultaneously
- ❌ Browser handles token counting for all messages
- ❌ Browser memory holds full context for all debaters
- ❌ Browser CPU processes streaming chunks
- ⚠️ Tab slowdown, high memory usage

### Backend Approach (Browser Light):
- ✅ Backend manages SSE connections (connection pooling)
- ✅ Backend handles token counting (server-side)
- ✅ Backend caches context efficiently
- ✅ Browser just renders UI updates
- ✅ Smooth UI, low memory usage

**Winner:** Backend approach - much better performance

---

## Development Workflow

### Local Development (Hot Reload)

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Or just use Docker Compose:
docker-compose up
```

### Project Structure

```
quorum/
├── frontend/               # Next.js app
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
├── backend/                # FastAPI app
│   ├── app/
│   │   ├── main.py        # FastAPI routes
│   │   ├── llm/           # LiteLLM integration
│   │   ├── debate/        # Debate orchestration
│   │   └── db/            # SQLite models
│   ├── requirements.txt
│   └── Dockerfile
├── data/                   # SQLite database (gitignored)
├── docker-compose.yml
├── .env.example
├── .env                    # User's API keys (gitignored)
└── README.md
```

---

## Deployment Options

### Now: Local Only (docker-compose up)
- Zero hosting costs for you
- Users run on their own machines
- Perfect for MVP

### Later: Cloud Deployment (Stretch Goal)

**Option 1: Vercel + Railway**
```bash
# Frontend → Vercel (free tier)
cd frontend
vercel deploy

# Backend → Railway (free tier: 500 hours/month)
cd backend
railway up
```

**Option 2: Fly.io (Full Stack)**
```bash
# Deploy both frontend + backend to Fly.io
fly deploy
```

**Option 3: DigitalOcean/AWS (Traditional)**
- Frontend: Static hosting (S3 + CloudFront)
- Backend: Docker on EC2/Droplet

---

## API Key Management

### For Local Deployment:
- User adds keys to `.env` file
- Backend reads from environment variables
- Keys never exposed to frontend/browser
- More secure than localStorage approach

### For Future Cloud Deployment:
- User adds keys via Settings UI
- Backend stores encrypted in PostgreSQL
- Per-user isolation
- Session-based authentication

---

## Why This Is The Best Approach

### ✅ Performance
- Backend handles heavy LLM orchestration
- Browser stays lightweight and responsive
- Better for users with slower machines

### ✅ Architecture
- Clean separation: Frontend = UI, Backend = Logic
- Easier to test and debug
- Industry-standard pattern

### ✅ Scalability
- Ready to deploy to cloud when you want
- Can add authentication, multi-user, sharing easily
- No major refactoring needed

### ✅ Developer Experience
- FastAPI auto-generates API docs (http://localhost:8000/docs)
- Backend logs all LLM interactions
- Frontend just makes simple HTTP/SSE requests

### ✅ User Experience
- One command: `docker-compose up`
- Better performance than client-side
- Familiar Docker workflow

### ✅ Future-Proof
- Easy to add features (sharing, analytics, multi-user)
- Easy to deploy (already containerized)
- No technical debt

---

## Updated Timeline

### Phase 1: Foundation (Weeks 1-2)
- [x] Next.js 15 frontend setup
- [x] **FastAPI backend setup**
- [x] **Docker Compose configuration**
- [x] Basic debate API (single LLM)
- [x] SSE streaming frontend → backend

**Deliverable:** Simple debate with one LLM

### Phase 2: Core Engine (Weeks 3-4)
- [x] **LiteLLM integration (multi-provider)**
- [x] Parallel streaming (backend orchestrates 2-4 LLMs)
- [x] XState debate FSM (backend)
- [x] Token counting & cost tracking (backend)
- [x] Context management (backend)

**Deliverable:** Full multi-LLM debates

### Phase 3-5: Same as Before
- Judge agent, formats, export, testing, polish
- **Backend handles all logic, frontend renders**

**Total:** Still 9 weeks, but better architecture

---

## LiteLLM Benefits (Why Backend Makes Sense)

```python
# Without LiteLLM (manual approach):
# - 500+ lines to normalize 4 providers
# - Manual token counting for each
# - Different retry logic per provider
# - 3-4 weeks of work

# With LiteLLM (automatic):
from litellm import completion

# Works with 100+ providers automatically
response = completion(
    model="anthropic/claude-sonnet-4-5",  # or "openai/gpt-4", "gemini/pro"
    messages=messages,
    stream=True
)

# Automatic:
# ✅ Provider normalization
# ✅ Token counting
# ✅ Rate limiting
# ✅ Cost tracking
# ✅ Error handling

# 50 lines of code vs 500+
```

**This is why keeping the backend makes sense!**

---

## Summary

| Aspect | Client-Side Only | **Backend + Docker (Final Choice)** |
|--------|------------------|-------------------------------------|
| Performance | Browser heavy ❌ | Browser light ✅ |
| Deployment | npm start | `docker-compose up` ✅ |
| Future Cloud | Major refactor ❌ | Ready to deploy ✅ |
| Architecture | Mixed concerns ❌ | Clean separation ✅ |
| API Keys | localStorage ⚠️ | .env file ✅ |
| Testing | Mock LLM SDKs | Mock backend API ✅ |
| User Setup | Easy ✅ | Easy ✅ (one command) |
| Your Costs Now | $0 ✅ | $0 ✅ |
| Your Costs Later | N/A | Optional deployment |

---

## Action Items

1. ✅ Keep backend architecture (FastAPI + LiteLLM)
2. ✅ Use Docker Compose for local deployment
3. ✅ Frontend calls localhost:8000 backend
4. ✅ Backend handles all LLM orchestration
5. ✅ Cloud deployment as stretch goal (post-MVP)

---

**Final Decision:** Backend + Docker architecture for better performance, clean separation, and future-proof design.

**Next Step:** Begin implementation with this architecture.
