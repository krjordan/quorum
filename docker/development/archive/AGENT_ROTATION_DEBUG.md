# Agent Rotation Bug - Debug Plan

## Problem
All 9 responses went to Bob instead of rotating Bob → Mary → Agent Smith.

## Debug Logging Added

Added logging in `sequential_debate_service.py`:

### Before getting participant (line 237-239):
```python
logger.info(f"[TURN DEBUG] Debate {debate_id}: current_round={debate.current_round}, current_turn={debate.current_turn}, participants={len(debate.config.participants)}")
participant = debate.get_current_participant()
logger.info(f"[TURN DEBUG] Selected participant: {participant.name} (index {debate.current_turn})")
```

### After advancing turn (line 581-583):
```python
logger.info(f"[TURN DEBUG] Before advance_turn: current_round={debate.current_round}, current_turn={debate.current_turn}")
debate.advance_turn()
logger.info(f"[TURN DEBUG] After advance_turn: current_round={debate.current_round}, current_turn={debate.current_turn}")
```

## Expected Output

For a debate with 3 participants (Bob, Mary, Agent Smith):

### Turn 1 (Bob):
```
[TURN DEBUG] Debate debate_v2_xxx: current_round=1, current_turn=0, participants=3
[TURN DEBUG] Selected participant: Bob (index 0)
[TURN DEBUG] Before advance_turn: current_round=1, current_turn=0
[TURN DEBUG] After advance_turn: current_round=1, current_turn=1
```

### Turn 2 (Mary):
```
[TURN DEBUG] Debate debate_v2_xxx: current_round=1, current_turn=1, participants=3
[TURN DEBUG] Selected participant: Mary (index 1)
[TURN DEBUG] Before advance_turn: current_round=1, current_turn=1
[TURN DEBUG] After advance_turn: current_round=1, current_turn=2
```

### Turn 3 (Agent Smith):
```
[TURN DEBUG] Debate debate_v2_xxx: current_round=1, current_turn=2, participants=3
[TURN DEBUG] Selected participant: Agent Smith (index 2)
[TURN DEBUG] Before advance_turn: current_round=1, current_turn=2
[TURN DEBUG] After advance_turn: current_round=2, current_turn=0
```

## Testing Steps

1. Start a new debate with 3 agents, 3 rounds
2. Click "Next Turn" 3 times
3. Check backend logs:
   ```bash
   docker logs quorum-backend-dev 2>&1 | grep "\[TURN DEBUG\]"
   ```

## Hypotheses

### Hypothesis 1: advance_turn() not being called
- Debug logs would show: "Before advance_turn" but no "After advance_turn"
- Fix: Ensure no exceptions are preventing advance_turn from executing

### Hypothesis 2: advance_turn() called but currentturn not incrementing
- Debug logs would show: current_turn=0 before AND after advance_turn
- Fix: Check if debate object is being cloned/copied somewhere

### Hypothesis 3: State reset between requests
- Debug logs would show: Turn 1 advances to turn=1, but Turn 2 starts at turn=0
- Fix: Debate state not persisting in singleton service
- Possible cause: Multiple service instances or debate dict not working

### Hypothesis 4: Frontend requesting wrong debate
- Debug logs would show: Different debate_id for each request
- Fix: Frontend debateIdRef not persisting correctly

## What to Look For

Compare the `current_turn` value:
- **At start of request**: Should be previous turn + 1
- **After advance_turn**: Should be current + 1

If turn always starts at 0, the state is being reset between requests.
If turn increments but then next request still uses 0, there's a state persistence issue.

---

## Fix Applied

**Root Cause**: Pydantic BaseModel field mutations were not persisting correctly. The `debate.advance_turn()` method was modifying fields, but Pydantic's validation/descriptor system may have been preventing proper state updates.

**Solution Applied** (2025-12-05):
1. Replaced `debate.advance_turn()` with direct state calculation
2. Used `object.__setattr__()` to bypass Pydantic descriptors and ensure field mutations
3. Added explicit persistence: `self.debates[debate_id] = debate`
4. Added comprehensive debug logging to track state changes

**Code Changes** (`sequential_debate_service.py:580-600`):
```python
# Calculate next state
next_turn = debate.current_turn + 1
next_round = debate.current_round

if next_turn >= len(debate.config.participants):
    next_turn = 0
    next_round = debate.current_round + 1

# Update using Pydantic-safe attribute assignment
object.__setattr__(debate, 'current_turn', next_turn)
object.__setattr__(debate, 'current_round', next_round)

# Explicitly persist to dictionary
self.debates[debate_id] = debate
```

**Backend Restarted**: 2025-12-05
**Status**: Ready for testing

---

**Created**: 2025-12-05
**Updated**: 2025-12-05 (Fix applied)
