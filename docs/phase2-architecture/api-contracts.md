# Phase 2: Backend API Contracts

## Overview

RESTful API contracts for multi-LLM debate orchestration with Server-Sent Events (SSE) for real-time streaming. All endpoints return JSON except streaming endpoints.

## Base Configuration

```
Base URL: http://localhost:8000/api/v1
Content-Type: application/json
Accept: application/json, text/event-stream
```

## Authentication (Future)

```typescript
// For now: No auth required
// Phase 3: Bearer token authentication
Authorization: Bearer <token>
```

## Error Response Format

All errors follow RFC 7807 Problem Details:

```typescript
interface ErrorResponse {
  type: string;        // Error type URI
  title: string;       // Human-readable title
  status: number;      // HTTP status code
  detail: string;      // Detailed error message
  instance?: string;   // Request ID for tracking
  errors?: Record<string, string[]>; // Validation errors
}
```

**Example:**
```json
{
  "type": "/errors/validation",
  "title": "Validation Failed",
  "status": 422,
  "detail": "Invalid debate configuration",
  "instance": "/api/v1/debates",
  "errors": {
    "participants": ["Minimum 2 participants required"],
    "maxRounds": ["Must be between 1 and 10"]
  }
}
```

## API Endpoints

### 1. Create Debate

**POST** `/api/v1/debates`

Create a new multi-LLM debate session.

#### Request Body

```typescript
interface CreateDebateRequest {
  topic: string;                    // Debate topic (max 500 chars)
  format: 'oxford' | 'lincoln-douglas' | 'roundtable';
  participants: DebateParticipantConfig[];
  judge: JudgeConfig;
  config: DebateSessionConfig;
}

interface DebateParticipantConfig {
  name: string;                     // Display name
  model: ModelConfig;
  position: 'for' | 'against' | 'neutral';
  systemPrompt?: string;            // Custom system prompt
  color?: string;                   // Hex color for UI
}

interface ModelConfig {
  provider: 'anthropic' | 'openai' | 'google' | 'mistral';
  modelId: string;                  // e.g., "claude-3-5-sonnet-20241022"
  temperature?: number;             // 0.0 - 1.0, default 0.7
  maxTokens?: number;               // Default 4096
}

interface JudgeConfig {
  name: string;
  model: ModelConfig;
  evaluationCriteria?: string[];    // Custom judging criteria
}

interface DebateSessionConfig {
  maxRounds: number;                // 1-10, default 5
  timeoutPerRound?: number;         // Seconds, default 120
  costLimit?: number;               // USD, optional
  warnAtCost?: number;              // USD, optional
  autoJudge?: boolean;              // Auto-judge at end, default true
}
```

#### Response (201 Created)

```typescript
interface CreateDebateResponse {
  id: string;                       // Debate UUID
  status: 'initializing';
  topic: string;
  participants: DebateParticipant[];
  judge: Judge;
  config: DebateSessionConfig;
  createdAt: string;                // ISO 8601 timestamp
  streamUrl: string;                // SSE endpoint URL
}

interface DebateParticipant {
  id: string;
  name: string;
  model: string;                    // Full model ID
  position: string;
  color: string;
}

interface Judge {
  id: string;
  name: string;
  model: string;
}
```

#### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/debates \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Should AI development be regulated by government?",
    "format": "oxford",
    "participants": [
      {
        "name": "Pro-Regulation (Claude)",
        "model": {
          "provider": "anthropic",
          "modelId": "claude-3-5-sonnet-20241022",
          "temperature": 0.7
        },
        "position": "for",
        "color": "#FF6B6B"
      },
      {
        "name": "Anti-Regulation (GPT-4)",
        "model": {
          "provider": "openai",
          "modelId": "gpt-4-turbo-preview",
          "temperature": 0.8
        },
        "position": "against",
        "color": "#4ECDC4"
      }
    ],
    "judge": {
      "name": "Judge Claude",
      "model": {
        "provider": "anthropic",
        "modelId": "claude-3-opus-20240229"
      }
    },
    "config": {
      "maxRounds": 5,
      "timeoutPerRound": 90,
      "costLimit": 5.0,
      "warnAtCost": 3.0,
      "autoJudge": true
    }
  }'
