# Agent Rotation Debug - Second Attempt

**Date**: 2025-12-05
**Issue**: All responses going to Agent 1, other agents "think" but never post content

---

## Investigation Results

### Confirmed Problem
Looking at backend logs, the system prompt **ALWAYS** says:
```
"You are Agent 1. Provide your next debate response."
```

And the transcript shows:
```
Agent 1: [first response]
Agent 1: [second response]
Agent 1: [third response]
```

This proves the backend is NOT advancing `current_turn` - it's stuck at 0.

### Why First Fix Failed

**First approach** (lines 580-600):
- Used `object.__setattr__(debate, 'current_turn', next_turn)`
- Tried to modify Pydantic BaseModel fields directly
- State changes didn't persist between requests

**Root Cause**: Pydantic BaseModel may be creating defensive copies or the singleton service's dictionary isn't properly storing the modified state.

---

## Second Fix Applied

### New Strategy: Replace Entire Object

Instead of modifying the debate object in place, we now:
1. **Extract** the debate as a dictionary using `model_dump()`
2. **Update** the state fields in the dictionary
3. **Create** a completely NEW `DebateV2` instance
4. **Replace** the old object in `self.debates` dictionary

**Code** (`sequential_debate_service.py:580-605`):
```python
# Create new debate instance with updated state (Pydantic-safe)
debate_dict = debate.model_dump()
debate_dict['current_turn'] = next_turn
debate_dict['current_round'] = next_round
debate_dict['updated_at'] = datetime.now()

# Replace the entire debate object
updated_debate = DebateV2(**debate_dict)
self.debates[debate_id] = updated_debate
debate = updated_debate  # Update local reference
```

### Debug Statements Added

Using `print()` instead of `logger.info()` to ensure output appears in Docker logs:

```python
📍 [REQUEST START] - State at beginning of request
👤 [PARTICIPANT] - Selected participant name
🔍 [TURN] BEFORE - State before advancement
🔄 [TURN] Round complete - When round advances
✅ [TURN] AFTER - State after advancement
✅ [TURN] PERSISTED - State in dictionary
```

---

## Testing Instructions

### 1. Start a New Debate
Create a debate with 3 agents, 2 rounds. Click "Next Turn" 3 times.

### 2. Monitor Docker Logs in Real-Time
```bash
docker logs -f quorum-backend-dev 2>&1 | grep -E "📍|👤|🔍|✅|🔄"
```

### 3. Expected Output

**Turn 1** (Agent 1):
```
📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=0
👤 [PARTICIPANT] Selected: Agent 1 (turn index 0)
🔍 [TURN] BEFORE: round=1, turn=0
✅ [TURN] AFTER: round=1, turn=1
✅ [TURN] PERSISTED: round=1, turn=1
```

**Turn 2** (Agent 2):
```
📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=1
👤 [PARTICIPANT] Selected: Agent 2 (turn index 1)
🔍 [TURN] BEFORE: round=1, turn=1
✅ [TURN] AFTER: round=1, turn=2
✅ [TURN] PERSISTED: round=1, turn=2
```

**Turn 3** (Agent 3):
```
📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=2
👤 [PARTICIPANT] Selected: Agent 3 (turn index 2)
🔍 [TURN] BEFORE: round=1, turn=2
🔄 [TURN] Round complete, advancing to round 2
✅ [TURN] AFTER: round=2, turn=0
✅ [TURN] PERSISTED: round=2, turn=0
```

### 4. What To Look For

**If the fix works**:
- REQUEST START shows incrementing `turn` values: 0 → 1 → 2
- PARTICIPANT shows different agent names: Agent 1 → Agent 2 → Agent 3
- Frontend displays all three agents speaking in order

**If it still fails**:
- REQUEST START always shows `turn=0`
- PARTICIPANT always shows Agent 1
- This indicates a deeper issue with the singleton service pattern

---

## Diagnostic Questions

If this fix STILL doesn't work, we need to investigate:

1. **Are multiple service instances being created?**
   - Check if `__init__` is called multiple times
   - Verify singleton pattern is working

2. **Is the debate_id changing between requests?**
   - Frontend should send same `debate_id` for all turns
   - Check browser network tab

3. **Is FastAPI creating new service instances per request?**
   - Dependency injection might be creating new instances
   - Need to verify module-level singleton

---

## Backend Restarted

✅ Backend restarted with new fix: `docker compose restart backend`

**Status**: Ready for testing

---

**Created**: 2025-12-05
**Version**: 2nd attempt - Object replacement strategy
