# Phase 2: Data Flow Architecture

## Overview

Comprehensive data flow for multi-LLM debate system, showing how user actions propagate through frontend state machines, backend orchestration, LLM APIs, and back to real-time UI updates.

## High-Level Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Config Panel │  │ Debate Arena │  │ Cost Tracker │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                       │
│         │ User Config      │ Display Updates  │ Cost Updates         │
│         ▼                  ▼                  ▼                       │
│  ┌──────────────────────────────────────────────────────┐           │
│  │              XState Debate Machine                    │           │
│  │  States: idle → initializing → debating → completed  │           │
│  └──────┬────────────────────────┬──────────────────────┘           │
│         │ Send Events            │ State Updates                     │
└─────────┼────────────────────────┼───────────────────────────────────┘
          │                        │
          │ START_DEBATE           │ SSE Events
          │ (POST /debates)        │ (GET /debates/:id/stream)
          ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND API LAYER                             │
│  ┌────────────────────────────────────────────────────────┐         │
│  │           Debate Orchestrator (FastAPI)                │         │
│  │  - Validate config                                     │         │
│  │  - Initialize participants                             │         │
│  │  - Manage SSE connections                              │         │
│  │  - Coordinate rounds                                   │         │
│  └───┬──────────────────┬──────────────────┬─────────────┘         │
│      │                  │                  │                         │
│      │ Store State      │ Parallel LLM     │ Token Count            │
│      ▼                  │ Calls            ▼                         │
│  ┌────────────┐         ▼          ┌────────────────┐               │
│  │ PostgreSQL │    ┌────────┐      │ Token Counter  │               │
│  │ - Debates  │    │ Redis  │      │ (tiktoken)     │               │
│  │ - Rounds   │    │ Pub/Sub│      └───────┬────────┘               │
│  │ - Verdicts │    └────────┘              │                         │
│  └────────────┘                            │ Cost Calculation        │
│                                             ▼                         │
│                                      ┌────────────────┐               │
│                                      │ Cost Tracker   │               │
│                                      │ Service        │               │
│                                      └────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          │ LLM API Calls (parallel)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL LLM APIs                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Anthropic   │  │    OpenAI    │  │    Google    │              │
│  │   Claude     │  │    GPT-4     │  │    Gemini    │              │
│  │              │  │              │  │              │              │
│  │  Streaming   │  │  Streaming   │  │  Streaming   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │ SSE Chunks       │                  │                      │
└─────────┼──────────────────┼──────────────────┼──────────────────────┘
          │                  │                  │
          │ Stream text      │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND STREAM PROCESSOR                          │
│  ┌────────────────────────────────────────────────────────┐         │
│  │         SSE Event Multiplexer                          │         │
│  │  - Buffer LLM chunks                                   │         │
│  │  - Publish to Redis                                    │         │
│  │  - Forward to all connected clients                    │         │
│  │  - Track tokens in real-time                           │         │
│  └────────────────────────────────────────────────────────┘         │
└─────────────┬───────────────────────────────────────────────────────┘
              │ SSE Events
              │ (participant, cost_update, round_complete, etc.)
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FRONTEND SSE HANDLER                               │
│  ┌────────────────────────────────────────────────────────┐         │
│  │         useDebateSSE Hook                              │         │
│  │  - Parse SSE events                                    │         │
│  │  - Route to XState machine                             │         │
│  │  - Buffer chunks in Zustand                            │         │
│  └────────────────────────────────────────────────────────┘         │
└─────────────┬───────────────────────────────────────────────────────┘
              │ Dispatch to XState + Zustand
              ▼
        [Back to USER INTERFACE - Loop Closed]
```

---

## Detailed Flow Breakdowns

### Flow 1: Debate Initialization

```
[User] Fill Config Form
   │
   ├─ Topic: "Should AI be regulated?"
   ├─ Participants: Claude (for), GPT-4 (against)
   ├─ Judge: Claude Opus
   ├─ Max Rounds: 5
   └─ Cost Limit: $5.00
   │
   ▼
[Frontend] Validate Input
   ├─ Check topic length (10-500 chars)
   ├─ Verify 2-4 participants
   └─ Validate cost limits
   │
   ▼
