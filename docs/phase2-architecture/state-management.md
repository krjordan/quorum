# Phase 2: State Management Architecture

## Overview

Hybrid state management approach combining **XState** for deterministic debate flow logic and **Zustand** for performant UI state management. This separation ensures clean architecture and optimal performance.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    APPLICATION STATE LAYER                           │
│                                                                       │
│  ┌─────────────────────────────┐  ┌───────────────────────────┐   │
│  │      XState Machine         │  │    Zustand Store          │   │
│  │  (Debate Flow Logic)        │  │    (UI State)             │   │
│  │                             │  │                           │   │
│  │ - State machine states      │  │ - Stream buffers          │   │
│  │ - Event handling            │  │ - UI toggles              │   │
│  │ - Guard conditions          │  │ - Optimistic updates      │   │
│  │ - Context management        │  │ - Cached data             │   │
│  │ - Persistence logic         │  │ - View preferences        │   │
│  └──────────┬──────────────────┘  └──────────┬────────────────┘   │
│             │                                  │                     │
│             │ Coordinates                      │ Fast updates       │
│             │                                  │                     │
└─────────────┼──────────────────────────────────┼─────────────────────┘
              │                                  │
              ▼                                  ▼
    ┌─────────────────┐                ┌─────────────────┐
    │ React Components│◀───────────────│ React Components│
    │ (Container)     │                │ (UI Components) │
    └─────────────────┘                └─────────────────┘
```

---

## Separation of Concerns

### XState Responsibilities (Business Logic)

**What it manages:**
- ✅ Debate lifecycle states (idle, initializing, debating, completed, etc.)
- ✅ State transitions based on events
- ✅ Business rules and guard conditions
- ✅ Debate context (participants, rounds, costs, verdict)
- ✅ SSE event routing to appropriate handlers
- ✅ Error states and recovery logic
- ✅ State persistence (snapshots)

**What it doesn't manage:**
- ❌ UI visibility toggles
- ❌ Streaming text buffers (high-frequency updates)
- ❌ Component-level state (modals, dropdowns)
- ❌ View preferences (expanded/collapsed panels)

### Zustand Responsibilities (UI State)

**What it manages:**
- ✅ Stream text buffers (for batching SSE chunks)
- ✅ UI component visibility (modals, tooltips, panels)
- ✅ Optimistic UI updates (before server confirms)
- ✅ View preferences (collapsed/expanded, themes)
- ✅ Temporary UI state (hover states, selections)
- ✅ Client-side caching (for performance)

**What it doesn't manage:**
- ❌ Debate flow states
- ❌ Business logic or rules
- ❌ Server-side state of truth
- ❌ State machine transitions

---

## XState Machine Implementation

### Machine Definition

```typescript
// frontend/src/machines/debate-machine.ts

import { createMachine, assign } from 'xstate';