```

#### Example Response

```json
{
  "id": "deb_01HZ9X8K7M3QR5TNVWXYZ12345",
  "status": "initializing",
  "topic": "Should AI development be regulated by government?",
  "participants": [
    {
      "id": "part_01HZ9X8K7N1",
      "name": "Pro-Regulation (Claude)",
      "model": "anthropic/claude-3-5-sonnet-20241022",
      "position": "for",
      "color": "#FF6B6B"
    },
    {
      "id": "part_01HZ9X8K7N2",
      "name": "Anti-Regulation (GPT-4)",
      "model": "openai/gpt-4-turbo-preview",
      "position": "against",
      "color": "#4ECDC4"
    }
  ],
  "judge": {
    "id": "judge_01HZ9X8K7N3",
    "name": "Judge Claude",
    "model": "anthropic/claude-3-opus-20240229"
  },
  "config": {
    "maxRounds": 5,
    "timeoutPerRound": 90,
    "costLimit": 5.0,
    "warnAtCost": 3.0,
    "autoJudge": true
  },
  "createdAt": "2024-12-03T05:30:00Z",
  "streamUrl": "/api/v1/debates/deb_01HZ9X8K7M3QR5TNVWXYZ12345/stream"
}
```

#### Validation Rules

- **topic**: Required, 10-500 characters
- **participants**: 2-4 participants required
- **maxRounds**: 1-10 rounds
- **timeoutPerRound**: 30-300 seconds
- **costLimit**: If set, must be > 0.10 USD
- **warnAtCost**: Must be < costLimit

---

### 2. Stream Debate Events

**GET** `/api/v1/debates/{debateId}/stream`

Server-Sent Events (SSE) stream for real-time debate updates.

#### Headers

```
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

#### SSE Event Types

```typescript
type DebateEventType =
  | 'status'           // State machine status update
  | 'participant'      // Participant response chunk
  | 'round_complete'   // Round finished
  | 'judge'            // Judge evaluation chunk
  | 'verdict'          // Final verdict
  | 'cost_update'      // Cost tracking update
  | 'cost_warning'     // Cost threshold warning
  | 'error'            // Error occurred
  | 'complete';        // Debate finished
```

#### Event Formats

**Status Event:**
```typescript
{
  event: 'status',
  data: {
    debateId: string;
    state: 'initializing' | 'awaiting_arguments' | 'debating' |
           'judge_evaluating' | 'completed' | 'error';
    currentRound: number;
    timestamp: string;
  }
}
```

**Participant Event (Streaming Response):**
```typescript
{
  event: 'participant',
  data: {
    participantId: string;
    participantName: string;
    roundNumber: number;
    chunk: string;              // Text chunk
    done: boolean;              // true on final chunk
    tokensUsed?: number;        // Only on done=true
    latencyMs?: number;         // Only on done=true
    timestamp: string;
  }
}
```

**Round Complete Event:**
```typescript
{
  event: 'round_complete',
  data: {
    roundNumber: number;
    responses: Array<{
      participantId: string;
      participantName: string;
      content: string;
      tokensUsed: number;
      latencyMs: number;
    }>;
    totalTokens: number;
    roundCost: number;          // USD
    timestamp: string;
  }
}
```

**Judge Event (Streaming):**
```typescript
{
  event: 'judge',
  data: {
    chunk: string;
    done: boolean;
    timestamp: string;
  }
}
```

**Verdict Event:**
```typescript
{
  event: 'verdict',
  data: {
    winner?: string;            // participant ID or "tie"
    scores: Record<string, {
      score: number;            // 0-100
      strengths: string[];
      weaknesses: string[];
    }>;
    reasoning: string;
    criteria: Record<string, string>;
    tokensUsed: number;
    timestamp: string;
  }
}
```

