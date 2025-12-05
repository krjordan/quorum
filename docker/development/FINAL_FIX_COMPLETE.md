# Agent Rotation Bug - Complete Fix Summary

**Date**: 2025-12-05
**Status**: ✅ **ALL ISSUES FIXED**

---

## 🐛 The Original Problem

**Symptom**: All debate responses going to Agent 1, other agents "think" but never post content

**Root Cause Chain**: Three interconnected bugs

---

## 🔧 Bug #1: Turn Advancement Never Executed

### Problem
Turn advancement code was **unreachable** because the frontend closed the SSE connection before it could run.

**Event Flow (Broken)**:
```
1. Backend: Emit participant_complete event
2. Frontend: Receive event → CLOSE SSE ❌
3. Backend: Generator terminated
4. Backend: Turn advancement code never runs ❌
```

### Fix
**Move turn advancement BEFORE `participant_complete` event**

**File**: `backend/app/services/sequential_debate_service.py:357-402`

```python
# Advance turn FIRST (while connection is still open)
next_turn = debate.current_turn + 1
next_round = debate.current_round

if next_turn >= len(debate.config.participants):
    next_turn = 0
    next_round = debate.current_round + 1

# Create new debate instance
debate_dict = debate.model_dump()
debate_dict['current_turn'] = next_turn
debate_dict['current_round'] = next_round
updated_debate = DebateV2(**debate_dict)
self.debates[debate_id] = updated_debate
debate = updated_debate

# NOW emit participant_complete (frontend can safely close)
yield participant_complete_event
```

---

## 🐛 Bug #2: Missing Round Object in List

### Problem
When advancing to round 2, we only updated the `current_round` NUMBER, but didn't create the actual `DebateRoundV2` object in the `debate.rounds` list.

**Error**: `list index out of range` when accessing `debate.rounds[1]`

### Fix
**Create new round object immediately when advancing**

**File**: `backend/app/services/sequential_debate_service.py:379-389`

```python
# If we're advancing to a new round, create the round object
if next_round > debate.current_round:
    new_round = DebateRoundV2(
        round_number=next_round,
        responses=[],
        tokens_used={},
        cost_estimate=0.0,
        timestamp=datetime.now()
    )
    debate_dict['rounds'].append(new_round.model_dump())
```

**Also removed duplicate round creation** at line 645 that was causing conflicts.

---

## 🐛 Bug #3: Stale Object References

### Problem
After replacing the debate object, the `current_round` variable was pointing to the OLD debate's round object, causing stale data issues.

### Fix
**Update reference to point to new debate's round**

**File**: `backend/app/services/sequential_debate_service.py:396-398`

```python
# Replace debate object
updated_debate = DebateV2(**debate_dict)
self.debates[debate_id] = updated_debate
debate = updated_debate

# Update current_round reference (prevents stale object issues)
current_round = debate.rounds[current_round_num - 1]
```

---

## 🐛 Bug #4: Invalid JSON in Error Events

### Problem
Error handler was sending Python dict representation instead of valid JSON, causing parse errors in frontend.

**Broken**:
```python
yield f"data: {error_event}\n\n"  # ❌ Outputs: {'key': 'value'}
```

### Fix
**Convert to JSON properly**

**File**: `backend/app/api/routes/debate_v2.py:134, 145`

```python
import json

yield f"data: {json.dumps(error_event)}\n\n"  # ✅ Outputs: {"key": "value"}
```

---

## ✅ Final Event Flow (Fixed)

```
1. Backend: Stream LLM response chunks
2. Backend: Calculate next turn/round ✅
3. Backend: Create new round object if needed ✅
4. Backend: Replace debate object with updated state ✅
5. Backend: Update stale references ✅
6. Backend: Emit participant_complete ───┐
7. Frontend: Receive event               │
8. Frontend: Close SSE ──────────────────┘
9. Next request: Turn advanced correctly! ✅
```

