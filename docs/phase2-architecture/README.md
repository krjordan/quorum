# Phase 2: Multi-LLM Debate Engine - Architecture Documentation

## Overview

Comprehensive architecture documentation for the multi-LLM debate system featuring parallel debate execution, real-time streaming, cost tracking, and intelligent state management.

## Architecture Documents

### 1. [Debate State Machine](./debate-state-machine.md)
**XState Finite State Machine with 11 States**

- Complete FSM definition with state transitions
- 11 states: idle → initializing → awaitingArguments → debating → judgeEvaluating → completed (+ paused, error)
- Context structure (participants, rounds, costs, verdict)
- Event types and guard conditions
- Error handling and recovery flows
- TypeScript interface definitions
- Integration examples with React

**Key Highlights:**
- Deterministic state transitions
- Cost limit guards
- Retry logic with exponential backoff
- State persistence for crash recovery

---

### 2. [API Contracts](./api-contracts.md)
**RESTful Backend API with Server-Sent Events**

- **11 API Endpoints:**
  - POST `/api/v1/debates` - Create debate
  - GET `/api/v1/debates/{id}/stream` - SSE multi-participant stream
  - GET `/api/v1/debates/{id}/status` - Current state
  - POST `/api/v1/debates/{id}/rounds` - Submit round
  - POST `/api/v1/debates/{id}/judge` - Trigger judge
  - POST `/api/v1/debates/{id}/pause` - Pause debate
  - POST `/api/v1/debates/{id}/resume` - Resume debate
  - POST `/api/v1/debates/{id}/stop` - Stop debate
  - GET `/api/v1/debates/{id}/transcript` - Export transcript
  - GET `/api/v1/debates` - List debates
  - DELETE `/api/v1/debates/{id}` - Delete debate

- **8 SSE Event Types:**
  - `status`, `participant`, `round_complete`, `judge`, `verdict`, `cost_update`, `cost_warning`, `error`, `complete`

- Complete request/response schemas
- Error handling (RFC 7807)
- Reconnection strategy
- WebSocket alternative design

**Key Highlights:**
- SSE for real-time streaming
- Multi-participant parallel events
- Token counting integration
- Cost tracking per model

---

### 3. [Component Hierarchy](./component-hierarchy.md)
**React Component Architecture with 20+ Components**

- **Component Tree:**
  ```
  DebateContainer
  ├── DebateConfigPanel (topic, participants, judge)
  ├── DebateArena
  │   ├── ParticipantPanel[] (2-4 debaters)
  │   │   └── StreamingResponse (typewriter effect)
  │   ├── JudgePanel (verdict, scores)
  │   └── RoundTimeline
  ├── CostTracker (floating overlay)
  └── DebateControls (start, pause, export)
  ```

- Component specifications with props
- State integration patterns (XState + Zustand)
- Custom hooks (`useDebateMachine`, `useDebateSSE`, `useTypewriterEffect`)
- Responsive design breakpoints
- Accessibility features (ARIA, keyboard nav)
- Performance optimizations (virtual scrolling, memoization)
- Testing strategy

**Key Highlights:**
- Separation of concerns (business logic vs UI)
- Stream buffering for performance
- Optimistic UI updates
- Export functionality (JSON, Markdown, HTML)

---

### 4. [Data Flow](./data-flow.md)
**Comprehensive Data Flow Diagrams**

- **5 Major Flows:**
  1. Debate Initialization (User → Backend → DB → SSE)
  2. Round Execution (Parallel LLM calls → Streaming)
  3. Cost Tracking & Warning (Real-time token counting)
  4. Judge Evaluation (Transcript compilation → Verdict)
  5. Error Handling (Timeout recovery, rate limit handling)

- Detailed sequence diagrams
- Token counting flow
- Multi-client synchronization (Redis Pub/Sub)
- State persistence strategy
- Optimistic updates & rollback

**Key Highlights:**
- Parallel LLM API calls with asyncio
- SSE multiplexing across models
- Real-time cost calculation
- Horizontal scaling with Redis

---

### 5. [State Management](./state-management.md)
**Hybrid XState + Zustand Architecture**

- **XState (Business Logic):**
  - Debate lifecycle states
  - State transitions and guards
  - Event routing
  - Context management
  - State persistence

- **Zustand (UI State):**
  - Stream buffers (high-frequency updates)
  - UI toggles and visibility
  - Optimistic updates
  - View preferences (persisted)
  - Client-side caching

- Integration patterns
- Performance optimizations (batching, selective subscriptions)
- Testing strategies
- Debugging tools (XState Inspector, Redux DevTools)