**Cost Update Event:**
```typescript
{
  event: 'cost_update',
  data: {
    totalCost: number;          // USD
    costByModel: Record<string, number>;
    tokensUsed: {
      total: number;
      byModel: Record<string, {
        inputTokens: number;
        outputTokens: number;
      }>;
    };
    timestamp: string;
  }
}
```

**Cost Warning Event:**
```typescript
{
  event: 'cost_warning',
  data: {
    threshold: number;          // USD
    currentCost: number;        // USD
    percentOfLimit: number;     // If limit set
    message: string;
    timestamp: string;
  }
}
```

**Error Event:**
```typescript
{
  event: 'error',
  data: {
    type: 'model_error' | 'timeout' | 'cost_limit' | 'validation';
    message: string;
    participantId?: string;
    retryable: boolean;
    timestamp: string;
  }
}
```

**Complete Event:**
```typescript
{
  event: 'complete',
  data: {
    debateId: string;
    totalRounds: number;
    finalCost: number;
    duration: number;           // seconds
    verdict: { /* ... */ };
    timestamp: string;
  }
}
```

#### Example SSE Stream

```bash
curl -N -H "Accept: text/event-stream" \
  http://localhost:8000/api/v1/debates/deb_01HZ9X8K7M3QR5TNVWXYZ12345/stream
```

```
event: status
data: {"debateId":"deb_01HZ9X8K7M3QR5TNVWXYZ12345","state":"initializing","currentRound":0,"timestamp":"2024-12-03T05:30:01Z"}

event: status
data: {"debateId":"deb_01HZ9X8K7M3QR5TNVWXYZ12345","state":"awaiting_arguments","currentRound":1,"timestamp":"2024-12-03T05:30:02Z"}

event: participant
data: {"participantId":"part_01HZ9X8K7N1","participantName":"Pro-Regulation (Claude)","roundNumber":1,"chunk":"Government regulation of AI is crucial","done":false,"timestamp":"2024-12-03T05:30:03Z"}

event: participant
data: {"participantId":"part_01HZ9X8K7N1","participantName":"Pro-Regulation (Claude)","roundNumber":1,"chunk":" because of safety concerns...","done":false,"timestamp":"2024-12-03T05:30:03.5Z"}

event: participant
data: {"participantId":"part_01HZ9X8K7N1","participantName":"Pro-Regulation (Claude)","roundNumber":1,"chunk":"","done":true,"tokensUsed":250,"latencyMs":3500,"timestamp":"2024-12-03T05:30:06Z"}

event: cost_update
data: {"totalCost":0.015,"costByModel":{"anthropic/claude-3-5-sonnet-20241022":0.015},"tokensUsed":{"total":250,"byModel":{"anthropic/claude-3-5-sonnet-20241022":{"inputTokens":50,"outputTokens":200}}},"timestamp":"2024-12-03T05:30:06Z"}

event: round_complete
data: {"roundNumber":1,"responses":[...],"totalTokens":500,"roundCost":0.03,"timestamp":"2024-12-03T05:30:12Z"}

event: status
data: {"debateId":"deb_01HZ9X8K7M3QR5TNVWXYZ12345","state":"debating","currentRound":2,"timestamp":"2024-12-03T05:30:12Z"}

# ... more rounds ...

event: status
data: {"debateId":"deb_01HZ9X8K7M3QR5TNVWXYZ12345","state":"judge_evaluating","currentRound":5,"timestamp":"2024-12-03T05:32:00Z"}

event: judge
data: {"chunk":"After careful consideration...","done":false,"timestamp":"2024-12-03T05:32:05Z"}

event: verdict
data: {"winner":"part_01HZ9X8K7N1","scores":{...},"reasoning":"...","timestamp":"2024-12-03T05:32:15Z"}

event: complete
data: {"debateId":"deb_01HZ9X8K7M3QR5TNVWXYZ12345","totalRounds":5,"finalCost":1.25,"duration":135,"verdict":{...},"timestamp":"2024-12-03T05:32:15Z"}
```

