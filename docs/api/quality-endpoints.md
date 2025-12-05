# Quality Monitoring API Endpoints

**Status:** Phase 3 Implementation - Endpoints Created, Services Pending
**Base URL:** `http://localhost:8000/api/v1/quality`
**API Version:** 0.2.0

---

## Overview

The Quality Monitoring API provides real-time conversation quality metrics, contradiction detection, loop detection, and health scoring for multi-agent debates.

### Features
- **Anti-Contradiction Detection** - Identify conflicting statements between participants
- **Loop Detection** - Recognize repetitive conversation patterns
- **Health Scoring** - Real-time quality metrics (0-100 scale)
- **Evidence Grounding** - Track and validate citations
- **SSE Integration** - Real-time quality events streamed via Server-Sent Events

---

## Endpoints

### 1. Get Conversation Quality Metrics

**Endpoint:** `GET /api/v1/quality/conversations/{conversation_id}/quality`

**Description:** Retrieve current quality metrics including overall health score, contradictions, loops, and citation tracking.

**Parameters:**
- `conversation_id` (path, required): Debate/conversation identifier

**Response:** `ConversationQualityResponse`

```json
{
  "conversation_id": "debate_v2_123456",
  "overall_score": 78.5,
  "score_breakdown": {
    "coherence": 85.0,
    "diversity": 72.0,
    "engagement": 90.0,
    "evidence_quality": 65.0,
    "progression": 80.0
  },
  "contradictions_count": 2,
  "loops_detected": 1,
  "total_citations": 15,
  "missing_citations": 8,
  "rounds_analyzed": 3,
  "last_updated": "2024-12-04T12:30:45.123456"
}
```

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/quality" \
  -H "accept: application/json"