export const debateMachine = createMachine({
  id: 'debate',
  initial: 'idle',
  types: {} as {
    context: DebateContext;
    events: DebateEvent;
  },
  context: {
    config: null,
    debateId: null,
    participants: [],
    judge: null,
    currentRound: 0,
    maxRounds: 5,
    rounds: [],
    activeStreams: new Map(),
    costTracker: {
      totalCost: 0,
      costByModel: new Map(),
      warnings: [],
    },
    tokenUsage: new Map(),
    verdict: null,
    lastError: null,
    retryCount: 0,
  },
  states: {
    idle: {
      on: {
        START_DEBATE: {
          target: 'initializing',
          actions: assign({
            config: ({ event }) => event.config,
            retryCount: 0,
          }),
        },
      },
    },
    initializing: {
      entry: ['persistState', 'initializeDebate'],
      invoke: {
        id: 'createDebate',
        src: 'createDebateAPI',
        input: ({ context }) => ({ config: context.config }),
        onDone: {
          target: 'awaitingArguments',
          actions: assign({
            debateId: ({ event }) => event.output.id,
            participants: ({ event }) => event.output.participants,
            judge: ({ event }) => event.output.judge,
          }),
        },
        onError: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => ({
              type: 'network',
              message: event.error.message,
              retryable: true,
              timestamp: new Date(),
            }),
          }),
        },
      },
    },
    awaitingArguments: {
      entry: ['persistState', 'connectSSE'],
      on: {
        STREAM_CHUNK: {
          actions: 'handleStreamChunk',
        },
        ARGUMENTS_READY: {
          target: 'debating',
          actions: assign({
            rounds: ({ event }) => [event.round],
            currentRound: 1,
          }),
        },
        ERROR: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => event.error,
          }),
        },
        PAUSE: 'paused',
      },
    },
    debating: {
      entry: ['persistState'],
      on: {
        STREAM_CHUNK: {
          actions: 'handleStreamChunk',
        },
        ROUND_COMPLETE: [
          {
            target: 'judgeEvaluating',
            guard: 'maxRoundsReached',
            actions: 'recordRound',
          },
          {
            actions: ['recordRound', 'incrementRound', 'persistState'],
          },
        ],
        COST_WARNING: {
          actions: 'addCostWarning',
        },
        PAUSE: 'paused',
        STOP: 'judgeEvaluating',
        ERROR: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => event.error,
          }),
        },
      },
      always: [
        {
          target: 'error',
          guard: 'costLimitExceeded',
        },
      ],
    },
    judgeEvaluating: {
      entry: ['persistState'],
      on: {
        STREAM_CHUNK: {
          actions: 'handleStreamChunk',
        },
        VERDICT_READY: {
          target: 'completed',
          actions: assign({
            verdict: ({ event }) => event.verdict,
          }),
        },
        ERROR: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => event.error,
          }),
        },
      },
    },
    completed: {
      type: 'final',
      entry: ['persistState', 'disconnectSSE', 'cleanupState'],
    },
    paused: {
      entry: ['persistState'],
      on: {
        RESUME: {
          target: '#debate.debating',
        },
        STOP: 'judgeEvaluating',
      },
    },
    error: {
      entry: ['persistState', 'logError'],
      on: {
        RETRY: {
          target: 'initializing',
          guard: 'canRetry',
          actions: assign({
            retryCount: ({ context }) => context.retryCount + 1,
          }),
        },
        RESET: 'idle',
      },
    },
  },
});
```

### Actions

```typescript
// frontend/src/machines/debate-actions.ts

export const debateActions = {
  // Persist state to localStorage
  persistState: assign(({ context }) => {
    const snapshot = {
      debateId: context.debateId,
      state: 'current', // Will be filled by XState
      context: {
        config: context.config,
        currentRound: context.currentRound,
        rounds: context.rounds,
        costTracker: context.costTracker,
        verdict: context.verdict,
      },
      timestamp: Date.now(),
    };
    localStorage.setItem('debate_state', JSON.stringify(snapshot));
    return context;
  }),

  // Handle streaming chunk
  handleStreamChunk: assign(({ context, event }) => {
    const { participantId, chunk } = event;

    // Store in Zustand instead of XState (high frequency)
    useDebateUIStore.getState().updateStreamBuffer(participantId, chunk);

    return context;
  }),

  // Record completed round
  recordRound: assign(({ context, event }) => {
    const updatedRounds = [...context.rounds, event.round];
    return {
      ...context,
      rounds: updatedRounds,
    };
  }),

  // Increment round counter
  incrementRound: assign(({ context }) => ({
    ...context,
    currentRound: context.currentRound + 1,
  })),

  // Add cost warning
  addCostWarning: assign(({ context, event }) => {
    const warnings = [...context.costTracker.warnings, event.warning];
    return {
      ...context,
      costTracker: {
        ...context.costTracker,
        warnings,
      },
    };
  }),

  // Log error
  logError: ({ context }) => {
    console.error('[Debate Machine] Error:', context.lastError);
    // Send to error tracking service (e.g., Sentry)
  },

  // Cleanup state
  cleanupState: () => {
    localStorage.removeItem('debate_state');
  },
};
```

### Guards

```typescript
// frontend/src/machines/debate-guards.ts