#### Reconnection

Clients should reconnect on disconnect:
```typescript
const eventSource = new EventSource('/api/v1/debates/deb_123/stream');

eventSource.addEventListener('error', () => {
  // Browser automatically reconnects
  console.log('Reconnecting...');
});

eventSource.addEventListener('complete', () => {
  eventSource.close();
});
```

---

### 3. Get Debate Status

**GET** `/api/v1/debates/{debateId}/status`

Get current debate status without streaming.

#### Response (200 OK)

```typescript
interface DebateStatusResponse {
  id: string;
  status: DebateState;
  topic: string;
  currentRound: number;
  maxRounds: number;
  participants: DebateParticipant[];
  judge: Judge;
  rounds: DebateRoundSummary[];
  costs: CostSummary;
  verdict?: Verdict;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

interface DebateRoundSummary {
  roundNumber: number;
  responses: Array<{
    participantId: string;
    participantName: string;
    contentPreview: string;     // First 200 chars
    tokensUsed: number;
  }>;
  totalTokens: number;
  roundCost: number;
  timestamp: string;
}

interface CostSummary {
  totalCost: number;
  costByModel: Record<string, number>;
  totalTokens: number;
  tokensByModel: Record<string, {
    inputTokens: number;
    outputTokens: number;
  }>;
}
```

#### Example

```bash
curl http://localhost:8000/api/v1/debates/deb_01HZ9X8K7M3QR5TNVWXYZ12345/status
```

---

### 4. Submit Round Response (Manual Mode)

**POST** `/api/v1/debates/{debateId}/rounds`

Manually trigger next round (when not auto-progressing).

#### Request Body

```typescript
interface SubmitRoundRequest {
  action: 'next_round' | 'skip_to_judge';
}
```

#### Response (202 Accepted)

```typescript
interface SubmitRoundResponse {
  debateId: string;
  currentRound: number;
  status: string;
  message: string;
}
```

---

### 5. Trigger Judge Evaluation

**POST** `/api/v1/debates/{debateId}/judge`

Manually trigger judge evaluation before max rounds.

#### Request Body

```typescript
interface TriggerJudgeRequest {
  reason?: string;  // Optional reason for early judging
}
```

#### Response (202 Accepted)

```typescript
interface TriggerJudgeResponse {
  debateId: string;
  status: 'judge_evaluating';
  message: string;
}
```

---

### 6. Pause Debate

**POST** `/api/v1/debates/{debateId}/pause`

Pause active debate.

#### Response (200 OK)

```typescript
interface PauseDebateResponse {
  debateId: string;
  status: 'paused';
  pausedAt: string;
}
```

---

### 7. Resume Debate

**POST** `/api/v1/debates/{debateId}/resume`

Resume paused debate.

#### Response (200 OK)

```typescript
interface ResumeDebateResponse {
  debateId: string;
  status: string;           // Returns to previous state
  resumedAt: string;
}
```

---

### 8. Stop Debate

**POST** `/api/v1/debates/{debateId}/stop`

Stop debate and trigger judge evaluation.

#### Response (200 OK)

```typescript
interface StopDebateResponse {
  debateId: string;
  status: 'judge_evaluating' | 'completed';
  stoppedAt: string;
  message: string;
}
```

---

### 9. Get Debate Transcript

**GET** `/api/v1/debates/{debateId}/transcript`

Get full debate transcript for export.

#### Query Parameters

- `format`: `json` | `markdown` | `html` (default: `json`)

#### Response (200 OK)

**JSON Format:**
```typescript
interface TranscriptResponse {
  debate: {
    id: string;
    topic: string;
    format: string;
    createdAt: string;
    completedAt: string;
    duration: number;
  };
  participants: DebateParticipant[];
  judge: Judge;
  rounds: Array<{
    roundNumber: number;
    responses: Array<{
      participant: string;
      content: string;
      tokensUsed: number;
    }>;
  }>;
  verdict: Verdict;
  costs: CostSummary;
}
```