[XState] send({ type: 'START_DEBATE', config })
   │
   ▼ State: idle → initializing
   │
[Frontend] POST /api/v1/debates
   │
   │ Request Body:
   │ {
   │   topic: "Should AI be regulated?",
   │   format: "oxford",
   │   participants: [
   │     { name: "Pro (Claude)", model: { provider: "anthropic", ... } },
   │     { name: "Con (GPT-4)", model: { provider: "openai", ... } }
   │   ],
   │   judge: { name: "Judge", model: { provider: "anthropic", ... } },
   │   config: { maxRounds: 5, costLimit: 5.0, ... }
   │ }
   │
   ▼
[Backend] Debate Orchestrator
   ├─ Generate debate_id: "deb_abc123"
   ├─ Validate API keys exist
   ├─ Initialize LLM clients
   │  ├─ AnthropicClient(model="claude-3-5-sonnet")
   │  └─ OpenAIClient(model="gpt-4-turbo")
   ├─ Store debate in PostgreSQL:
   │  └─ INSERT INTO debates (id, topic, config, status)
   └─ Initialize cost tracker:
      └─ CostTracker(limit=5.0, warn_at=3.0)
   │
   ▼
[Backend] Return 201 Created
   │ Response:
   │ {
   │   id: "deb_abc123",
   │   status: "initializing",
   │   streamUrl: "/api/v1/debates/deb_abc123/stream",
   │   participants: [...],
   │   ...
   │ }
   │
   ▼
[Frontend] Store debateId in XState context
   │
   ▼
[Frontend] Open SSE Connection
   │ GET /api/v1/debates/deb_abc123/stream
   │
   ▼
[XState] send({ type: 'INIT_COMPLETE' })
   │
   ▼ State: initializing → awaitingArguments
```

---

### Flow 2: Round Execution (Parallel LLM Calls)

```
[Backend] Round Start (Round 1)
   │
   ├─ Prepare prompts for each participant
   │  ├─ Participant 1 (Claude): "You are debating FOR AI regulation..."
   │  └─ Participant 2 (GPT-4): "You are debating AGAINST regulation..."
   │
   ▼
[Backend] Parallel LLM API Calls (asyncio.gather)
   │
   ├──────────────────────┬──────────────────────┐
   │                      │                      │
   ▼                      ▼                      ▼
[Anthropic API]      [OpenAI API]         [Google API]
POST /v1/messages    POST /v1/chat/       POST /v1/generate
   │                 completions              │
   │ stream=true        │ stream=true          │
   │                    │                      │
   ▼                    ▼                      ▼
SSE Stream 1       SSE Stream 2         SSE Stream 3
   │                    │                      │
   │ Chunk: "Government" │ Chunk: "Innovation"  │
   │ Chunk: " regulation"│ Chunk: " requires"   │
   │ ...                 │ ...                  │
   │                    │                      │
   ▼                    ▼                      ▼
[Backend] Stream Aggregator
   │
   ├─ For each chunk received:
   │  ├─ Count tokens (tiktoken)
   │  ├─ Calculate cost increment
   │  ├─ Publish to Redis (for horizontal scaling)
   │  └─ Forward to SSE clients
   │
   ▼
[Backend] Emit SSE Events (multiplexed)
   │
   ├─ event: participant
   │  data: { participantId: "part_1", chunk: "Government", done: false }
   │
   ├─ event: participant
   │  data: { participantId: "part_2", chunk: "Innovation", done: false }
   │
   ├─ event: cost_update
   │  data: { totalCost: 0.05, costByModel: {...} }
   │
   └─ ... (continue streaming)
   │
   ▼
[Frontend] SSE Handler (useDebateSSE)
   │
   ├─ Parse events
   ├─ Route to appropriate handler
   │
   ▼
[Zustand] Buffer chunks
   │ streamBuffers.set("part_1", currentText + newChunk)
   │
   ▼
[React] Re-render ParticipantPanel
   │ Display buffered text with typewriter effect
   │
   ▼
[XState] When all streams complete:
   │ send({ type: 'ROUND_COMPLETE', round: {...} })
   │
   ▼ State: debating (round 1) → debating (round 2)