```

**Status Codes:**
- `200 OK` - Successfully retrieved quality metrics
- `404 Not Found` - Conversation not found
- `500 Internal Server Error` - Server error

---

### 2. List Detected Contradictions

**Endpoint:** `GET /api/v1/quality/conversations/{conversation_id}/contradictions`

**Description:** Get all contradictions detected in a conversation with optional filtering and pagination.

**Parameters:**
- `conversation_id` (path, required): Debate/conversation identifier
- `status` (query, optional): Filter by status (`detected`, `acknowledged`, `resolved`, `dismissed`)
- `severity` (query, optional): Filter by severity (`low`, `medium`, `high`, `critical`)
- `page` (query, optional, default=1): Page number
- `page_size` (query, optional, default=50): Items per page (max 100)

**Response:** `ContradictionListResponse`

```json
{
  "conversation_id": "debate_v2_123456",
  "contradictions": [
    {
      "id": "contradiction_abc123",
      "conversation_id": "debate_v2_123456",
      "statement_1": "AI should be completely open source",
      "statement_2": "We need strict proprietary controls on AI development",
      "participant_1": "Agent 1",
      "participant_2": "Agent 1",
      "round_1": 1,
      "round_2": 3,
      "similarity_score": 0.89,
      "severity": "high",
      "status": "detected",
      "explanation": "Agent 1 contradicted their initial position on open source AI",
      "detected_at": "2024-12-04T12:30:45.123456",
      "resolved_at": null
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

**Curl Examples:**
```bash
# Get all contradictions
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/contradictions" \
  -H "accept: application/json"

# Filter by status and severity
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/contradictions?status=detected&severity=high" \
  -H "accept: application/json"

# Pagination
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/contradictions?page=2&page_size=25" \
  -H "accept: application/json"
```

**Status Codes:**
- `200 OK` - Successfully retrieved contradictions
- `404 Not Found` - Conversation not found
- `500 Internal Server Error` - Server error

---

### 3. Resolve Contradiction

**Endpoint:** `POST /api/v1/quality/contradictions/{contradiction_id}/resolve`

**Description:** Mark a contradiction as resolved, acknowledged, or dismissed with explanatory notes.

**Parameters:**
- `contradiction_id` (path, required): Contradiction identifier

**Request Body:** `ContradictionResolution`

```json
{
  "resolution_note": "Participant clarified their position evolved based on new evidence",
  "new_status": "resolved"
}
```

**Response:** `ContradictionResponse`

```json
{
  "id": "contradiction_abc123",
  "conversation_id": "debate_v2_123456",
  "statement_1": "AI should be completely open source",
  "statement_2": "We need strict proprietary controls on AI development",
  "participant_1": "Agent 1",
  "participant_2": "Agent 1",
  "round_1": 1,
  "round_2": 3,
  "similarity_score": 0.89,
  "severity": "high",
  "status": "resolved",
  "explanation": "Agent 1 contradicted their initial position on open source AI",
  "detected_at": "2024-12-04T12:30:45.123456",
  "resolved_at": "2024-12-04T12:45:12.345678"
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/quality/contradictions/contradiction_abc123/resolve" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "resolution_note": "Participant clarified their position evolved based on new evidence",
    "new_status": "resolved"
  }'
```

**Status Codes:**
- `200 OK` - Successfully resolved contradiction
- `400 Bad Request` - Invalid status transition
- `404 Not Found` - Contradiction not found
- `500 Internal Server Error` - Server error

---

### 4. List Detected Loops

**Endpoint:** `GET /api/v1/quality/conversations/{conversation_id}/loops`

**Description:** Get all conversational loops detected in a conversation with optional filtering.

**Parameters:**
- `conversation_id` (path, required): Debate/conversation identifier
- `loop_type` (query, optional): Filter by type (`repetitive_argument`, `circular_reasoning`, `redundant_points`, `stuck_topic`)
- `min_repetitions` (query, optional): Minimum repetition count (≥2)
- `page` (query, optional, default=1): Page number
- `page_size` (query, optional, default=50): Items per page (max 100)

**Response:** `LoopListResponse`

```json
{
  "conversation_id": "debate_v2_123456",
  "loops": [
    {
      "id": "loop_xyz789",
      "conversation_id": "debate_v2_123456",
      "loop_type": "repetitive_argument",
      "start_round": 2,
      "end_round": 4,
      "repetition_count": 3,
      "participants_involved": ["Agent 1", "Agent 2"],
      "pattern_summary": "Both agents repeatedly stating the same arguments without new evidence",
      "detected_at": "2024-12-04T12:30:45.123456"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

**Curl Examples:**
```bash
# Get all loops
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/loops" \
  -H "accept: application/json"

# Filter by type and minimum repetitions
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/loops?loop_type=repetitive_argument&min_repetitions=3" \
  -H "accept: application/json"
```

**Status Codes:**
- `200 OK` - Successfully retrieved loops
- `404 Not Found` - Conversation not found
- `500 Internal Server Error` - Server error

---

### 5. Get Health Score History

**Endpoint:** `GET /api/v1/quality/conversations/{conversation_id}/health-history`

**Description:** Retrieve historical health score data for trend analysis and visualization.

**Parameters:**
- `conversation_id` (path, required): Debate/conversation identifier
- `limit` (query, optional, default=100): Maximum data points to return (max 1000)

**Response:**

```json
{
  "conversation_id": "debate_v2_123456",
  "data_points": [],
  "total_count": 0
}
```

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/health-history?limit=200" \
  -H "accept: application/json"
```

**Status Codes:**
- `200 OK` - Successfully retrieved health history
- `404 Not Found` - Conversation not found
- `500 Internal Server Error` - Server error

---

## SSE Quality Events (Phase 3 Integration)

Quality monitoring integrates with the existing debate SSE stream at:
`GET /api/v1/debates/v2/{debate_id}/next-turn`

### New Event Types

**1. contradiction_detected**
```json
{
  "event_type": "contradiction_detected",
  "conversation_id": "debate_v2_123456",
  "round_number": 3,
  "data": {
    "message": "Contradiction detected in Agent 1's statements",
    "contradiction": {
      "id": "contradiction_abc123",
      "severity": "high",
      "statement_1": "AI should be open source",
      "statement_2": "AI needs proprietary controls"
    }
  },
  "timestamp": "2024-12-04T12:30:45.123456"
}
```

**2. loop_detected**
```json
{
  "event_type": "loop_detected",
  "conversation_id": "debate_v2_123456",
  "round_number": 4,
  "data": {
    "message": "Conversational loop detected",
    "loop": {
      "id": "loop_xyz789",
      "loop_type": "repetitive_argument",
      "repetition_count": 3
    }
  },
  "timestamp": "2024-12-04T12:30:45.123456"
}
```

**3. health_score_update**
```json
{
  "event_type": "health_score_update",
  "conversation_id": "debate_v2_123456",
  "round_number": 2,
  "data": {
    "message": "Health score updated",
    "quality_metrics": {
      "overall_score": 78.5,
      "score_breakdown": {
        "coherence": 85.0,
        "diversity": 72.0,
        "engagement": 90.0,
        "evidence_quality": 65.0,
        "progression": 80.0
      }
    }
  },
  "timestamp": "2024-12-04T12:30:45.123456"
}
```

**4. citation_missing**
```json
{
  "event_type": "citation_missing",
  "conversation_id": "debate_v2_123456",
  "round_number": 2,
  "data": {
    "message": "Factual claim detected without citation",
    "details": {
      "participant": "Agent 1",
      "claim": "Studies show that...",
      "suggestion": "Please provide a source for this claim"
    }
  },
  "timestamp": "2024-12-04T12:30:45.123456"
}
```

**5. quality_alert**
```json
{
  "event_type": "quality_alert",
  "conversation_id": "debate_v2_123456",
  "round_number": 3,
  "data": {
    "message": "Overall quality declining",
    "details": {
      "alert_type": "health_score_drop",
      "previous_score": 85.0,
      "current_score": 65.0,
      "recommendation": "Consider introducing new perspectives or evidence"
    }
  },
  "timestamp": "2024-12-04T12:30:45.123456"
}
```

---

## Integration Example

### Client-Side SSE Listener

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/debates/v2/debate_v2_123456/next-turn'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Handle debate events
  if (data.event_type === 'chunk') {
    appendToTranscript(data.data.text);
  }

  // Handle quality events
  if (data.event_type === 'contradiction_detected') {
    showContradictionAlert(data.data.contradiction);
    updateHealthScore(data.data);
  }

  if (data.event_type === 'loop_detected') {
    showLoopWarning(data.data.loop);
  }

  if (data.event_type === 'health_score_update') {
    updateHealthDashboard(data.data.quality_metrics);
  }

  if (data.event_type === 'citation_missing') {
    highlightClaimWithoutCitation(data.data.details);
  }
};
```

---

## Implementation Status

### ✅ Completed
- Pydantic schemas for all quality models (`quality_schemas.py`)
- FastAPI route definitions (`quality.py`)
- SSE event type definitions
- Integration points in debate_v2 routes
- API documentation with curl examples

### 🚧 Pending (Phase 3 Service Implementation)
- Contradiction detection service (semantic similarity + LLM analysis)
- Loop detection service (pattern matching + embedding comparison)
- Health scoring service (multi-factor quality metrics)
- Citation tracking service (claim detection + source verification)
- Database schema for quality data storage
- Integration with existing debate service

---

## Testing Endpoints

Once the backend server is running:

```bash
# Test server health
curl http://localhost:8000/health

# Create a debate
curl -X POST "http://localhost:8000/api/v1/debates/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Should AI be open source?",
    "participants": [
      {"name": "Agent 1", "model": "gpt-4o"},
      {"name": "Agent 2", "model": "claude-3-5-sonnet-20241022"}
    ],
    "max_rounds": 3
  }'

# Get quality metrics (will return mock data until services implemented)
curl http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/quality

# List contradictions
curl http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/contradictions

# List loops
curl http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/loops
```

---

## OpenAPI Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

All quality endpoints will be grouped under the **"Quality Monitoring"** tag.

---

**Document Version:** 1.0
**Last Updated:** December 4, 2024
**Author:** Backend Development Team