**Markdown Format:**
```markdown
# Debate: Should AI development be regulated by government?

**Format:** Oxford Debate
**Date:** 2024-12-03
**Duration:** 2 minutes, 15 seconds

## Participants

1. **Pro-Regulation (Claude)** - For
   - Model: anthropic/claude-3-5-sonnet-20241022

2. **Anti-Regulation (GPT-4)** - Against
   - Model: openai/gpt-4-turbo-preview

## Round 1

### Pro-Regulation (Claude)
Government regulation of AI is crucial...

### Anti-Regulation (GPT-4)
Innovation requires freedom...

[... more rounds ...]

## Judge's Verdict

**Winner:** Pro-Regulation (Claude)

**Scores:**
- Pro-Regulation: 85/100
- Anti-Regulation: 78/100

**Reasoning:**
[Judge's reasoning...]

## Costs
- Total: $1.25 USD
- Total Tokens: 12,500
```

---

### 10. List Debates

**GET** `/api/v1/debates`

List all debates (paginated).

#### Query Parameters

- `status`: Filter by status (optional)
- `limit`: Results per page (default 20, max 100)
- `offset`: Pagination offset (default 0)

#### Response (200 OK)

```typescript
interface ListDebatesResponse {
  debates: DebateSummary[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    hasMore: boolean;
  };
}

interface DebateSummary {
  id: string;
  topic: string;
  status: DebateState;
  participantCount: number;
  currentRound: number;
  maxRounds: number;
  totalCost: number;
  createdAt: string;
  completedAt?: string;
}
```

---

### 11. Delete Debate

**DELETE** `/api/v1/debates/{debateId}`

Delete debate and all associated data.

#### Response (204 No Content)

---

## WebSocket Alternative (Future Consideration)

For more advanced use cases, WebSocket bi-directional communication:

### Connection

```typescript
const ws = new WebSocket('ws://localhost:8000/api/v1/debates/deb_123/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  // Same event structure as SSE
};

// Send control messages
ws.send(JSON.stringify({
  type: 'PAUSE'
}));

ws.send(JSON.stringify({
  type: 'INJECT_CONTEXT',
  data: { additionalContext: '...' }
}));
```

## Rate Limiting

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1638360000
```

- 100 requests per minute per IP
- 10 concurrent debates per IP
- SSE connections count as 1 request (persistent)

## HTTP Status Codes

- **200 OK**: Success
- **201 Created**: Debate created
- **202 Accepted**: Action queued
- **204 No Content**: Deleted
- **400 Bad Request**: Invalid input
- **404 Not Found**: Debate not found
- **422 Unprocessable Entity**: Validation failed
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: LLM API unavailable

## Backend Implementation Notes

1. **SSE Connection Management**: Use Redis pub/sub for multi-instance support
2. **Token Counting**: Use tiktoken for accurate counts
3. **Cost Calculation**: Cache pricing per model, update quarterly
4. **Timeout Handling**: Use asyncio.wait_for for LLM API calls
5. **Error Recovery**: Implement exponential backoff for API retries
6. **State Persistence**: Store state snapshots in PostgreSQL every state transition
7. **Cleanup**: TTL-based cleanup of completed debates (30 days)

## Client-Side Integration

```typescript
// Create debate
const debate = await createDebate(config);

// Subscribe to stream
const eventSource = new EventSource(debate.streamUrl);

eventSource.addEventListener('participant', (e) => {
  const data = JSON.parse(e.data);
  updateParticipantUI(data);
});

eventSource.addEventListener('cost_update', (e) => {
  const data = JSON.parse(e.data);
  updateCostTracker(data);
});

eventSource.addEventListener('verdict', (e) => {
  const data = JSON.parse(e.data);
  displayVerdict(data);
});

eventSource.addEventListener('complete', (e) => {
  eventSource.close();
  showDebateResults();
});
```