```

---

### Flow 3: Cost Tracking & Warning

```
[Backend] Token Counter (real-time during streaming)
   │
   ├─ For each LLM response chunk:
   │  ├─ Count tokens: tiktoken.encode(chunk)
   │  ├─ Accumulate: total_tokens += chunk_tokens
   │  └─ Calculate cost:
   │     ├─ Claude: input=$3/1M, output=$15/1M
   │     ├─ GPT-4: input=$10/1M, output=$30/1M
   │     └─ total_cost += (tokens * price_per_token)
   │
   ▼
[Backend] Cost Tracker Service
   │
   ├─ Update totals:
   │  ├─ total_cost: $2.85
   │  ├─ cost_by_model:
   │  │  ├─ "anthropic/claude": $1.20
   │  │  └─ "openai/gpt-4": $1.65
   │  └─ token_usage: { total: 15000, by_model: {...} }
   │
   ├─ Check thresholds:
   │  ├─ warn_at: $3.00 (not reached yet)
   │  └─ limit: $5.00 (not reached)
   │
   ▼
[Backend] Emit SSE cost_update every 5 seconds
   │
   │ event: cost_update
   │ data: {
   │   totalCost: 2.85,
   │   costByModel: { "anthropic/claude": 1.20, "openai/gpt-4": 1.65 },
   │   tokensUsed: { total: 15000, ... }
   │ }
   │
   ▼
[Frontend] CostTracker Component
   │
   ├─ Display: "$2.85 / $5.00"
   ├─ Progress bar: 57% (green)
   └─ Model breakdown:
      ├─ Claude: $1.20 (8,000 tokens)
      └─ GPT-4: $1.65 (7,000 tokens)

   ... Later in debate ...

[Backend] Cost exceeds warning threshold ($3.00)
   │
   ├─ Create warning:
   │  └─ CostWarning(threshold=3.0, current=3.15)
   │
   ▼
[Backend] Emit SSE cost_warning
   │
   │ event: cost_warning
   │ data: {
   │   threshold: 3.0,
   │   currentCost: 3.15,
   │   percentOfLimit: 63,
   │   message: "Cost exceeded 60% of limit"
   │ }
   │
   ▼
[Frontend] Display Modal Warning
   │
   ├─ Title: "Cost Warning"
   ├─ Message: "You've used $3.15 of $5.00 (63%)"
   ├─ Actions:
   │  ├─ [Continue] → send({ type: 'ACKNOWLEDGE_WARNING' })
   │  └─ [Stop Debate] → send({ type: 'STOP' })
   │
   ▼
[User] Clicks "Continue"
   │
   ▼
[XState] Mark warning as acknowledged
   │ context.costTracker.warnings[0].acknowledged = true
   │
   ▼
[Debate Continues...]

   ... If cost limit exceeded ($5.00) ...

[Backend] Cost limit check (guard in orchestrator)
   │
   ├─ total_cost: $5.10 >= limit: $5.00
   │
   ▼
[Backend] Force stop debate
   │
   ├─ Cancel active LLM streams
   ├─ Trigger judge evaluation early
   │
   ▼
[Backend] Emit SSE error event
   │
   │ event: error
   │ data: {
   │   type: "cost_limit",
   │   message: "Cost limit of $5.00 exceeded",
   │   retryable: false
   │ }
   │
   ▼
[XState] Transition to error state
   │ State: debating → error
   │
   ▼
[Frontend] Display error message + final costs
```

---

### Flow 4: Judge Evaluation

```
[Backend] All rounds completed (or manual stop)
   │
   ├─ Compile full debate transcript
   │  ├─ Round 1:
   │  │  ├─ Claude: "Government regulation..."
   │  │  └─ GPT-4: "Innovation requires freedom..."
   │  ├─ Round 2:
   │  │  └─ ...
   │  └─ Round 5 (final)
   │
   ▼
[Backend] Prepare judge prompt
   │
   │ system: "You are an impartial debate judge. Evaluate based on:
   │          - Argument strength
   │          - Evidence quality
   │          - Logical consistency
   │          - Rebuttal effectiveness"
   │
   │ user: "Here is the full debate transcript:\n\n[transcript]\n\n
   │         Provide your verdict with scores for each participant."
   │
   ▼
