# Phase 2: Multi-LLM Debate Engine - Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      React Frontend (Next.js 15)                      │  │
│  │                                                                        │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│  │  │ Config Panel     │  │ Debate Arena     │  │ Cost Tracker     │  │  │
│  │  │ - Topic input    │  │ - Participants   │  │ - Real-time $    │  │  │
│  │  │ - Participants   │  │ - Streaming text │  │ - Warnings       │  │  │
│  │  │ - Judge          │  │ - Round timeline │  │ - Model costs    │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  │  │
│  │                                                                        │  │
│  └────────────────────────────────┬───────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
                                      │ HTTP / SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STATE MANAGEMENT LAYER                             │
│                                                                               │
│  ┌────────────────────────────────┐    ┌────────────────────────────────┐  │
│  │      XState Machine v5         │    │      Zustand Store             │  │
│  │  (Business Logic)              │    │  (UI State)                    │  │
│  │                                │    │                                │  │
│  │  States:                       │    │  - Stream buffers              │  │
│  │  • idle                        │    │  - UI toggles                  │  │
│  │  • initializing                │    │  - Optimistic updates          │  │
│  │  • awaitingArguments           │    │  - View preferences            │  │
│  │  • debating (rounds 1-N)       │    │  - Cached data                 │  │
│  │  • judgeEvaluating             │    │                                │  │
│  │  • completed                   │    │  Performance:                  │  │
│  │  • paused                      │    │  - Batched updates (100ms)     │  │
│  │  • error                       │    │  - Selective subscriptions     │  │
│  │                                │    │  - Memoized selectors          │  │
│  │  Events:                       │    │                                │  │
│  │  - START_DEBATE                │    │  Persistence:                  │  │
│  │  - ROUND_COMPLETE              │    │  - localStorage (preferences)  │  │
│  │  - VERDICT_READY               │    │                                │  │
│  │  - PAUSE / RESUME / STOP       │    │                                │  │
│  │  - ERROR / RETRY               │    │                                │  │
│  └────────────────────────────────┘    └────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                                        │ REST API + SSE
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND API LAYER (FastAPI)                          │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    Debate Orchestrator                              │    │
│  │                                                                      │    │
│  │  Core Services:                                                     │    │
│  │  • Debate Coordinator (state management)                            │    │
│  │  • SSE Stream Multiplexer (Redis Pub/Sub)                          │    │
│  │  • Token Counter (tiktoken)                                         │    │
│  │  • Cost Tracker (real-time calculation)                            │    │
│  │  • Judge Evaluator (verdict generation)                            │    │
│  │                                                                      │    │
│  │  API Endpoints (11 total):                                          │    │
│  │  POST   /api/v1/debates                 - Create debate             │    │
│  │  GET    /api/v1/debates/:id/stream      - SSE stream               │    │
│  │  GET    /api/v1/debates/:id/status      - Get status               │    │
│  │  POST   /api/v1/debates/:id/rounds      - Submit round             │    │
│  │  POST   /api/v1/debates/:id/judge       - Trigger judge            │    │
│  │  POST   /api/v1/debates/:id/pause       - Pause debate             │    │
│  │  POST   /api/v1/debates/:id/resume      - Resume debate            │    │
│  │  POST   /api/v1/debates/:id/stop        - Stop debate              │    │
│  │  GET    /api/v1/debates/:id/transcript  - Export transcript        │    │
│  │  GET    /api/v1/debates                 - List debates             │    │
│  │  DELETE /api/v1/debates/:id             - Delete debate            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
└───────┬─────────────────────────────────┬─────────────────────────────┬─────┘
        │                                 │                             │
        │ Parallel API Calls              │ Pub/Sub                     │ Persist
        ▼                                 ▼                             ▼