export const debateGuards = {
  maxRoundsReached: ({ context }) => {
    return context.currentRound >= context.maxRounds;
  },

  costLimitExceeded: ({ context }) => {
    const { costLimit } = context.config || {};
    if (!costLimit) return false;
    return context.costTracker.totalCost >= costLimit;
  },

  canRetry: ({ context }) => {
    return (
      context.lastError?.retryable === true &&
      context.retryCount < 3
    );
  },
};
```

### Services

```typescript
// frontend/src/machines/debate-services.ts

import { fromPromise } from 'xstate';
import { debateApi } from '@/lib/api/debate-api';

export const debateServices = {
  createDebateAPI: fromPromise(async ({ input }) => {
    const response = await debateApi.createDebate(input.config);
    return response.data;
  }),
};
```

---

## Zustand Store Implementation

### Store Definition

```typescript
// frontend/src/stores/debate-store.ts

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface DebateUIState {
  // Stream buffers (high-frequency updates)
  streamBuffers: Map<string, string>;
  updateStreamBuffer: (participantId: string, chunk: string) => void;
  flushStreamBuffer: (participantId: string) => string;
  clearStreamBuffers: () => void;

  // UI visibility toggles
  costTrackerExpanded: boolean;
  toggleCostTracker: () => void;

  showCostWarningModal: boolean;
  setShowCostWarningModal: (show: boolean) => void;

  roundTimelineExpanded: boolean;
  toggleRoundTimeline: () => void;

  // Optimistic updates
  optimisticState: string | null;
  setOptimisticState: (state: string | null) => void;

  // View preferences (persisted)
  preferences: {
    autoScrollEnabled: boolean;
    typewriterSpeed: number;
    costTrackerPosition: 'bottom-right' | 'bottom-left';
  };
  updatePreferences: (updates: Partial<typeof preferences>) => void;

  // Cached data
  cachedTranscript: string | null;
  setCachedTranscript: (transcript: string | null) => void;
}

export const useDebateUIStore = create<DebateUIState>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Stream buffers
        streamBuffers: new Map(),

        updateStreamBuffer: (participantId, chunk) =>
          set((state) => {
            const current = state.streamBuffers.get(participantId) || '';
            state.streamBuffers.set(participantId, current + chunk);
          }),

        flushStreamBuffer: (participantId) => {
          const buffer = get().streamBuffers.get(participantId) || '';
          set((state) => {
            state.streamBuffers.delete(participantId);
          });
          return buffer;
        },

        clearStreamBuffers: () =>
          set((state) => {
            state.streamBuffers.clear();
          }),

        // UI toggles
        costTrackerExpanded: false,
        toggleCostTracker: () =>
          set((state) => {
            state.costTrackerExpanded = !state.costTrackerExpanded;
          }),

        showCostWarningModal: false,
        setShowCostWarningModal: (show) =>
          set((state) => {
            state.showCostWarningModal = show;
          }),

        roundTimelineExpanded: true,
        toggleRoundTimeline: () =>
          set((state) => {
            state.roundTimelineExpanded = !state.roundTimelineExpanded;
          }),

        // Optimistic state
        optimisticState: null,
        setOptimisticState: (state) =>
          set({ optimisticState: state }),

        // Preferences (persisted)
        preferences: {
          autoScrollEnabled: true,
          typewriterSpeed: 5, // chars per frame
          costTrackerPosition: 'bottom-right',
        },
        updatePreferences: (updates) =>
          set((state) => {
            state.preferences = { ...state.preferences, ...updates };
          }),

        // Cached data
        cachedTranscript: null,
        setCachedTranscript: (transcript) =>
          set({ cachedTranscript: transcript }),
      })),
      {
        name: 'debate-ui-storage',
        // Only persist preferences, not transient state
        partialize: (state) => ({
          preferences: state.preferences,
        }),
      }
    ),
    { name: 'DebateUIStore' }
  )
);
```

---

## Integration Patterns

### Pattern 1: XState + Zustand in Components

```typescript
// frontend/src/components/debate/DebateContainer.tsx