[Backend] Call Judge LLM API (streaming)
   │
   │ POST https://api.anthropic.com/v1/messages
   │ {
   │   model: "claude-3-opus-20240229",
   │   messages: [...],
   │   stream: true
   │ }
   │
   ▼
[Anthropic API] Stream judge response
   │
   │ Chunk: "After careful consideration"
   │ Chunk: " of both arguments,"
   │ Chunk: " the winner is Pro-Regulation"
   │ ...
   │
   ▼
[Backend] Forward judge chunks via SSE
   │
   │ event: judge
   │ data: { chunk: "After careful consideration", done: false }
   │
   │ event: judge
   │ data: { chunk: " of both arguments,", done: false }
   │
   │ ... (continue streaming)
   │
   ▼
[Frontend] JudgePanel displays streaming verdict
   │
   │ "After careful consideration of both arguments, the winner is..."
   │ (typewriter effect)
   │
   ▼
[Backend] Judge stream completes
   │
   ├─ Parse verdict from response
   │  ├─ winner: "part_1" (Claude)
   │  ├─ scores:
   │  │  ├─ Claude: 85/100
   │  │  └─ GPT-4: 78/100
   │  ├─ reasoning: "Pro-Regulation presented stronger evidence..."
   │  └─ criteria:
   │     ├─ "Argument Strength": "Both strong, Pro had edge"
   │     ├─ "Evidence Quality": "Pro cited more sources"
   │     └─ ...
   │
   ├─ Count judge tokens: 1,200 tokens
   ├─ Calculate judge cost: $0.04
   ├─ Update total cost: $5.14
   │
   ▼
[Backend] Store verdict in PostgreSQL
   │
   │ INSERT INTO verdicts (debate_id, winner, scores, reasoning, ...)
   │
   ▼
[Backend] Emit SSE verdict event
   │
   │ event: verdict
   │ data: {
   │   winner: "part_1",
   │   scores: {
   │     "part_1": { score: 85, strengths: [...], weaknesses: [...] },
   │     "part_2": { score: 78, ... }
   │   },
   │   reasoning: "Pro-Regulation presented...",
   │   criteria: {...},
   │   tokensUsed: 1200
   │ }
   │
   ▼
[XState] send({ type: 'VERDICT_READY', verdict })
   │
   ▼ State: judgeEvaluating → completed
   │
   ▼
[Backend] Emit SSE complete event
   │
   │ event: complete
   │ data: {
   │   debateId: "deb_abc123",
   │   totalRounds: 5,
   │   finalCost: 5.14,
   │   duration: 180,
   │   verdict: {...}
   │ }
   │
   ▼
[Frontend] Display DebateResults
   │
   ├─ Winner announcement: "🏆 Pro-Regulation (Claude)"
   ├─ Score cards with breakdown
   ├─ Full transcript viewer
   ├─ Final cost summary
   └─ Export options (JSON, Markdown, HTML)
   │
   ▼
[Frontend] Close SSE connection
   │ eventSource.close()
```

---

## Token Counting Flow

```
[LLM Response Chunk] "Government regulation is necessary"
   │
   ▼
[Backend] Token Counter
   │
   ├─ Use tiktoken library:
   │  └─ tokens = tiktoken.encode("Government regulation is necessary")
   │     └─ Result: [38, 5435, 374, 5995] (4 tokens)
   │
   ├─ Accumulate for current response:
   │  └─ participant_tokens["part_1"] += 4
   │
   ├─ Calculate cost:
   │  ├─ Get model pricing from cache:
   │  │  └─ claude-3-5-sonnet: $3/1M input, $15/1M output
   │  ├─ Determine token type (assume output for responses):
   │  │  └─ price_per_token = $15 / 1,000,000 = $0.000015
   │  └─ cost_increment = 4 * $0.000015 = $0.00006
   │
   ├─ Update cost tracker:
   │  ├─ total_cost += $0.00006
   │  └─ cost_by_model["anthropic/claude"] += $0.00006
   │
   └─ Check if should emit cost_update:
      └─ If 5 seconds elapsed since last update:
         └─ Emit SSE cost_update event
```

---

## Error Handling Flows

### Flow 5A: LLM API Timeout

```
[Backend] Call LLM API with timeout
   │ async with timeout(90):  # 90 second timeout
   │     response = await anthropic_client.stream(...)
   │
   ▼