┌──────────────────┐            ┌──────────────────┐         ┌──────────────────┐
│  LLM APIs        │            │     Redis        │         │   PostgreSQL     │
│                  │            │                  │         │                  │
│ • Anthropic      │            │ • Pub/Sub        │         │ • debates        │
│   Claude 3.5     │            │ • Caching        │         │ • rounds         │
│   Sonnet, Opus   │            │ • Rate limiting  │         │ • participants   │
│                  │            │ • Multi-instance │         │ • verdicts       │
│ • OpenAI         │            │   sync           │         │ • costs          │
│   GPT-4 Turbo    │            │                  │         │ • state_snapshots│
│                  │            └──────────────────┘         └──────────────────┘
│ • Google Gemini  │
│   Pro            │
│                  │
│ • Mistral Large  │
│                  │
│ All streaming    │
│ SSE enabled      │
└──────────────────┘
```

---

## Data Flow Overview

### 1. Initialization Flow

```
User fills config
    ↓
Frontend validates
    ↓
XState: idle → initializing
    ↓
POST /api/v1/debates
    ↓
Backend creates debate_id
    ↓
Store in PostgreSQL
    ↓
Return 201 + streamUrl
    ↓
Frontend opens SSE connection
    ↓
XState: initializing → awaitingArguments
```

### 2. Debate Execution Flow

```
Backend starts round
    ↓
Parallel LLM API calls (asyncio.gather)
    ├─ Anthropic Claude ───┐
    ├─ OpenAI GPT-4 ───────┤
    └─ Google Gemini ──────┴─ All streaming
         ↓
    SSE Multiplexer
    ├─ Count tokens (tiktoken)
    ├─ Calculate costs
    └─ Publish to Redis
         ↓
    Forward to all SSE clients
         ↓
    Frontend receives chunks
    ├─ Buffer in Zustand (every 100ms)
    └─ Display with typewriter effect
         ↓
    All participants complete
         ↓
    XState: ROUND_COMPLETE
         ↓
    Next round or judge evaluation
```

### 3. Cost Tracking Flow

```
LLM response chunk
    ↓
Token counter (tiktoken)
    ↓
Calculate cost (model pricing)
    ↓
Update cost tracker
    ├─ total_cost
    ├─ cost_by_model
    └─ token_usage
    ↓
Check thresholds
    ├─ warn_at: $3.00
    └─ limit: $5.00
    ↓
If threshold reached:
    ├─ Emit SSE cost_warning
    └─ Display modal
    ↓
If limit exceeded:
    ├─ Force stop debate
    └─ XState: debating → error
```

### 4. Judge Evaluation Flow

```
All rounds complete
    ↓
Compile transcript
    ↓
Call judge LLM API (streaming)
    ↓
Stream verdict chunks via SSE
    ↓
Parse verdict + scores
    ↓
Store in PostgreSQL
    ↓
XState: judgeEvaluating → completed
    ↓
Display final results
```

---

## Component Architecture

### Frontend Component Tree

```
app/debate/page.tsx
    └─ DebateContainer (Root)
        ├─ DebateConfigPanel
        │   ├─ TopicInput
        │   ├─ FormatSelector
        │   ├─ ParticipantConfigurator
        │   │   └─ ModelSelector
        │   ├─ JudgeConfigurator
        │   └─ AdvancedSettings
        │
        ├─ DebateArena (Active Debate)
        │   ├─ DebateHeader
        │   │   ├─ TopicDisplay
        │   │   ├─ StateIndicator
        │   │   └─ RoundProgress
        │   │
        │   ├─ ParticipantGrid
        │   │   └─ ParticipantPanel[] (2-4)
        │   │       ├─ ParticipantHeader
        │   │       ├─ StreamingResponse
        │   │       │   ├─ TypewriterText
        │   │       │   └─ StreamingIndicator
        │   │       └─ ParticipantMetrics
        │   │
        │   ├─ JudgePanel (Evaluation)
        │   │   ├─ JudgeHeader
        │   │   ├─ StreamingVerdict
        │   │   └─ ScoreCards
        │   │
        │   └─ RoundTimeline
        │       └─ RoundCard[] (History)
        │
        ├─ CostTracker (Floating)
        │   ├─ TotalCostDisplay
        │   ├─ ModelBreakdown
        │   ├─ CostWarningModal
        │   └─ LimitProgressBar
        │
        └─ DebateControls (Toolbar)
            ├─ StartButton
            ├─ PauseButton
            ├─ ResumeButton
            ├─ StopButton
            └─ ExportMenu
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend Framework** | Next.js 15 + React 19 | Server components, routing |
| **State Machine** | XState v5 | Debate flow logic |
| **UI State** | Zustand | Performance-optimized UI state |
| **Styling** | Tailwind CSS + shadcn/ui | Component styling |
| **Testing** | Vitest + Testing Library | Unit and integration tests |
| **Backend API** | FastAPI | RESTful API + SSE |
| **Database** | PostgreSQL | Persistent storage |
| **Cache/Pub-Sub** | Redis | Multi-instance sync |
| **Token Counting** | tiktoken | Accurate token estimation |
| **LLM APIs** | Anthropic, OpenAI, Google, Mistral | Multi-model debate |