import { useMachine } from '@xstate/react';
import { debateMachine } from '@/machines/debate-machine';
import { useDebateUIStore } from '@/stores/debate-store';

export function DebateContainer() {
  // XState for business logic
  const [state, send] = useMachine(debateMachine);

  // Zustand for UI state
  const {
    costTrackerExpanded,
    toggleCostTracker,
    streamBuffers,
  } = useDebateUIStore();

  const isDebating = state.matches('debating');
  const participants = state.context.participants;

  return (
    <div>
      {/* XState determines what to render */}
      {state.matches('idle') && (
        <DebateConfigPanel onStart={(config) => send({ type: 'START_DEBATE', config })} />
      )}

      {isDebating && (
        <DebateArena
          participants={participants}
          rounds={state.context.rounds}
          currentRound={state.context.currentRound}
          streamBuffers={streamBuffers} // From Zustand
          onPause={() => send({ type: 'PAUSE' })}
        />
      )}

      {/* Zustand controls UI visibility */}
      <CostTracker
        expanded={costTrackerExpanded}
        onToggle={toggleCostTracker}
        totalCost={state.context.costTracker.totalCost}
      />
    </div>
  );
}
```

### Pattern 2: Stream Buffering for Performance

```typescript
// frontend/src/hooks/useDebateSSE.ts

import { useEffect } from 'react';
import { useMachine } from '@xstate/react';
import { useDebateUIStore } from '@/stores/debate-store';