**Key Highlights:**
- Clear separation of concerns
- Stream batching (100ms intervals)
- Selective re-renders
- State restoration on page reload

---

## Quick Reference

### State Machine States

```
idle → initializing → awaitingArguments → debating → judgeEvaluating → completed
                                            ↓           ↓
                                         paused      error
```

### API Flow

```
POST /debates
  ↓
GET /debates/:id/stream (SSE)
  ↓ (events: participant, round_complete, judge, verdict)
GET /debates/:id/transcript
```

### Component Integration

```typescript
// Container
const [state, send] = useMachine(debateMachine);  // XState
const { streamBuffers } = useDebateUIStore();      // Zustand

// Streaming
useDebateSSE(debateId, send);                      // SSE → XState

// Display
<ParticipantPanel content={streamBuffers.get(id)} />
```

---

## Technology Stack

### Frontend
- **React 19** with Server Components
- **Next.js 15** for routing
- **XState v5** for state machines
- **Zustand** for UI state
- **Tailwind CSS** + **shadcn/ui** for styling
- **Vitest** + **Testing Library** for tests

### Backend (To Implement)
- **FastAPI** for REST API
- **PostgreSQL** for persistence
- **Redis** for pub/sub and caching
- **tiktoken** for token counting
- **asyncio** for parallel LLM calls

### External APIs
- **Anthropic Claude** (3.5 Sonnet, Opus)
- **OpenAI GPT-4** (Turbo)
- **Google Gemini** (Pro)
- **Mistral** (Large)

---

## Implementation Phases

### Phase 2A: Frontend Foundation (Week 1-2)
- [ ] Implement XState debate machine
- [ ] Create Zustand UI store
- [ ] Build core components (ConfigPanel, Arena, ParticipantPanel)
- [ ] Add SSE client with event routing
- [ ] Implement typewriter streaming effect

### Phase 2B: Backend API (Week 3-4)
- [ ] FastAPI debate orchestration
- [ ] PostgreSQL schema and migrations
- [ ] SSE endpoint with Redis pub/sub
- [ ] Token counting service
- [ ] Cost tracking system

### Phase 2C: LLM Integration (Week 5)
- [ ] Anthropic Claude integration
- [ ] OpenAI GPT-4 integration
- [ ] Google Gemini integration
- [ ] Parallel streaming implementation
- [ ] Error handling and retries

### Phase 2D: Judge & Export (Week 6)
- [ ] Judge evaluation logic
- [ ] Verdict parsing and scoring
- [ ] Transcript export (JSON, Markdown, HTML)
- [ ] Cost summary reports
- [ ] Debate analytics

### Phase 2E: Polish & Testing (Week 7-8)
- [ ] Comprehensive unit tests
- [ ] Integration tests (full debate flow)
- [ ] Performance optimization
- [ ] Accessibility audit
- [ ] Documentation and examples

---

## Key Metrics & Goals

### Performance
- SSE connection: < 100ms
- LLM first chunk: 500-1500ms (varies by model)
- Token counting: < 1ms per chunk
- Frontend render: < 16ms (60fps)

### Scalability
- Support 2-4 concurrent debaters
- Handle 5-10 debate rounds
- Real-time cost tracking
- Multi-client synchronization

### Reliability
- 99.9% uptime target
- Automatic retry on transient errors
- State persistence (crash recovery)
- Graceful degradation

---

## Design Decisions

### Why XState?
- Deterministic state transitions
- Visual state machine graphs
- Built-in error handling
- TypeScript-first design
- Excellent debugging tools

### Why Zustand over Redux?
- Simpler API (less boilerplate)
- Better performance (selective subscriptions)
- Built-in immer support
- Smaller bundle size
- Easier to learn

### Why SSE over WebSocket?
- Simpler protocol (HTTP)
- Automatic reconnection
- Better browser support
- Easier to proxy/cache
- Sufficient for one-way streaming

### Why Redis Pub/Sub?
- Horizontal scaling support
- Multi-instance coordination
- Low latency (<1ms)
- Simple API
- Battle-tested

---

## Related Documentation

- [Phase 1: Chat Interface](../phase1-docs/) (if exists)
- [Backend API Implementation Guide](../backend-guide.md) (to be created)
- [Frontend Development Guide](../frontend-guide.md) (to be created)
- [Deployment Guide](../deployment.md) (to be created)

---

## Contact & Support

For questions about this architecture:
1. Review the detailed documents linked above
2. Check the implementation examples in each file
3. Refer to XState and Zustand official documentation
4. Review FastAPI and SSE best practices

---

**Architecture Version:** 1.0.0
**Last Updated:** December 3, 2024
**Status:** ✅ Architecture Complete - Ready for Implementation
