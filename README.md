# Quorum - AI Debate Platform

**Multi-LLM structured debates with AI judge oversight**

Quorum is an open-source platform that enables multiple LLMs to engage in structured debates and discussions on user-provided topics. Watch AI models argue different positions, with an AI judge monitoring quality, detecting diminishing returns, and determining when meaningful conclusions have been reached.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose (for backend services)
- Node.js 20+ (for frontend development)
- API keys for at least one LLM provider (Anthropic, OpenAI, Google, or Mistral)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/quorum.git
cd quorum
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Start the development environment**

**Option A: Quick Start Script (Recommended)**
```bash
./scripts/dev.sh
```

This script will:
- Start backend services in Docker (FastAPI + Redis)
- Wait for backend to be healthy
- Install frontend dependencies if needed
- Start the frontend dev server locally

**Option B: Manual Start**
```bash
# Terminal 1: Start backend services
docker-compose -f docker/development/docker-compose.yml up

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

5. **Stop services**
```bash
# Stop backend services
./scripts/stop.sh

# Stop frontend: Press Ctrl+C in the frontend terminal
```

## 📋 Current Status: Phase 2 Complete

**Phase 1: Single-LLM Streaming Chat Interface** ✅ COMPLETE
- ✅ Next.js 15 frontend with TypeScript strict mode
- ✅ FastAPI backend with LiteLLM integration
- ✅ Basic SSE streaming for single LLM
- ✅ Zustand state management
- ✅ Tailwind CSS + shadcn/ui components
- ✅ Docker Compose deployment

**Phase 2: Sequential Multi-LLM Debate Engine** ✅ COMPLETE
- ✅ Sequential turn-based debate system (2-4 agents)
- ✅ XState v5 state machine for robust state management
- ✅ Custom system prompts per agent
- ✅ Manual debate control (pause/resume/stop)
- ✅ Real-time cost tracking
- ✅ Formatted markdown summaries
- ✅ Comprehensive backend tests (34/34 passing)
- ✅ Python 3.9+ compatibility

## 🏗️ Architecture

```
Development Environment
├── Frontend (localhost:3000) - Runs locally
│   ├── Next.js 15 + React 19
│   ├── Zustand (state management)
│   ├── npm run dev (hot-reload)
│   └── shadcn/ui (components)
│
├── Backend (localhost:8000) - Docker Container
│   ├── FastAPI + LiteLLM
│   ├── SSE streaming
│   └── Multi-provider support
│
└── Redis (localhost:6379) - Docker Container
    └── Rate limiting & caching
```

## 📚 Documentation

- [Product Requirements Document](./docs/quorum-prd.md)
- [Technical Architecture](./FINAL_ARCHITECTURE.md)
- [Tech Stack Consensus](./docs/TECH_STACK_CONSENSUS.md)
- [Phase 1 Research Findings](./docs/phase1-research-findings.md)

## 🎯 Phase 2 Features: Sequential Multi-LLM Debates

### Quick Start (V2 Debates)

Access the V2 debate interface at `http://localhost:3000/debate-v2`

**Key Features:**
- Configure 2-4 AI agents with custom system prompts
- Select from multiple LLM providers (OpenAI, Anthropic, Google, Mistral)
- Choose 1-5 rounds of sequential debate
- Manual control: pause, resume, or stop at any time
- Real-time cost and token tracking
- Formatted markdown summary export

### API Endpoints (V2)

**Base URL:** `http://localhost:8000/api/v1/debates/v2`

#### 1. Create Debate
```http
POST /api/v1/debates/v2
Content-Type: application/json

{
  "topic": "Should AI development be open source?",
  "participants": [
    {
      "name": "Agent 1",
      "model": "gpt-4o",
      "system_prompt": "You are an advocate for open source AI.",
      "temperature": 0.7
    },
    {
      "name": "Agent 2",
      "model": "claude-3-5-sonnet-20241022",
      "system_prompt": "You are a proponent of controlled AI development.",
      "temperature": 0.7
    }
  ],
  "max_rounds": 2,
  "context_window_rounds": 10,
  "cost_warning_threshold": 1.0
}
```

**Response:**
```json
{
  "id": "debate_v2_abc123",
  "status": "initialized",
  "current_round": 1,
  "current_turn": 0,
  "config": { ... },
  "total_cost": 0.0
}
```

#### 2. Get Next Turn (SSE Stream)
```http
GET /api/v1/debates/v2/{debate_id}/next-turn
Accept: text/event-stream
```

