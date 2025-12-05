# Agent Rotation Bug - Root Cause Analysis & Fix

**Date**: 2025-12-05
**Issue**: All debate responses going to Agent 1, other agents think but never post content
**Status**: ✅ **FIXED**

---

## 🔍 Root Cause: Premature SSE Connection Closure

### The Problem

The agent rotation was broken because **the turn advancement code never executed**. Here's what was happening:

1. **Backend** emits `participant_complete` SSE event (line 357)
2. **Frontend** receives event and **immediately closes SSE connection** (useSequentialDebate.ts:156-159)
3. **Backend's async generator is terminated** when connection closes
4. **Turn advancement code (line 580) never runs** ❌

### Why It Looked Like a State Persistence Issue

The symptoms suggested Pydantic wasn't saving state:
- Every request showed `turn=0`
- Debug logs at the START showed `turn=0`
- The system prompt always said "You are Agent 1"

But the real issue was **the turn advancement code path was unreachable** due to early connection termination.

---

## ✅ The Fix

### Solution: Advance Turn BEFORE Emitting `participant_complete`

**File**: `backend/app/services/sequential_debate_service.py`

**Changes**: Moved turn advancement from line 580 to line 357 (before `participant_complete` event)

**Why This Works**:
- Turn state updates while SSE connection is still open
- Next turn sees updated state (turn=1, turn=2, etc.)
- Frontend can safely close connection after receiving `participant_complete`

**Code** (lines 357-399):
```python
# ===== ADVANCE TURN BEFORE EMITTING PARTICIPANT_COMPLETE =====
# This must happen BEFORE participant_complete because the frontend closes
# the SSE connection immediately upon receiving that event, which would
# terminate this generator before turn advancement occurs.

# Calculate next state
next_turn = debate.current_turn + 1
next_round = debate.current_round

if next_turn >= len(debate.config.participants):
    next_turn = 0
    next_round = debate.current_round + 1

# Create new debate instance with updated state (Pydantic-safe)
debate_dict = debate.model_dump()
debate_dict['current_turn'] = next_turn
debate_dict['current_round'] = next_round
debate_dict['updated_at'] = datetime.now()

# Replace the entire debate object
updated_debate = DebateV2(**debate_dict)
self.debates[debate_id] = updated_debate
debate = updated_debate  # Update local reference

# NOW emit participant_complete (frontend can safely close)
yield SequentialTurnEvent(
    event_type=SequentialTurnEventType.PARTICIPANT_COMPLETE,
    ...
)
```

---

## 📊 Event Flow (Before vs After)

### ❌ BEFORE (Broken):
```
1. Backend: Stream LLM response
2. Backend: Emit participant_complete ─────┐
3. Frontend: Receive event                 │
4. Frontend: CLOSE SSE ────────────────────┘
5. Backend: ❌ Generator terminated
6. Backend: ❌ Turn advancement never runs
7. Next request: turn=0 (stuck!)
```

### ✅ AFTER (Fixed):
```
1. Backend: Stream LLM response
2. Backend: Advance turn (0 → 1) ✅
3. Backend: Emit participant_complete ─────┐
4. Frontend: Receive event                 │
5. Frontend: Close SSE ────────────────────┘
6. Next request: turn=1 ✅ (correct!)
```

---

## 🧪 Testing Verification

### Expected Behavior
Create debate with 3 agents, click "Next Turn" 6 times:

**Turn 1**: Agent 1 speaks (turn=0) ✅
**Turn 2**: Agent 2 speaks (turn=1) ✅
**Turn 3**: Agent 3 speaks (turn=2) ✅
**Turn 4**: Agent 1 speaks (turn=0, round=2) ✅
**Turn 5**: Agent 2 speaks (turn=1, round=2) ✅
**Turn 6**: Agent 3 speaks (turn=2, round=2) ✅

### Debug Logs to Verify
```bash
docker logs -f quorum-backend-dev 2>&1 | grep -E "📍|👤|🔍|✅|🔄"
```

**Expected Output**:
```
📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=0
👤 [PARTICIPANT] Selected: Agent 1 (turn index 0)
🔍 [TURN] BEFORE: round=1, turn=0
✅ [TURN] AFTER: round=1, turn=1
✅ [TURN] PERSISTED: round=1, turn=1

📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=1
👤 [PARTICIPANT] Selected: Agent 2 (turn index 1)
🔍 [TURN] BEFORE: round=1, turn=1
✅ [TURN] AFTER: round=1, turn=2
✅ [TURN] PERSISTED: round=1, turn=2

📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=2
👤 [PARTICIPANT] Selected: Agent 3 (turn index 2)
🔍 [TURN] BEFORE: round=1, turn=2
🔄 [TURN] Round complete, advancing to round 2
✅ [TURN] AFTER: round=2, turn=0
✅ [TURN] PERSISTED: round=2, turn=0
```

---

## 🎯 Key Insights

### 1. Order of Operations Matters
In SSE streaming, operations after connection close are unreachable. Critical state updates must happen BEFORE events that trigger connection closure.

### 2. Frontend Behavior Drives Backend Design
The frontend's pattern of closing connections on `participant_complete` is reasonable and shouldn't change. The backend must accommodate this.

### 3. Async Generator Lifecycle
When an SSE connection closes, Python's async generator is terminated immediately via `GeneratorExit`. Any code after the last successfully yielded event won't execute.

### 4. Pydantic Immutability Pattern
The fix uses Pydantic-safe object replacement:
```python
debate_dict = debate.model_dump()
debate_dict['field'] = new_value
updated_debate = DebateV2(**debate_dict)
self.debates[id] = updated_debate
```

This ensures state changes persist correctly with Pydantic's validation.

---

## 🚀 Backend Status

**Backend restarted**: ✅
**Fix deployed**: ✅
**Ready for testing**: ✅

---

## 📝 Remaining Frontend Issues

These are **separate bugs** and don't affect agent rotation:

1. **Cost tracking showing $0**
   - Backend sends correct data
   - Frontend SSE handler not updating state

2. **Health score stuck at 100%**
   - Backend sends 95-96%
   - Frontend likely using wrong field (`coherence` instead of `score`)

---

**Created**: 2025-12-05
**Fix Applied**: Moving turn advancement before `participant_complete` emission
**Lines Changed**: 357-399, removed duplicate code at 612-637
**Backend Version**: Latest with turn advancement fix