[LLM API] Takes too long (> 90 seconds)
   │
   ▼
[Backend] asyncio.TimeoutError caught
   │
   ├─ Log error:
   │  └─ logger.error(f"Timeout for participant {part_id}")
   │
   ├─ Create error:
   │  └─ DebateError(type="timeout", participantId=part_id, retryable=true)
   │
   ▼
[Backend] Emit SSE error event
   │
   │ event: error
   │ data: {
   │   type: "timeout",
   │   message: "Anthropic API timeout (90s)",
   │   participantId: "part_1",
   │   retryable: true
   │ }
   │
   ▼
[XState] send({ type: 'ERROR', error })
   │
   ▼ State: debating → error
   │
   ▼
[Frontend] Display ErrorDisplay
   │
   ├─ Message: "Anthropic API timed out"
   ├─ Participant: "Pro-Regulation (Claude)"
   ├─ Actions:
   │  ├─ [Retry] → send({ type: 'RETRY' })
   │  └─ [Stop Debate] → send({ type: 'STOP' })
   │
   ▼
[User] Clicks "Retry"
   │
   ▼
[XState] Check canRetry guard
   │ ├─ error.retryable === true ✓
   │ └─ retryCount < 3 ✓
   │
   ▼ State: error → initializing → debating (resumes)
   │
   ▼
[Backend] Retry failed participant API call
   │ (with exponential backoff)
```

### Flow 5B: Model API Error (Rate Limit)

```
[Backend] Call OpenAI API
   │
   ▼
[OpenAI API] Returns 429 Too Many Requests
   │
   │ Response:
   │ {
   │   error: {
   │     message: "Rate limit exceeded",
   │     type: "rate_limit_error",
   │     code: "rate_limit_exceeded"
   │   }
   │ }
   │
   ▼
[Backend] Catch APIError
   │
   ├─ Parse retry-after header: 60 seconds
   ├─ Create error:
   │  └─ DebateError(type="model_error", retryable=true, retryAfter=60)
   │
   ▼
[Backend] Emit SSE error + automatic retry
   │
   │ event: error
   │ data: {
   │   type: "model_error",
   │   message: "OpenAI rate limit. Retrying in 60s...",
   │   participantId: "part_2",
   │   retryable: true
   │ }
   │
   ▼
[Frontend] Display temporary error banner
   │ "OpenAI rate limited. Auto-retrying in 60s..."
   │
   ▼
[Backend] Wait 60 seconds, then retry
   │ await asyncio.sleep(60)
   │ response = await openai_client.stream(...)
   │
   ▼
[Debate Continues...]
```

---

## State Persistence Flow

```
[XState] State transition occurs
   │ (e.g., debating → judgeEvaluating)
   │
   ▼
[Frontend] Serialize state snapshot
   │
   │ snapshot = {
   │   debateId: "deb_abc123",
   │   state: "judgeEvaluating",
   │   context: {
   │     currentRound: 5,
   │     rounds: [...],
   │     costTracker: {...},
   │     ...
   │   },
   │   timestamp: Date.now()
   │ }
   │
   ▼
[Frontend] Store in localStorage
   │ localStorage.setItem('debate_state', JSON.stringify(snapshot))
   │
   ▼
[Backend] Also persist to PostgreSQL
   │
   │ UPDATE debates
   │ SET
   │   status = 'judge_evaluating',
   │   state_snapshot = $snapshot,
   │   updated_at = NOW()
   │ WHERE id = 'deb_abc123'

   ... Browser refresh or crash ...

[Frontend] Page reload
   │
   ▼
[Frontend] Check localStorage
   │
   │ const saved = localStorage.getItem('debate_state')
   │
   ▼
[Frontend] If snapshot exists and recent (< 1 hour):
   │
   ├─ Restore XState machine state:
   │  └─ machine.start({ snapshot: saved })
   │
   ├─ Reconnect SSE:
   │  └─ GET /api/v1/debates/deb_abc123/stream
   │     (Backend resumes from saved state)
   │
   └─ Resume debate from last known state
```

---

## Optimistic Updates & Rollback

```
[User] Clicks "Pause Debate"
   │
   ▼