**Stream Events:**
```
event: participant_start
data: {"participant_name": "Agent 1", "model": "gpt-4o"}

event: chunk
data: {"text": "I believe that open source..."}

event: participant_complete
data: {"participant_name": "Agent 1", "tokens_used": 150, "cost": 0.002}

event: round_complete
data: {"round": 1, "total_cost": 0.005}

event: debate_complete
data: {"reason": "All rounds completed"}
```

#### 3. Get Debate Status
```http
GET /api/v1/debates/v2/{debate_id}
```

#### 4. Stop Debate
```http
POST /api/v1/debates/v2/{debate_id}/stop
```

#### 5. Pause Debate
```http
POST /api/v1/debates/v2/{debate_id}/pause
```

#### 6. Resume Debate
```http
POST /api/v1/debates/v2/{debate_id}/resume
```

#### 7. Get Summary
```http
GET /api/v1/debates/v2/{debate_id}/summary
```

**Response:**
```json
{
  "debate_id": "debate_v2_abc123",
  "topic": "Should AI development be open source?",
  "status": "completed",
  "rounds_completed": 2,
  "total_rounds": 2,
  "participants": ["Agent 1", "Agent 2"],
  "participant_stats": [
    {
      "name": "Agent 1",
      "model": "gpt-4o",
      "total_tokens": 500,
      "total_cost": 0.015,
      "average_response_time_ms": 1200.0,
      "response_count": 2
    }
  ],
  "total_cost": 0.030,
  "markdown_transcript": "# Debate Transcript\n\n..."
}
```

### State Machine (XState)

The V2 debate UI uses XState v5 for robust state management:

```
CONFIGURING → READY → RUNNING → COMPLETED
                ↓         ↓
              ERROR     PAUSED
                         ↓
                      RUNNING
```

**States:**
- **CONFIGURING**: User configures participants and rounds
- **READY**: Configuration validated, ready to start
- **RUNNING**: Debate in progress, streaming responses
- **PAUSED**: Debate paused, can resume
- **COMPLETED**: All rounds complete or manually stopped
- **ERROR**: Error occurred, can retry

### Backend Testing

Run the comprehensive test suite:

```bash
cd backend
python3 -m pytest tests/ -v

# Results: 34 tests passing
# - 13 API route tests
# - 13 Sequential debate service tests
# - 8 Summary service tests
```

## 🛠️ Development

### Development Workflow

**Recommended Setup:**
- Frontend runs locally with `npm run dev` for instant hot-reload
- Backend services run in Docker for consistency

**Quick Start:**
```bash
./scripts/dev.sh
```

### Frontend Development
The frontend runs locally for the best development experience:
```bash
cd frontend
npm install
npm run dev       # Start dev server
npm run test      # Run tests
npm run lint      # Lint code
```

### Backend Development
Backend runs in Docker with hot-reload enabled:
```bash
# Start backend
docker-compose -f docker/development/docker-compose.yml up

# View logs
docker-compose -f docker/development/docker-compose.yml logs -f backend

# Run backend tests (inside container)
docker exec quorum-backend-dev pytest --cov=app

# Or run locally (without Docker)
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

### Running Tests
```bash
# Frontend tests (local)
cd frontend
npm run test:coverage

# Backend tests (Docker)
docker exec quorum-backend-dev pytest --cov=app

# Backend tests (local)
cd backend
pytest --cov=app
```

### Environment Variables
- **Root `.env`**: Backend configuration (API keys, CORS, etc.)
- **Frontend `.env.local`**: Frontend-specific vars (auto-created by dev script)

### Useful Commands
```bash
# Start everything
./scripts/dev.sh

# Stop backend services
./scripts/stop.sh

# Rebuild backend container
docker-compose -f docker/development/docker-compose.yml up --build

# View backend logs
docker-compose -f docker/development/docker-compose.yml logs -f

# Reset everything
docker-compose -f docker/development/docker-compose.yml down -v
```

## 🗺️ Roadmap

### Phase 2: Multi-LLM Debate Engine (Weeks 3-4)
- Multi-provider support (Anthropic, Google, Mistral)
- XState debate state machine
- Parallel streaming (2-4 debaters)
- Context management
- Token counting and cost tracking

### Phase 3: Judge & Features (Weeks 5-6)
- Judge agent with structured output
- Debate format selection
- Persona assignment
- Export functionality

### Phase 4: Polish & Testing (Weeks 7-8)
- Comprehensive test suite
- Error handling
- Security audit
- Performance optimization

### Phase 5: Deployment & Launch (Week 9)
- Production deployment
- Community guidelines
- Public release

## 📝 License

MIT License - see [LICENSE](./LICENSE) for details

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📞 Support

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/quorum/issues)
- Documentation: [Full docs](./docs/)

---

**Built with ❤️ using Next.js, FastAPI, and LiteLLM**