---

## Key Architectural Decisions

### 1. XState for Business Logic
**Why:** Deterministic state transitions, visual debugging, built-in error handling

**Alternatives Considered:**
- Redux: Too verbose, unnecessary complexity
- React Context: No state machine semantics
- Custom reducer: Reinventing the wheel

**Result:** Clean, testable, maintainable state logic

---

### 2. Zustand for UI State
**Why:** Simple API, excellent performance, smaller bundle

**Alternatives Considered:**
- Redux: Overkill for UI state
- MobX: More complex mental model
- Jotai: Good but less mature

**Result:** Fast UI updates without XState overhead

---

### 3. SSE over WebSocket
**Why:** Simpler protocol, automatic reconnection, HTTP-based

**Alternatives Considered:**
- WebSocket: More complex, bidirectional (unnecessary)
- Long polling: Inefficient for streaming
- GraphQL subscriptions: Too heavy

**Result:** Reliable one-way streaming with minimal complexity

---

### 4. Redis Pub/Sub for Scaling
**Why:** Horizontal scaling, multi-instance sync, low latency

**Alternatives Considered:**
- In-memory only: Single instance limitation
- RabbitMQ: Overkill for pub/sub
- Kafka: Too complex for use case

**Result:** Easy horizontal scaling for SSE multiplexing

---

### 5. PostgreSQL for Persistence
**Why:** ACID compliance, JSON support, battle-tested

**Alternatives Considered:**
- MongoDB: Unnecessary NoSQL overhead
- DynamoDB: Vendor lock-in
- SQLite: Not suitable for multi-instance

**Result:** Reliable persistent storage with JSONB for state snapshots

---

## Performance Characteristics

### Latency Targets

| Operation | Target | Actual (Expected) |
|-----------|--------|-------------------|
| SSE Connection Establish | < 100ms | ~50ms |
| LLM First Chunk | < 2000ms | 500-1500ms |
| Token Counting | < 1ms | ~0.5ms |
| Cost Calculation | < 1ms | ~0.3ms |
| Frontend Render | < 16ms | ~8ms (60fps) |
| State Persistence | < 10ms | ~5ms |
| Database Write | < 50ms | ~20ms |

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent Debates | 100+ | Per backend instance |
| SSE Connections | 500+ | With Redis Pub/Sub |
| LLM API Calls | 20/sec | Across all models |
| Token Processing | 10K/sec | tiktoken throughput |
| Frontend Updates | 60fps | React render rate |

---

## Scalability Strategy

### Horizontal Scaling

```
┌─────────────┐
│ Load Balancer│
└──────┬──────┘
       │
       ├────────────┬────────────┐
       ▼            ▼            ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│ Backend    │ │ Backend    │ │ Backend    │
│ Instance 1 │ │ Instance 2 │ │ Instance N │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │
      └──────────────┼──────────────┘
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
      ┌─────────┐         ┌──────────┐
      │  Redis  │         │PostgreSQL│
      │ Pub/Sub │         │ (Primary)│
      └─────────┘         └──────────┘
```

**Key Points:**
- Redis Pub/Sub synchronizes SSE events across instances
- PostgreSQL stores persistent state
- Stateless backend instances (except SSE connections)
- Auto-scaling based on CPU/memory usage

