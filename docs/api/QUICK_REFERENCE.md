# Quality Monitoring API - Quick Reference

## Base URL
```
http://localhost:8000/api/v1/quality
```

## Endpoints

### 1. Get Quality Metrics
```bash
GET /conversations/{conversation_id}/quality

curl http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/quality
```

**Response:** Overall score (0-100), breakdown, contradiction count, loop count, citations

---

### 2. List Contradictions
```bash
GET /conversations/{conversation_id}/contradictions

# Basic
curl http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/contradictions

# With filters
curl "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/contradictions?status=detected&severity=high&page=1&page_size=50"
```

**Query Params:**
- `status`: detected | acknowledged | resolved | dismissed
- `severity`: low | medium | high | critical
- `page`: number (default: 1)
- `page_size`: number (default: 50, max: 100)

---

### 3. Resolve Contradiction
```bash
POST /contradictions/{contradiction_id}/resolve

curl -X POST http://localhost:8000/api/v1/quality/contradictions/contradiction_abc123/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "resolution_note": "Participant clarified position",
    "new_status": "resolved"
  }'
```

**Body:**
```json
{
  "resolution_note": "string",
  "new_status": "acknowledged" | "resolved" | "dismissed"
}
```

---

### 4. List Loops
```bash
GET /conversations/{conversation_id}/loops

# Basic
curl http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/loops

# With filters
curl "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/loops?loop_type=repetitive_argument&min_repetitions=3"
```

**Query Params:**
- `loop_type`: repetitive_argument | circular_reasoning | redundant_points | stuck_topic
- `min_repetitions`: number (min: 2)
- `page`: number (default: 1)
- `page_size`: number (default: 50, max: 100)

---

### 5. Get Health History
```bash
GET /conversations/{conversation_id}/health-history

curl "http://localhost:8000/api/v1/quality/conversations/debate_v2_123456/health-history?limit=200"
```

**Query Params:**
- `limit`: number (default: 100, max: 1000)

---

## SSE Quality Events

Subscribe to debate stream for real-time quality events:
```bash
curl -N http://localhost:8000/api/v1/debates/v2/{debate_id}/next-turn
```

**Quality Event Types:**
- `contradiction_detected` - Contradiction found
- `loop_detected` - Loop identified
- `health_score_update` - Score updated
- `citation_missing` - Missing citation
- `quality_alert` - General warning

---

## Full Documentation
- **API Docs:** http://localhost:8000/docs
- **Detailed Guide:** `/docs/api/quality-endpoints.md`
- **Implementation:** `/docs/implementation-summary-quality-endpoints.md`