[Frontend] Optimistic state update (immediate)
   │
   ├─ XState: State → paused (optimistic)
   ├─ UI: Disable streaming, show "Paused" badge
   │
   ▼
[Frontend] POST /api/v1/debates/:id/pause
   │
   ▼
[Backend] Process pause request
   │
   ├─ Cancel active LLM streams
   ├─ Save state snapshot
   │
   ▼
[Backend] Returns 200 OK
   │
   │ Response:
   │ {
   │   debateId: "deb_abc123",
   │   status: "paused",
   │   pausedAt: "2024-12-03T05:45:00Z"
   │ }
   │
   ▼
[Frontend] Confirm optimistic update
   │ (State already paused, no action needed)

   ... OR if error occurs ...

[Backend] Returns 500 Internal Server Error
   │
   ▼
[Frontend] Rollback optimistic update
   │
   ├─ XState: Revert to previous state (debating)
   ├─ UI: Show error toast: "Failed to pause"
   ├─ Re-enable streaming
   │
   ▼
[User] Sees error message, debate continues
```

---

## Multi-Client Synchronization (Redis Pub/Sub)

```
[Backend Instance 1] Receives SSE connection from Client A
   │
   ▼
[Backend Instance 2] Receives SSE connection from Client B
   │ (Load balanced, different server)
   │
   ▼
[Backend Instance 1] LLM stream chunk received
   │
   │ Chunk: "Government regulation"
   │
   ├─ Forward to Client A via SSE
   │
   └─ Publish to Redis:
      │ PUBLISH debate:deb_abc123 {
      │   event: "participant",
      │   data: { participantId: "part_1", chunk: "Government regulation" }
      │ }
      │
      ▼
[Redis] Broadcast to all subscribers
   │
   ▼
[Backend Instance 2] Subscribed to debate:deb_abc123
   │
   ├─ Receive published message
   │
   └─ Forward to Client B via SSE
      │
      ▼
[Client A] Sees chunk
[Client B] Sees same chunk (synchronized)
```

---

## Summary of Key Data Flows

| Flow | Trigger | Path | Result |
|------|---------|------|--------|
| **Initialization** | User clicks "Start" | Frontend → Backend → DB → SSE Setup | Debate begins |
| **Round Execution** | Backend orchestrator | Backend → LLM APIs (parallel) → SSE → Frontend | Participants respond |
| **Cost Tracking** | Every LLM response | Token Counter → Cost Calculator → SSE → CostTracker | Real-time cost display |
| **Warning** | Cost threshold | Backend → SSE cost_warning → Modal | User notified |
| **Judge Evaluation** | All rounds complete | Backend → Judge LLM → SSE → JudgePanel | Verdict displayed |
| **Error Handling** | LLM API failure | Backend → SSE error → XState → ErrorDisplay | Error shown + retry option |
| **State Persistence** | Every transition | XState → localStorage + PostgreSQL | Crash-resistant |
| **Multi-Client Sync** | SSE events | Backend → Redis Pub/Sub → All Clients | Multiple viewers synchronized |

---

## Performance Metrics

- **SSE Connection**: < 100ms to establish
- **LLM First Chunk**: 500-1500ms latency (varies by model)
- **Token Counting**: < 1ms per chunk
- **Cost Calculation**: < 1ms (cached pricing)
- **Frontend Render**: < 16ms (60fps) for streaming updates
- **State Persistence**: < 5ms to localStorage
- **Database Write**: < 50ms for state snapshot

---

## Scalability Considerations

1. **Horizontal Scaling**: Redis Pub/Sub enables multi-instance backends
2. **Connection Pooling**: Reuse LLM API connections
3. **Rate Limiting**: Queue requests if approaching API limits
4. **Caching**: Cache debate configs, model pricing, token counts
5. **Database Indexes**: Index debates by status, created_at
6. **CDN**: Static assets (React bundle) served via CDN

---

## Next Steps

1. Implement Backend orchestrator with asyncio for parallel LLM calls
2. Build SSE multiplexer with Redis Pub/Sub
3. Create token counting service with tiktoken
4. Implement frontend SSE handler with event routing
5. Add Zustand stream buffering for optimized React updates
6. Build cost tracking service with real-time updates
7. Implement state persistence (localStorage + PostgreSQL)
8. Add error recovery with exponential backoff