### Database Optimization

```sql
-- Indexes for fast queries
CREATE INDEX idx_debates_status ON debates(status);
CREATE INDEX idx_debates_created_at ON debates(created_at DESC);
CREATE INDEX idx_rounds_debate_id ON rounds(debate_id);

-- Partitioning for large tables
CREATE TABLE rounds_2024_12 PARTITION OF rounds
FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
```

---

## Security Considerations

### API Security
- ✅ Rate limiting (100 req/min per IP)
- ✅ API key validation for LLM providers
- ✅ Input validation (Pydantic models)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS prevention (React auto-escaping)
- ✅ CORS configuration (whitelist origins)

### Data Privacy
- ✅ No API keys stored in browser
- ✅ Encrypted API keys in backend (Vault)
- ✅ Debate data retention policy (30 days)
- ✅ Optional user authentication (Phase 3)

---

## Monitoring & Observability

### Metrics to Track

```typescript
// Backend Metrics
- debate_created_total
- debate_completed_total
- debate_errors_total
- llm_api_latency_seconds
- token_count_total
- cost_total_usd
- sse_connections_active

// Frontend Metrics
- page_load_time_ms
- component_render_time_ms
- sse_reconnections_total
- state_transitions_total
```

### Logging Strategy

```
[INFO] Debate deb_123 created (topic: "AI Regulation")
[DEBUG] Participant part_1 streaming chunk (25 tokens)
[WARN] Cost threshold reached: $3.15 / $5.00 (63%)
[ERROR] LLM API timeout: anthropic-claude (90s exceeded)
```

---

## Disaster Recovery

### State Recovery

1. **Frontend Crash:**
   - Reload from localStorage (< 1 hour old)
   - Reconnect SSE stream
   - Resume from last known state

2. **Backend Crash:**
   - Load debate state from PostgreSQL
   - Reconnect to LLM APIs
   - Notify clients of disruption
   - Resume from last completed round

3. **Database Failure:**
   - Automated backups (hourly)
   - Point-in-time recovery
   - Read replicas for high availability

---

## Documentation Index

| Document | Lines | Size | Purpose |
|----------|-------|------|---------|
| [debate-state-machine.md](./debate-state-machine.md) | 740 | 20K | XState FSM with 11 states |
| [api-contracts.md](./api-contracts.md) | 854 | 18K | REST API + SSE specifications |
| [component-hierarchy.md](./component-hierarchy.md) | 1,150 | 31K | React component architecture |
| [data-flow.md](./data-flow.md) | 832 | 28K | Data flow diagrams |
| [state-management.md](./state-management.md) | 994 | 26K | XState + Zustand strategy |
| [README.md](./README.md) | 321 | 8.6K | Quick reference guide |
| **TOTAL** | **4,891** | **131K** | Complete architecture |

---

## Next Steps

### Immediate (Week 1)
1. ✅ Architecture documentation complete
2. ⏳ Set up project structure (`/frontend`, `/backend`)
3. ⏳ Initialize XState machine skeleton
4. ⏳ Create Zustand store boilerplate
5. ⏳ Build DebateConfigPanel component

### Short-term (Week 2-4)
- Implement full XState machine with all states
- Build ParticipantPanel with streaming
- Create SSE client and event router
- Set up FastAPI backend skeleton
- Implement PostgreSQL schema

### Mid-term (Week 5-6)
- Integrate LLM APIs (Anthropic, OpenAI, Google)
- Implement parallel streaming
- Build token counting service
- Add cost tracking system
- Create judge evaluation logic

### Long-term (Week 7-8)
- Comprehensive testing suite
- Performance optimization
- Documentation and examples
- Deployment guide
- Launch Phase 2! 🚀

---

**Status:** ✅ Architecture Complete - Ready for Implementation

**Total Documentation:** 4,891 lines across 6 files

**Estimated Implementation Time:** 8 weeks (2 developers)

**Phase 2 Launch Target:** Q1 2025