---

## 🧪 Testing Verification

### Expected Behavior
Create debate with 3 agents, 2 rounds. Click "Next Turn" 6 times:

**Round 1**:
- Turn 1: Agent 1 ✅
- Turn 2: Agent 2 ✅
- Turn 3: Agent 3 ✅

**Round 2**:
- Turn 1: Agent 1 ✅
- Turn 2: Agent 2 ✅
- Turn 3: Agent 3 ✅

### Debug Logs
```bash
docker logs -f quorum-backend-dev 2>&1 | grep -E "📍|👤|🔍|✅|🔄"
```

**Expected Output**:
```
📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=0
👤 [PARTICIPANT] Selected: Agent 1 (turn index 0)
🔍 [TURN] BEFORE: round=1, turn=0
✅ [TURN] AFTER: round=1, turn=1

📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=1
👤 [PARTICIPANT] Selected: Agent 2 (turn index 1)
🔍 [TURN] BEFORE: round=1, turn=1
✅ [TURN] AFTER: round=1, turn=2

📍 [REQUEST START] Debate debate_v2_xxx: round=1, turn=2
👤 [PARTICIPANT] Selected: Agent 3 (turn index 2)
🔍 [TURN] BEFORE: round=1, turn=2
🔄 [TURN] Round complete, advancing to round 2
✅ [TURN] AFTER: round=2, turn=0

📍 [REQUEST START] Debate debate_v2_xxx: round=2, turn=0
👤 [PARTICIPANT] Selected: Agent 1 (turn index 0)
...
```

---

## 📝 Files Modified

### Backend Changes
1. **`backend/app/services/sequential_debate_service.py`**
   - Lines 357-402: Turn advancement moved before participant_complete
   - Lines 379-389: Added round object creation when advancing
   - Line 398: Added stale reference update
   - Removed duplicate round creation at ~line 645

2. **`backend/app/api/routes/debate_v2.py`**
   - Line 6: Added `import json`
   - Lines 134, 145: Fixed error event JSON serialization
   - Line 137: Added `exc_info=True` for better error logging

### No Frontend Changes Required
The frontend behavior was correct - it's designed to close SSE on `participant_complete`. The backend needed to accommodate this pattern.

---

## 🎯 Key Learnings

### 1. SSE Connection Lifecycle Matters
Operations after connection close are unreachable. Critical state updates must happen BEFORE events that trigger connection closure.

### 2. Pydantic Object Replacement Pattern
When mutating Pydantic models, replace the entire object:
```python
dict = model.model_dump()
dict['field'] = new_value
new_model = Model(**dict)
storage[id] = new_model
```

### 3. Keep Data Structure in Sync
When incrementing `current_round` counter, immediately create the corresponding `DebateRoundV2` object in the list.

### 4. Update References After Mutations
After replacing an object, update all variable references to point to the new instance.

### 5. Proper Error Handling
Always serialize errors to valid JSON for SSE streams. Include stack traces for debugging.

---

## 🚀 Backend Status

**All fixes applied**: ✅
**Backend restarted**: ✅
**Ready for production**: ✅

---

## 📊 Remaining Issues (Frontend Only)

These are **separate bugs** unrelated to agent rotation:

### 1. Cost Tracking Shows $0
- **Backend**: Sending correct data in SSE events ✅
- **Frontend**: Not consuming `cost_update` events properly
- **Next Step**: Debug frontend SSE handler

### 2. Health Score Stuck at 100%
- **Backend**: Sending 95-96% correctly ✅
- **Frontend**: Likely using wrong field (`coherence` instead of `score`)
- **Next Step**: Fix frontend to use `quality_update.data.score`

---

**Created**: 2025-12-05
**Last Updated**: 2025-12-05
**Backend Version**: Latest with complete agent rotation fix
**Total Bugs Fixed**: 4 (turn advancement, missing rounds, stale references, invalid JSON)