export function useDebateSSE(debateId: string, send: any) {
  const updateStreamBuffer = useDebateUIStore((state) => state.updateStreamBuffer);

  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/debates/${debateId}/stream`);

    // High-frequency event: Buffer in Zustand
    eventSource.addEventListener('participant', (e) => {
      const data = JSON.parse(e.data);
      updateStreamBuffer(data.participantId, data.chunk);

      // Only notify XState on completion
      if (data.done) {
        send({
          type: 'STREAM_COMPLETE',
          participantId: data.participantId,
        });
      }
    });

    // Low-frequency event: Send directly to XState
    eventSource.addEventListener('round_complete', (e) => {
      const data = JSON.parse(e.data);
      send({
        type: 'ROUND_COMPLETE',
        round: data,
      });
    });

    eventSource.addEventListener('verdict', (e) => {
      const data = JSON.parse(e.data);
      send({
        type: 'VERDICT_READY',
        verdict: data,
      });
    });

    return () => eventSource.close();
  }, [debateId, send, updateStreamBuffer]);
}
```

### Pattern 3: Optimistic Updates

```typescript
// frontend/src/components/debate/DebateControls.tsx

import { useDebateUIStore } from '@/stores/debate-store';

export function DebateControls({ onPause, onResume, isPaused }) {
  const { optimisticState, setOptimisticState } = useDebateUIStore();

  const handlePause = async () => {
    // Optimistic update
    setOptimisticState('paused');

    try {
      await debateApi.pauseDebate(debateId);
      // Success: XState will confirm
      onPause();
    } catch (error) {
      // Rollback optimistic update
      setOptimisticState(null);
      toast.error('Failed to pause debate');
    }
  };

  // Use optimistic state for UI
  const displayPaused = optimisticState === 'paused' || isPaused;

  return (
    <Button onClick={displayPaused ? onResume : handlePause}>
      {displayPaused ? 'Resume' : 'Pause'}
    </Button>
  );
}
```

---

## State Persistence Strategy

### XState Persistence (Business Logic)

```typescript
// Persist on every state transition
const persistedMachine = debateMachine.provide({
  actions: {
    persistState: assign(({ context }) => {
      const snapshot = {
        debateId: context.debateId,
        context: {
          config: context.config,
          currentRound: context.currentRound,
          rounds: context.rounds,
          costTracker: context.costTracker,
          verdict: context.verdict,
        },
        timestamp: Date.now(),
      };
      localStorage.setItem('debate_state', JSON.stringify(snapshot));
      return context;
    }),
  },
});
```

### Zustand Persistence (UI Preferences)

```typescript
// Only persist user preferences, not transient state
export const useDebateUIStore = create(
  persist(
    (set) => ({ /* ... */ }),
    {
      name: 'debate-ui-storage',
      partialize: (state) => ({
        preferences: state.preferences, // Only persist this
      }),
    }
  )
);
```

### State Restoration on Load

```typescript
// frontend/src/app/debate/page.tsx

export default function DebatePage() {
  const [initialState, setInitialState] = useState(null);

  useEffect(() => {
    // Try to restore from localStorage
    const saved = localStorage.getItem('debate_state');
    if (saved) {
      const snapshot = JSON.parse(saved);
      const age = Date.now() - snapshot.timestamp;

      // Only restore if < 1 hour old
      if (age < 3600000) {
        setInitialState(snapshot);
      } else {
        localStorage.removeItem('debate_state');
      }
    }
  }, []);

  return (
    <DebateContainer initialState={initialState} />
  );
}
```

---

## Performance Optimizations

### 1. Stream Batching

```typescript
// frontend/src/hooks/useBatchedStreamUpdates.ts

import { useEffect, useState } from 'react';
import { useDebateUIStore } from '@/stores/debate-store';

export function useBatchedStreamUpdates(participantId: string) {
  const [displayedContent, setDisplayedContent] = useState('');
  const streamBuffers = useDebateUIStore((state) => state.streamBuffers);

  useEffect(() => {
    // Batch updates every 100ms (instead of every chunk)
    const interval = setInterval(() => {
      const buffer = streamBuffers.get(participantId);
      if (buffer && buffer !== displayedContent) {
        setDisplayedContent(buffer);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [participantId, streamBuffers, displayedContent]);

  return displayedContent;
}
```

### 2. Selective Re-renders

```typescript
// Only subscribe to specific Zustand slices
const costTrackerExpanded = useDebateUIStore(
  (state) => state.costTrackerExpanded
);
// Component only re-renders when costTrackerExpanded changes

// vs. subscribing to entire store (bad)
const store = useDebateUIStore(); // Re-renders on ANY state change
```

### 3. Memoization

```typescript
// frontend/src/components/debate/ParticipantPanel.tsx

import { memo } from 'react';

export const ParticipantPanel = memo(({ participant, content }) => {
  return <div>{content}</div>;
}, (prev, next) => {
  // Only re-render if content actually changed
  return prev.content === next.content;
});
```

---

## Testing Strategy

### XState Machine Tests

```typescript
// frontend/src/machines/debate-machine.test.ts

import { createActor } from 'xstate';
import { debateMachine } from './debate-machine';

describe('Debate State Machine', () => {
  it('transitions from idle to initializing', () => {
    const actor = createActor(debateMachine);
    actor.start();

    expect(actor.getSnapshot().value).toBe('idle');

    actor.send({ type: 'START_DEBATE', config: mockConfig });

    expect(actor.getSnapshot().value).toBe('initializing');
  });

  it('handles cost limit exceeded', () => {
    const actor = createActor(
      debateMachine.provide({
        context: {
          ...debateMachine.context,
          config: { costLimit: 5.0 },
          costTracker: { totalCost: 5.5 },
        },
      })
    );
    actor.start();

    // Should auto-transition to error
    expect(actor.getSnapshot().value).toBe('error');
  });

  it('records round and increments counter', () => {
    const actor = createActor(debateMachine);
    actor.start();

    // Transition to debating state
    actor.send({ type: 'START_DEBATE', config: mockConfig });
    actor.send({ type: 'INIT_COMPLETE' });
    actor.send({ type: 'ARGUMENTS_READY', round: mockRound1 });

    expect(actor.getSnapshot().context.currentRound).toBe(1);

    actor.send({ type: 'ROUND_COMPLETE', round: mockRound2 });

    expect(actor.getSnapshot().context.currentRound).toBe(2);
    expect(actor.getSnapshot().context.rounds.length).toBe(2);
  });
});
```

### Zustand Store Tests

```typescript
// frontend/src/stores/debate-store.test.ts

import { renderHook, act } from '@testing-library/react';
import { useDebateUIStore } from './debate-store';

describe('Debate UI Store', () => {
  beforeEach(() => {
    useDebateUIStore.setState({
      streamBuffers: new Map(),
      costTrackerExpanded: false,
    });
  });

  it('buffers stream chunks', () => {
    const { result } = renderHook(() => useDebateUIStore());

    act(() => {
      result.current.updateStreamBuffer('part_1', 'Hello');
      result.current.updateStreamBuffer('part_1', ' World');
    });

    expect(result.current.streamBuffers.get('part_1')).toBe('Hello World');
  });

  it('flushes buffer on completion', () => {
    const { result } = renderHook(() => useDebateUIStore());

    act(() => {
      result.current.updateStreamBuffer('part_1', 'Complete');
    });

    const flushed = act(() => result.current.flushStreamBuffer('part_1'));

    expect(flushed).toBe('Complete');
    expect(result.current.streamBuffers.get('part_1')).toBeUndefined();
  });

  it('toggles cost tracker', () => {
    const { result } = renderHook(() => useDebateUIStore());

    expect(result.current.costTrackerExpanded).toBe(false);

    act(() => {
      result.current.toggleCostTracker();
    });

    expect(result.current.costTrackerExpanded).toBe(true);
  });
});
```

---

## State Debugging

### XState Inspector (Development)

```typescript
// frontend/src/app/providers.tsx

import { createBrowserInspector } from '@statelyai/inspect';

const inspector = createBrowserInspector();

export function Providers({ children }) {
  return (
    <>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <script
          dangerouslySetInnerHTML={{
            __html: `window.__xstate__ = ${JSON.stringify(inspector)}`,
          }}
        />
      )}
    </>
  );
}
```

### Zustand DevTools

```typescript
// Automatically enabled with devtools middleware
export const useDebateUIStore = create(
  devtools(
    (set) => ({ /* ... */ }),
    { name: 'DebateUIStore' }
  )
);

// View in Redux DevTools extension
```

---

## Migration from Chat Store

### Coexistence Strategy

```typescript
// frontend/src/stores/index.ts

// Existing chat store (unchanged)
export { useChatStore } from './chat-store';

// New debate store (separate)
export { useDebateUIStore } from './debate-store';

// No conflicts - independent state trees
```

### Shared Utilities

```typescript
// frontend/src/lib/utils/state-utils.ts

// Shared helpers for both chat and debate
export function serializeState(state: any): string {
  return JSON.stringify(state, (key, value) =>
    value instanceof Map ? Array.from(value.entries()) : value
  );
}

export function deserializeState(json: string): any {
  return JSON.parse(json, (key, value) =>
    Array.isArray(value) && value.every(Array.isArray)
      ? new Map(value)
      : value
  );
}
```

---

## Summary: XState vs Zustand

| Aspect | XState | Zustand |
|--------|--------|---------|
| **Purpose** | Business logic & flow | UI state & performance |
| **Updates** | Low frequency (state transitions) | High frequency (streaming) |
| **Persistence** | Full state snapshots | Preferences only |
| **Testing** | State machine tests | UI state tests |
| **Performance** | Deterministic transitions | Optimized re-renders |
| **Debugging** | XState Inspector | Redux DevTools |
| **Example** | `idle → debating → completed` | `streamBuffers.set()` |

---

## Next Steps

1. Implement XState machine with all 11 states
2. Create Zustand store with stream buffering
3. Build integration hooks (`useDebateMachine`, `useDebateSSE`)
4. Implement state persistence (localStorage + IndexedDB)
5. Add XState Inspector for debugging
6. Write comprehensive tests for both state layers
7. Optimize with selective subscriptions and memoization
8. Add state migration logic for version updates
