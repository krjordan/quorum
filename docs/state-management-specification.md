# Quorum State Management Specification

> **⚠️ Phase 2+ Documentation**
> This specification is for the **Multi-LLM Debate Engine** (Phase 2+), not the current Phase 1 simple chat interface.
> Phase 1 uses basic Zustand state management. See [PHASE1_COMPLETE.md](./PHASE1_COMPLETE.md) for current implementation.

## Executive Summary

This specification defines the state management architecture for Quorum, a real-time multi-LLM debate platform. The system manages 2-4 concurrent streaming LLM responses, judge assessments, debate lifecycle, and complex UI state across multiple domains.

**Recommended Solution**: **Zustand + XState** hybrid approach
- **Zustand**: Primary state management (lightweight, TypeScript-first, dev-friendly)
- **XState**: Debate lifecycle state machine (predictable transitions, visualizable)
- **React Query**: Server state and streaming management (caching, retry logic)

---

## 1. State Domain Breakdown

### 1.1 Debate Configuration State

```typescript
interface DebateConfig {
  topic: string;
  context?: string;
  format: DebateFormat;
  mode: 'simultaneous' | 'sequential';
  roundLimit?: number;
  participants: ParticipantConfig[];
  judgeConfig: JudgeConfig;
  createdAt: number;
  id: string;
}

type DebateFormat =
  | 'free-form'
  | 'structured-rounds'
  | 'round-limited'
  | 'convergence-seeking';

interface ParticipantConfig {
  id: string;
  providerId: string; // 'anthropic', 'openai', 'google', 'mistral'
  modelId: string;   // 'claude-3-5-sonnet-20241022', 'gpt-4', etc.
  personaMode: 'auto-assign' | 'custom';
  customPersona?: string;
  assignedPosition?: string; // Auto-assigned or custom
  displayName: string;
  colorCode: string; // UI color coding
}

interface JudgeConfig {
  providerId: string;
  modelId: string;
  displayAssessments: boolean; // Show per-round or final only
}
```

### 1.2 Participant State

```typescript
interface Participant {
  id: string;
  config: ParticipantConfig;
  status: ParticipantStatus;
  responseHistory: Response[];
  currentResponse?: StreamingResponse;
  tokenUsage: TokenUsage;
  errors: ParticipantError[];
  retryCount: number;
}

type ParticipantStatus =
  | 'idle'
  | 'streaming'
  | 'complete'
  | 'error'
  | 'rate-limited'
  | 'context-exceeded';

interface Response {
  id: string;
  participantId: string;
  roundNumber: number;
  content: string;
  timestamp: number;
  tokenCount: number;
  streamDuration: number; // milliseconds
}

interface StreamingResponse {
  content: string; // Accumulated so far
  startedAt: number;
  lastChunkAt: number;
  chunkCount: number;
}

interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  estimatedCost: number; // USD
}

interface ParticipantError {
  timestamp: number;
  type: 'network' | 'api' | 'rate-limit' | 'context-overflow' | 'timeout';
  message: string;
  retryable: boolean;
  recoveryAction?: string;
}
```

### 1.3 Judge State

```typescript
interface JudgeState {
  config: JudgeConfig;
  status: JudgeStatus;
  assessments: RoundAssessment[];
  finalVerdict?: FinalVerdict;
  tokenUsage: TokenUsage;
  errors: ParticipantError[];
}

type JudgeStatus =
  | 'idle'
  | 'analyzing'
  | 'complete'
  | 'error';

interface RoundAssessment {
  roundNumber: number;
  timestamp: number;
  quality: {
    relevance: number; // 0-10
    engagement: number; // 0-10
    novelty: number; // 0-10
  };
  flags: {
    repetitive: boolean;
    drifting: boolean;
    diminishingReturns: boolean;
  };
  shouldContinue: boolean;
  reasoning: string;
}

interface FinalVerdict {
  timestamp: number;
  summary: string;
  keyPoints: {
    participantId: string;
    points: string[];
  }[];
  areasOfAgreement: string[];
  areasOfDisagreement: string[];
  winner?: {
    participantId: string;
    reasoning: string;
  };
  qualityScore: number; // 0-100
}
```

### 1.4 Debate Lifecycle State

```typescript
interface DebateState {
  id: string;
  status: DebateStatus;
  config: DebateConfig;
  currentRound: number;
  totalRounds?: number; // For round-limited format
  participants: Record<string, Participant>;
  judge: JudgeState;
  timeline: TimelineEvent[];
  startedAt?: number;
  completedAt?: number;
  pausedAt?: number;
}

type DebateStatus =
  | 'configuring'
  | 'ready'
  | 'running'
  | 'paused'
  | 'completing'
  | 'completed'
  | 'error';

interface TimelineEvent {
  id: string;
  timestamp: number;
  type: 'round-start' | 'response-complete' | 'judge-assessment' | 'error' | 'status-change';
  data: any;
}
```

### 1.5 API Provider State

```typescript
interface APIProviderState {
  providers: Record<string, ProviderConfig>;
  activeProviders: string[];
  validationStatus: Record<string, ValidationStatus>;
}

interface ProviderConfig {
  id: string; // 'anthropic', 'openai', etc.
  name: string;
  apiKey: string;
  storageMode: 'local' | 'session';
  availableModels: ModelInfo[];
  rateLimits?: RateLimitConfig;
}

interface ModelInfo {
  id: string;
  displayName: string;
  contextWindow: number;
  supportsStreaming: boolean;
  costPerToken: {
    prompt: number;
    completion: number;
  };
}

type ValidationStatus =
  | 'unchecked'
  | 'validating'
  | 'valid'
  | 'invalid';

interface RateLimitConfig {
  requestsPerMinute: number;
  tokensPerMinute: number;
  currentUsage: {
    requests: number;
    tokens: number;
    resetAt: number;
  };
}
```

### 1.6 UI State

```typescript
interface UIState {
  activeView: 'setup' | 'debate' | 'history' | 'settings';
  settingsPanelOpen: boolean;
  exportDialogOpen: boolean;
  selectedDebateId?: string;
  filters: {
    showJudgeAssessments: boolean;
    highlightedParticipant?: string;
  };
  notifications: Notification[];
  isLoading: boolean;
  optimisticUpdates: Record<string, any>;
}

interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  message: string;
  timestamp: number;
  dismissible: boolean;
  action?: {
    label: string;
    handler: () => void;
  };
}
```

### 1.7 Persistence State

```typescript
interface PersistedState {
  debates: Record<string, DebateState>;
  apiKeys: Record<string, string>; // Encrypted
  userPreferences: UserPreferences;
  lastSyncedAt: number;
}

interface UserPreferences {
  defaultFormat: DebateFormat;
  defaultMode: 'simultaneous' | 'sequential';
  autoSaveEnabled: boolean;
  showCostEstimates: boolean;
  preferredProviders: string[];
  theme: 'light' | 'dark' | 'system';
}
```

---

## 2. State Management Library Evaluation

### 2.1 Comparison Matrix

| Feature | Zustand | Jotai | Redux Toolkit | XState |
|---------|---------|-------|---------------|--------|
| Bundle Size | 1.2kb | 2.9kb | 11kb | 18kb |
| Learning Curve | Low | Medium | High | High |
| TypeScript Support | Excellent | Excellent | Good | Excellent |
| DevTools | Good | Good | Excellent | Excellent |
| Boilerplate | Minimal | Minimal | Medium | Medium |
| State Machine Support | Manual | Manual | Manual | Native |
| Streaming/Async | Good | Excellent | Good | Excellent |
| Middleware Ecosystem | Good | Limited | Excellent | Good |
| Testing | Simple | Simple | Complex | Excellent |
| Community Size | Large | Growing | Very Large | Large |

### 2.2 Recommendation: Zustand + XState Hybrid

**Primary Store (Zustand)** for global state:
- Minimal boilerplate, easy to learn for contributors
- Excellent TypeScript inference
- No providers needed, just hooks
- Built-in immer middleware for immutable updates
- Persistence middleware available
- Small bundle size critical for client-side app

**State Machine (XState)** for debate lifecycle:
- Complex state transitions (configuring → ready → running → paused → completing → completed)
- Guards for transition validation
- Actions for side effects
- Visualizable state chart for documentation
- Predictable error handling
- Testable state logic

**React Query** for streaming and API state:
- Built-in retry logic with exponential backoff
- Request deduplication
- Optimistic updates
- Cache management
- SSE/streaming support via custom hooks

### 2.3 Why Not Others

**Jotai**: Atomic approach excellent but overkill for this use case. Better for highly modular state.

**Redux Toolkit**: Too much boilerplate for open-source project. Harder onboarding for contributors.

**Context + Reducer**: No devtools, harder debugging for complex streaming state.

**Recoil**: Still experimental, smaller ecosystem, Facebook-centric.

---

## 3. State Machine Design - Debate Lifecycle

### 3.1 XState Machine Definition

```typescript
import { createMachine, assign } from 'xstate';

const debateMachine = createMachine({
  id: 'debate',
  initial: 'configuring',
  context: {
    config: null,
    currentRound: 0,
    participants: {},
    judge: null,
    errors: [],
  },
  states: {
    configuring: {
      on: {
        SET_CONFIG: {
          actions: assign({ config: (_, event) => event.config }),
        },
        VALIDATE: {
          target: 'validating',
        },
      },
    },
    validating: {
      invoke: {
        src: 'validateConfiguration',
        onDone: {
          target: 'ready',
          actions: assign({ errors: [] }),
        },
        onError: {
          target: 'configuring',
          actions: assign({
            errors: (_, event) => event.data.errors
          }),
        },
      },
    },
    ready: {
      on: {
        START: {
          target: 'initializing',
          cond: 'hasValidConfig',
        },
        EDIT_CONFIG: 'configuring',
      },
    },
    initializing: {
      invoke: {
        src: 'initializeDebate',
        onDone: {
          target: 'running',
          actions: assign({
            participants: (_, event) => event.data.participants,
            judge: (_, event) => event.data.judge,
            currentRound: 1,
          }),
        },
        onError: {
          target: 'error',
          actions: assign({ errors: (_, event) => [event.data] }),
        },
      },
    },
    running: {
      initial: 'awaitingResponses',
      on: {
        PAUSE: 'paused',
        FORCE_STOP: 'completing',
      },
      states: {
        awaitingResponses: {
          invoke: {
            src: 'streamResponses',
            onDone: 'judging',
          },
          on: {
            RESPONSE_CHUNK: {
              actions: 'updateStreamingResponse',
            },
            RESPONSE_COMPLETE: {
              actions: 'finalizeResponse',
            },
            RESPONSE_ERROR: {
              actions: 'handleResponseError',
            },
          },
        },
        judging: {
          invoke: {
            src: 'getJudgeAssessment',
            onDone: [
              {
                target: '#debate.completing',
                cond: 'shouldEndDebate',
                actions: 'storeAssessment',
              },
              {
                target: 'roundComplete',
                actions: 'storeAssessment',
              },
            ],
            onError: {
              target: 'awaitingResponses',
              actions: 'handleJudgeError',
            },
          },
        },
        roundComplete: {
          after: {
            1000: [
              {
                target: 'awaitingResponses',
                cond: 'canContinue',
                actions: assign({
                  currentRound: (ctx) => ctx.currentRound + 1
                }),
              },
              {
                target: '#debate.completing',
              },
            ],
          },
        },
      },
    },
    paused: {
      on: {
        RESUME: 'running',
        STOP: 'completing',
      },
    },
    completing: {
      invoke: {
        src: 'getFinalVerdict',
        onDone: {
          target: 'completed',
          actions: assign({
            judge: (ctx, event) => ({
              ...ctx.judge,
              finalVerdict: event.data,
            }),
          }),
        },
        onError: {
          target: 'error',
          actions: assign({ errors: (_, event) => [event.data] }),
        },
      },
    },
    completed: {
      type: 'final',
      entry: 'saveDebateToHistory',
    },
    error: {
      on: {
        RETRY: {
          target: 'ready',
          actions: assign({ errors: [] }),
        },
        RESET: 'configuring',
      },
    },
  },
});
```

### 3.2 State Transition Guards

```typescript
const guards = {
  hasValidConfig: (context) => {
    return (
      context.config?.topic?.trim().length > 0 &&
      context.config?.participants?.length >= 2 &&
      context.config?.participants?.length <= 4 &&
      context.config?.judgeConfig != null
    );
  },

  shouldEndDebate: (context, event) => {
    const assessment = event.data;
    const config = context.config;

    // Check format-specific end conditions
    if (config.format === 'round-limited') {
      return context.currentRound >= config.roundLimit;
    }

    if (config.format === 'convergence-seeking') {
      return assessment.flags.convergenceReached;
    }

    // Free-form and structured: judge decides
    return !assessment.shouldContinue;
  },

  canContinue: (context) => {
    const hasErrors = Object.values(context.participants).some(
      p => p.status === 'error' && !p.retryable
    );

    const contextExceeded = Object.values(context.participants).some(
      p => p.status === 'context-exceeded'
    );

    return !hasErrors && !contextExceeded;
  },
};
```

### 3.3 State Machine Actions

```typescript
const actions = {
  updateStreamingResponse: assign({
    participants: (context, event) => ({
      ...context.participants,
      [event.participantId]: {
        ...context.participants[event.participantId],
        currentResponse: {
          ...context.participants[event.participantId].currentResponse,
          content: event.chunk,
          lastChunkAt: Date.now(),
          chunkCount: context.participants[event.participantId].currentResponse.chunkCount + 1,
        },
      },
    }),
  }),

  finalizeResponse: assign({
    participants: (context, event) => {
      const participant = context.participants[event.participantId];
      const response: Response = {
        id: generateId(),
        participantId: event.participantId,
        roundNumber: context.currentRound,
        content: participant.currentResponse.content,
        timestamp: Date.now(),
        tokenCount: event.tokenCount,
        streamDuration: Date.now() - participant.currentResponse.startedAt,
      };

      return {
        ...context.participants,
        [event.participantId]: {
          ...participant,
          status: 'complete',
          responseHistory: [...participant.responseHistory, response],
          currentResponse: undefined,
          tokenUsage: {
            promptTokens: participant.tokenUsage.promptTokens + event.usage.prompt,
            completionTokens: participant.tokenUsage.completionTokens + event.usage.completion,
            totalTokens: participant.tokenUsage.totalTokens + event.usage.total,
            estimatedCost: participant.tokenUsage.estimatedCost + event.usage.cost,
          },
        },
      };
    },
  }),

  handleResponseError: assign({
    participants: (context, event) => ({
      ...context.participants,
      [event.participantId]: {
        ...context.participants[event.participantId],
        status: 'error',
        errors: [
          ...context.participants[event.participantId].errors,
          event.error,
        ],
        retryCount: context.participants[event.participantId].retryCount + 1,
      },
    }),
  }),

  storeAssessment: assign({
    judge: (context, event) => ({
      ...context.judge,
      assessments: [...context.judge.assessments, event.data],
    }),
  }),

  handleJudgeError: assign({
    judge: (context, event) => ({
      ...context.judge,
      status: 'error',
      errors: [...context.judge.errors, event.data],
    }),
  }),

  saveDebateToHistory: (context) => {
    // Persist to localStorage/IndexedDB
    persistDebate(context);
  },
};
```

### 3.4 State Machine Visualization

```
┌──────────────┐
│ configuring  │
└──────┬───────┘
       │ VALIDATE
       ▼
┌──────────────┐
│  validating  │
└──────┬───────┘
       │ onDone
       ▼
┌──────────────┐
│    ready     │◄─────────┐
└──────┬───────┘          │
       │ START            │ RETRY
       ▼                  │
┌──────────────┐          │
│ initializing │          │
└──────┬───────┘          │
       │ onDone           │
       ▼                  │
┌──────────────────────────────┐
│         running              │
│ ┌────────────────────────┐   │
│ │ awaitingResponses      │   │
│ └──────┬─────────────────┘   │
│        │ onDone              │
│        ▼                     │
│ ┌────────────────────────┐   │
│ │      judging           │   │
│ └──────┬─────────────────┘   │
│        │ shouldEndDebate?    │
│        ├─────────────────┐   │
│        │ NO              │   │
│        ▼                 │ YES
│ ┌────────────────────┐   │   │
│ │  roundComplete     │   │   │
│ └──────┬─────────────┘   │   │
│        │ after 1s        │   │
│        └─────────────────┘   │
└──────────────┬───────────────┘
               │
               ▼
        ┌──────────────┐
        │  completing  │
        └──────┬───────┘
               │ onDone
               ▼
        ┌──────────────┐
        │  completed   │
        └──────────────┘
```

---

## 4. Zustand Store Architecture

### 4.1 Store Slices Pattern

```typescript
// stores/debateStore.ts
import create from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// Slice creators
const createDebateSlice = (set, get) => ({
  debates: {},
  activeDebateId: null,

  createDebate: (config: DebateConfig) => set((state) => {
    const id = generateId();
    state.debates[id] = {
      id,
      status: 'configuring',
      config,
      currentRound: 0,
      participants: {},
      judge: initializeJudge(config.judgeConfig),
      timeline: [],
    };
    state.activeDebateId = id;
  }),

  updateDebateConfig: (debateId: string, updates: Partial<DebateConfig>) =>
    set((state) => {
      if (state.debates[debateId]) {
        state.debates[debateId].config = {
          ...state.debates[debateId].config,
          ...updates,
        };
      }
    }),

  setActiveDebate: (debateId: string) => set({ activeDebateId: debateId }),

  getActiveDebate: () => {
    const { debates, activeDebateId } = get();
    return activeDebateId ? debates[activeDebateId] : null;
  },
});

const createParticipantSlice = (set, get) => ({
  updateParticipant: (debateId: string, participantId: string, updates: Partial<Participant>) =>
    set((state) => {
      if (state.debates[debateId]?.participants[participantId]) {
        state.debates[debateId].participants[participantId] = {
          ...state.debates[debateId].participants[participantId],
          ...updates,
        };
      }
    }),

  addStreamChunk: (debateId: string, participantId: string, chunk: string) =>
    set((state) => {
      const participant = state.debates[debateId]?.participants[participantId];
      if (participant?.currentResponse) {
        participant.currentResponse.content += chunk;
        participant.currentResponse.lastChunkAt = Date.now();
        participant.currentResponse.chunkCount += 1;
      }
    }),

  finalizeParticipantResponse: (
    debateId: string,
    participantId: string,
    tokenUsage: TokenUsage
  ) =>
    set((state) => {
      const participant = state.debates[debateId]?.participants[participantId];
      if (!participant?.currentResponse) return;

      const response: Response = {
        id: generateId(),
        participantId,
        roundNumber: state.debates[debateId].currentRound,
        content: participant.currentResponse.content,
        timestamp: Date.now(),
        tokenCount: tokenUsage.totalTokens,
        streamDuration: Date.now() - participant.currentResponse.startedAt,
      };

      participant.responseHistory.push(response);
      participant.currentResponse = undefined;
      participant.status = 'complete';
      participant.tokenUsage = {
        promptTokens: participant.tokenUsage.promptTokens + tokenUsage.promptTokens,
        completionTokens: participant.tokenUsage.completionTokens + tokenUsage.completionTokens,
        totalTokens: participant.tokenUsage.totalTokens + tokenUsage.totalTokens,
        estimatedCost: participant.tokenUsage.estimatedCost + tokenUsage.estimatedCost,
      };
    }),
});

const createJudgeSlice = (set, get) => ({
  addJudgeAssessment: (debateId: string, assessment: RoundAssessment) =>
    set((state) => {
      state.debates[debateId]?.judge.assessments.push(assessment);
    }),

  setFinalVerdict: (debateId: string, verdict: FinalVerdict) =>
    set((state) => {
      if (state.debates[debateId]) {
        state.debates[debateId].judge.finalVerdict = verdict;
        state.debates[debateId].status = 'completed';
        state.debates[debateId].completedAt = Date.now();
      }
    }),
});

const createUISlice = (set, get) => ({
  ui: {
    activeView: 'setup',
    settingsPanelOpen: false,
    exportDialogOpen: false,
    filters: {
      showJudgeAssessments: false,
    },
    notifications: [],
    isLoading: false,
    optimisticUpdates: {},
  },

  setActiveView: (view: UIState['activeView']) =>
    set((state) => { state.ui.activeView = view; }),

  toggleSettingsPanel: () =>
    set((state) => { state.ui.settingsPanelOpen = !state.ui.settingsPanelOpen; }),

  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) =>
    set((state) => {
      state.ui.notifications.push({
        ...notification,
        id: generateId(),
        timestamp: Date.now(),
      });
    }),

  dismissNotification: (id: string) =>
    set((state) => {
      state.ui.notifications = state.ui.notifications.filter(n => n.id !== id);
    }),

  setLoading: (isLoading: boolean) =>
    set((state) => { state.ui.isLoading = isLoading; }),
});

const createProviderSlice = (set, get) => ({
  providers: {},
  activeProviders: [],
  validationStatus: {},

  addProvider: (provider: ProviderConfig) =>
    set((state) => {
      state.providers[provider.id] = provider;
      state.validationStatus[provider.id] = 'unchecked';
    }),

  validateProvider: async (providerId: string) => {
    set((state) => { state.validationStatus[providerId] = 'validating'; });

    try {
      const isValid = await validateAPIKey(
        providerId,
        get().providers[providerId].apiKey
      );

      set((state) => {
        state.validationStatus[providerId] = isValid ? 'valid' : 'invalid';
        if (isValid && !state.activeProviders.includes(providerId)) {
          state.activeProviders.push(providerId);
        }
      });

      return isValid;
    } catch (error) {
      set((state) => { state.validationStatus[providerId] = 'invalid'; });
      return false;
    }
  },

  removeProvider: (providerId: string) =>
    set((state) => {
      delete state.providers[providerId];
      delete state.validationStatus[providerId];
      state.activeProviders = state.activeProviders.filter(id => id !== providerId);
    }),
});

// Combined store with middleware
export const useStore = create(
  devtools(
    persist(
      immer((set, get) => ({
        ...createDebateSlice(set, get),
        ...createParticipantSlice(set, get),
        ...createJudgeSlice(set, get),
        ...createUISlice(set, get),
        ...createProviderSlice(set, get),
      })),
      {
        name: 'quorum-storage',
        partialize: (state) => ({
          // Only persist certain slices
          providers: state.providers,
          debates: state.debates,
          ui: {
            activeView: state.ui.activeView,
            filters: state.ui.filters,
          },
        }),
      }
    )
  )
);
```

### 4.2 Selectors for Performance

```typescript
// stores/selectors.ts
import { useStore } from './debateStore';
import { shallow } from 'zustand/shallow';

// Memoized selectors to prevent unnecessary re-renders

export const useActiveDebate = () =>
  useStore((state) => {
    const id = state.activeDebateId;
    return id ? state.debates[id] : null;
  });

export const useDebateParticipants = (debateId: string) =>
  useStore(
    (state) => state.debates[debateId]?.participants || {},
    shallow
  );

export const useParticipantStatus = (debateId: string, participantId: string) =>
  useStore((state) =>
    state.debates[debateId]?.participants[participantId]?.status
  );

export const useStreamingContent = (debateId: string, participantId: string) =>
  useStore((state) =>
    state.debates[debateId]?.participants[participantId]?.currentResponse?.content || ''
  );

export const useJudgeAssessments = (debateId: string) =>
  useStore(
    (state) => state.debates[debateId]?.judge.assessments || [],
    shallow
  );

export const useTotalCost = (debateId: string) =>
  useStore((state) => {
    const participants = state.debates[debateId]?.participants || {};
    return Object.values(participants).reduce(
      (sum, p) => sum + p.tokenUsage.estimatedCost,
      0
    );
  });

export const useActiveProviders = () =>
  useStore(
    (state) => state.activeProviders.map(id => state.providers[id]),
    shallow
  );

export const useNotifications = () =>
  useStore((state) => state.ui.notifications, shallow);
```

---

## 5. Streaming State Management Patterns

### 5.1 React Query for Stream Management

```typescript
// hooks/useStreamResponse.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { useStore } from '../stores/debateStore';

export const useStreamResponse = (debateId: string, participantId: string) => {
  const addStreamChunk = useStore((state) => state.addStreamChunk);
  const finalizeResponse = useStore((state) => state.finalizeParticipantResponse);

  return useMutation({
    mutationFn: async ({ prompt, context }: { prompt: string; context: string[] }) => {
      const participant = useStore.getState().debates[debateId].participants[participantId];
      const provider = useStore.getState().providers[participant.config.providerId];

      const stream = await initiateStream(provider, participant.config.modelId, prompt, context);

      // Track streaming state
      useStore.getState().updateParticipant(debateId, participantId, {
        status: 'streaming',
        currentResponse: {
          content: '',
          startedAt: Date.now(),
          lastChunkAt: Date.now(),
          chunkCount: 0,
        },
      });

      let fullContent = '';
      let tokenUsage = { promptTokens: 0, completionTokens: 0, totalTokens: 0, estimatedCost: 0 };

      for await (const chunk of stream) {
        if (chunk.type === 'content') {
          fullContent += chunk.text;
          addStreamChunk(debateId, participantId, chunk.text);
        } else if (chunk.type === 'usage') {
          tokenUsage = chunk.usage;
        }
      }

      finalizeResponse(debateId, participantId, tokenUsage);

      return { content: fullContent, tokenUsage };
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    onError: (error, variables) => {
      useStore.getState().updateParticipant(debateId, participantId, {
        status: 'error',
        errors: [{
          timestamp: Date.now(),
          type: 'network',
          message: error.message,
          retryable: true,
        }],
      });
    },
  });
};
```

### 5.2 Simultaneous Streaming Pattern

```typescript
// hooks/useSimultaneousRound.ts
import { useStore } from '../stores/debateStore';
import { useStreamResponse } from './useStreamResponse';

export const useSimultaneousRound = (debateId: string) => {
  const debate = useStore((state) => state.debates[debateId]);

  const streamMutations = Object.keys(debate.participants).map(participantId =>
    useStreamResponse(debateId, participantId)
  );

  const executeRound = async () => {
    const participants = debate.participants;
    const context = buildContextHistory(debate);

    // Start all streams in parallel
    const streamPromises = Object.entries(participants).map(([participantId, participant]) => {
      const prompt = buildDebaterPrompt(participant, context);
      return streamMutations
        .find(m => m.variables?.participantId === participantId)
        ?.mutateAsync({ prompt, context });
    });

    // Wait for all to complete
    const results = await Promise.allSettled(streamPromises);

    // Handle failures
    const failures = results.filter(r => r.status === 'rejected');
    if (failures.length > 0) {
      useStore.getState().addNotification({
        type: 'error',
        message: `${failures.length} participant(s) failed to respond`,
        dismissible: true,
      });
    }

    // Trigger judge assessment if all participants responded
    const successCount = results.filter(r => r.status === 'fulfilled').length;
    if (successCount === Object.keys(participants).length) {
      return triggerJudgeAssessment(debateId);
    }
  };

  return { executeRound, isExecuting: streamMutations.some(m => m.isPending) };
};
```

### 5.3 Sequential Streaming Pattern

```typescript
// hooks/useSequentialRound.ts
import { useStore } from '../stores/debateStore';
import { useStreamResponse } from './useStreamResponse';

export const useSequentialRound = (debateId: string) => {
  const debate = useStore((state) => state.debates[debateId]);

  const executeRound = async () => {
    const participantIds = Object.keys(debate.participants);
    const context = buildContextHistory(debate);

    for (const participantId of participantIds) {
      const participant = debate.participants[participantId];
      const prompt = buildDebaterPrompt(participant, context);

      try {
        const mutation = useStreamResponse(debateId, participantId);
        await mutation.mutateAsync({ prompt, context });

        // Update context for next participant
        context.push(participant.responseHistory[participant.responseHistory.length - 1]);

      } catch (error) {
        useStore.getState().addNotification({
          type: 'error',
          message: `${participant.config.displayName} failed to respond: ${error.message}`,
          dismissible: true,
          action: {
            label: 'Retry',
            handler: () => {
              // Retry this participant
              const mutation = useStreamResponse(debateId, participantId);
              mutation.mutate({ prompt, context });
            },
          },
        });

        // Continue to next participant or stop?
        if (!error.retryable) {
          break;
        }
      }
    }

    // Trigger judge assessment after all participants
    return triggerJudgeAssessment(debateId);
  };

  return { executeRound };
};
```

### 5.4 Rate Limit Queue Management

```typescript
// services/rateLimitQueue.ts
import PQueue from 'p-queue';

class ProviderQueue {
  private queues: Map<string, PQueue> = new Map();

  getQueue(providerId: string): PQueue {
    if (!this.queues.has(providerId)) {
      const provider = useStore.getState().providers[providerId];
      const rateLimit = provider.rateLimits;

      this.queues.set(providerId, new PQueue({
        concurrency: Math.min(rateLimit?.requestsPerMinute || 10, 5),
        interval: 60000, // 1 minute
        intervalCap: rateLimit?.requestsPerMinute || 10,
      }));
    }

    return this.queues.get(providerId)!;
  }

  async enqueue<T>(providerId: string, fn: () => Promise<T>): Promise<T> {
    const queue = this.getQueue(providerId);
    return queue.add(fn);
  }

  getQueueSize(providerId: string): number {
    return this.getQueue(providerId).size;
  }

  getPendingCount(providerId: string): number {
    return this.getQueue(providerId).pending;
  }
}

export const providerQueue = new ProviderQueue();

// Usage in stream hook
export const useStreamResponse = (debateId: string, participantId: string) => {
  const addStreamChunk = useStore((state) => state.addStreamChunk);

  return useMutation({
    mutationFn: async ({ prompt, context }) => {
      const participant = useStore.getState().debates[debateId].participants[participantId];
      const providerId = participant.config.providerId;

      // Enqueue request to respect rate limits
      return providerQueue.enqueue(providerId, async () => {
        const stream = await initiateStream(...);
        // ... streaming logic
      });
    },
  });
};
```

---

## 6. Error Handling and Recovery

### 6.1 Error Classification

```typescript
// types/errors.ts
export class QuorumError extends Error {
  constructor(
    message: string,
    public readonly type: ErrorType,
    public readonly retryable: boolean,
    public readonly recoveryAction?: string,
    public readonly metadata?: Record<string, any>
  ) {
    super(message);
    this.name = 'QuorumError';
  }
}

export type ErrorType =
  | 'network'
  | 'api'
  | 'rate-limit'
  | 'context-overflow'
  | 'timeout'
  | 'authentication'
  | 'validation';

export const ERROR_RECOVERY_STRATEGIES: Record<ErrorType, RecoveryStrategy> = {
  network: {
    retryable: true,
    maxRetries: 3,
    backoff: 'exponential',
    userAction: 'Check your internet connection',
  },
  api: {
    retryable: true,
    maxRetries: 2,
    backoff: 'linear',
    userAction: 'The API returned an error. Please try again.',
  },
  'rate-limit': {
    retryable: true,
    maxRetries: 5,
    backoff: 'exponential',
    userAction: 'Rate limit reached. Waiting before retry...',
    delayMs: 60000,
  },
  'context-overflow': {
    retryable: false,
    maxRetries: 0,
    userAction: 'Conversation too long. Consider summarization or ending debate.',
    recoveryOptions: ['summarize', 'end-debate'],
  },
  timeout: {
    retryable: true,
    maxRetries: 2,
    backoff: 'linear',
    userAction: 'Request timed out. Retrying...',
  },
  authentication: {
    retryable: false,
    maxRetries: 0,
    userAction: 'Invalid API key. Please check your settings.',
    recoveryOptions: ['update-api-key'],
  },
  validation: {
    retryable: false,
    maxRetries: 0,
    userAction: 'Configuration error. Please review your settings.',
  },
};

interface RecoveryStrategy {
  retryable: boolean;
  maxRetries: number;
  backoff?: 'linear' | 'exponential';
  userAction: string;
  delayMs?: number;
  recoveryOptions?: string[];
}
```

### 6.2 Error Boundary Component

```typescript
// components/ErrorBoundary.tsx
import React from 'react';
import { useStore } from '../stores/debateStore';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, { error: Error | null }> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);

    // Log to store for debugging
    useStore.getState().addNotification({
      type: 'error',
      message: `Application error: ${error.message}`,
      dismissible: true,
    });
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      return <FallbackComponent error={this.state.error} reset={this.reset} />;
    }

    return this.props.children;
  }
}

const DefaultErrorFallback: React.FC<{ error: Error; reset: () => void }> = ({ error, reset }) => (
  <div className="error-fallback">
    <h2>Something went wrong</h2>
    <pre>{error.message}</pre>
    <button onClick={reset}>Try again</button>
  </div>
);
```

### 6.3 Optimistic Updates with Rollback

```typescript
// hooks/useOptimisticUpdate.ts
import { useStore } from '../stores/debateStore';

export const useOptimisticUpdate = () => {
  const setOptimisticUpdate = useStore((state) => state.setOptimisticUpdate);
  const clearOptimisticUpdate = useStore((state) => state.clearOptimisticUpdate);

  const performOptimistic = async <T,>(
    updateId: string,
    optimisticData: any,
    asyncFn: () => Promise<T>,
    rollbackFn: () => void
  ): Promise<T> => {
    // Apply optimistic update
    setOptimisticUpdate(updateId, optimisticData);

    try {
      const result = await asyncFn();
      clearOptimisticUpdate(updateId);
      return result;
    } catch (error) {
      // Rollback on failure
      rollbackFn();
      clearOptimisticUpdate(updateId);
      throw error;
    }
  };

  return { performOptimistic };
};

// Example usage
const { performOptimistic } = useOptimisticUpdate();

await performOptimistic(
  'add-participant-response',
  { participantId, optimisticResponse: '...' },
  async () => {
    return await streamResponse(participantId, prompt);
  },
  () => {
    // Rollback: remove optimistic response
    useStore.getState().removeParticipantResponse(debateId, participantId, 'optimistic-id');
  }
);
```

### 6.4 Circuit Breaker Pattern

```typescript
// services/circuitBreaker.ts
class CircuitBreaker {
  private failures: Map<string, number> = new Map();
  private lastFailureTime: Map<string, number> = new Map();
  private state: Map<string, 'closed' | 'open' | 'half-open'> = new Map();

  private readonly threshold = 5; // failures
  private readonly timeout = 60000; // 1 minute

  async execute<T>(
    key: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const currentState = this.state.get(key) || 'closed';

    if (currentState === 'open') {
      const lastFailure = this.lastFailureTime.get(key) || 0;
      const elapsed = Date.now() - lastFailure;

      if (elapsed < this.timeout) {
        throw new QuorumError(
          'Circuit breaker is open',
          'rate-limit',
          true,
          'Wait before retrying',
          { timeRemaining: this.timeout - elapsed }
        );
      }

      // Try half-open
      this.state.set(key, 'half-open');
    }

    try {
      const result = await fn();

      // Success: reset
      this.failures.set(key, 0);
      this.state.set(key, 'closed');

      return result;
    } catch (error) {
      const failureCount = (this.failures.get(key) || 0) + 1;
      this.failures.set(key, failureCount);
      this.lastFailureTime.set(key, Date.now());

      if (failureCount >= this.threshold) {
        this.state.set(key, 'open');
      }

      throw error;
    }
  }

  reset(key: string) {
    this.failures.set(key, 0);
    this.state.set(key, 'closed');
  }

  getState(key: string) {
    return this.state.get(key) || 'closed';
  }
}

export const circuitBreaker = new CircuitBreaker();
```

---

## 7. Local Persistence Strategy

### 7.1 Storage Layer Abstraction

```typescript
// services/storage.ts
interface StorageAdapter {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T): Promise<void>;
  remove(key: string): Promise<void>;
  clear(): Promise<void>;
  keys(): Promise<string[]>;
}

class LocalStorageAdapter implements StorageAdapter {
  async get<T>(key: string): Promise<T | null> {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  }

  async set<T>(key: string, value: T): Promise<void> {
    localStorage.setItem(key, JSON.stringify(value));
  }

  async remove(key: string): Promise<void> {
    localStorage.removeItem(key);
  }

  async clear(): Promise<void> {
    localStorage.clear();
  }

  async keys(): Promise<string[]> {
    return Object.keys(localStorage);
  }
}

class IndexedDBAdapter implements StorageAdapter {
  private dbName = 'quorum-db';
  private storeName = 'debates';
  private db: IDBDatabase | null = null;

  private async getDB(): Promise<IDBDatabase> {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName);
        }
      };
    });
  }

  async get<T>(key: string): Promise<T | null> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result || null);
    });
  }

  async set<T>(key: string, value: T): Promise<void> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put(value, key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async remove(key: string): Promise<void> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async clear(): Promise<void> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async keys(): Promise<string[]> {
    const db = await this.getDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAllKeys();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result as string[]);
    });
  }
}

// Factory
export const createStorage = (type: 'localStorage' | 'indexedDB'): StorageAdapter => {
  return type === 'indexedDB' ? new IndexedDBAdapter() : new LocalStorageAdapter();
};

// Default storage
export const storage = createStorage('indexedDB');
```

### 7.2 Encrypted API Key Storage

```typescript
// services/keyStorage.ts
import CryptoJS from 'crypto-js';

class KeyStorage {
  private readonly storageKey = 'quorum-api-keys';
  private encryptionKey: string | null = null;

  // Generate encryption key from user session (or prompt for password)
  async initialize(): Promise<void> {
    // For MVP: use device fingerprint + timestamp
    // For production: user-provided password
    this.encryptionKey = await this.generateEncryptionKey();
  }

  private async generateEncryptionKey(): Promise<string> {
    const deviceId = await this.getDeviceId();
    return CryptoJS.SHA256(deviceId).toString();
  }

  private async getDeviceId(): Promise<string> {
    // Simple device fingerprint
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillText('device-id', 2, 2);
      return canvas.toDataURL();
    }
    return navigator.userAgent;
  }

  async storeKey(providerId: string, apiKey: string, mode: 'local' | 'session'): Promise<void> {
    if (!this.encryptionKey) await this.initialize();

    const keys = await this.getAllKeys();
    keys[providerId] = {
      encrypted: CryptoJS.AES.encrypt(apiKey, this.encryptionKey!).toString(),
      mode,
      storedAt: Date.now(),
    };

    const storage = mode === 'local' ? localStorage : sessionStorage;
    storage.setItem(this.storageKey, JSON.stringify(keys));
  }

  async getKey(providerId: string): Promise<string | null> {
    if (!this.encryptionKey) await this.initialize();

    const keys = await this.getAllKeys();
    const keyData = keys[providerId];

    if (!keyData) return null;

    try {
      const decrypted = CryptoJS.AES.decrypt(keyData.encrypted, this.encryptionKey!);
      return decrypted.toString(CryptoJS.enc.Utf8);
    } catch (error) {
      console.error('Failed to decrypt API key:', error);
      return null;
    }
  }

  async removeKey(providerId: string): Promise<void> {
    const keys = await this.getAllKeys();
    delete keys[providerId];

    localStorage.setItem(this.storageKey, JSON.stringify(keys));
    sessionStorage.removeItem(this.storageKey);
  }

  private async getAllKeys(): Promise<Record<string, any>> {
    const localKeys = localStorage.getItem(this.storageKey);
    const sessionKeys = sessionStorage.getItem(this.storageKey);

    return {
      ...(localKeys ? JSON.parse(localKeys) : {}),
      ...(sessionKeys ? JSON.parse(sessionKeys) : {}),
    };
  }

  async clearAll(): Promise<void> {
    localStorage.removeItem(this.storageKey);
    sessionStorage.removeItem(this.storageKey);
  }
}

export const keyStorage = new KeyStorage();
```

### 7.3 Debate History Persistence

```typescript
// services/debateHistory.ts
import { storage } from './storage';
import { DebateState } from '../types';

class DebateHistory {
  private readonly prefix = 'debate:';
  private readonly indexKey = 'debate-index';

  async saveDebate(debate: DebateState): Promise<void> {
    // Save debate
    await storage.set(`${this.prefix}${debate.id}`, debate);

    // Update index
    const index = await this.getIndex();
    if (!index.includes(debate.id)) {
      index.push(debate.id);
      await storage.set(this.indexKey, index);
    }
  }

  async getDebate(debateId: string): Promise<DebateState | null> {
    return storage.get(`${this.prefix}${debateId}`);
  }

  async getAllDebates(): Promise<DebateState[]> {
    const index = await this.getIndex();
    const debates = await Promise.all(
      index.map(id => this.getDebate(id))
    );
    return debates.filter(Boolean) as DebateState[];
  }

  async deleteDebate(debateId: string): Promise<void> {
    await storage.remove(`${this.prefix}${debateId}`);

    const index = await this.getIndex();
    const updated = index.filter(id => id !== debateId);
    await storage.set(this.indexKey, updated);
  }

  async searchDebates(query: string): Promise<DebateState[]> {
    const debates = await this.getAllDebates();
    const lowerQuery = query.toLowerCase();

    return debates.filter(debate =>
      debate.config.topic.toLowerCase().includes(lowerQuery) ||
      debate.config.context?.toLowerCase().includes(lowerQuery)
    );
  }

  async getRecentDebates(limit: number = 10): Promise<DebateState[]> {
    const debates = await this.getAllDebates();
    return debates
      .sort((a, b) => (b.startedAt || 0) - (a.startedAt || 0))
      .slice(0, limit);
  }

  private async getIndex(): Promise<string[]> {
    const index = await storage.get<string[]>(this.indexKey);
    return index || [];
  }

  async export(debateId: string, format: 'json' | 'markdown'): Promise<string> {
    const debate = await this.getDebate(debateId);
    if (!debate) throw new Error('Debate not found');

    if (format === 'json') {
      return JSON.stringify(debate, null, 2);
    }

    // Markdown export
    return this.toMarkdown(debate);
  }

  private toMarkdown(debate: DebateState): string {
    let md = `# ${debate.config.topic}\n\n`;

    if (debate.config.context) {
      md += `**Context**: ${debate.config.context}\n\n`;
    }

    md += `**Format**: ${debate.config.format}\n`;
    md += `**Mode**: ${debate.config.mode}\n\n`;

    md += `## Participants\n\n`;
    Object.values(debate.participants).forEach(p => {
      md += `- **${p.config.displayName}** (${p.config.modelId})\n`;
      if (p.config.assignedPosition) {
        md += `  Position: ${p.config.assignedPosition}\n`;
      }
    });

    md += `\n## Debate\n\n`;

    // Group responses by round
    const rounds = new Map<number, Response[]>();
    Object.values(debate.participants).forEach(p => {
      p.responseHistory.forEach(r => {
        if (!rounds.has(r.roundNumber)) {
          rounds.set(r.roundNumber, []);
        }
        rounds.get(r.roundNumber)!.push(r);
      });
    });

    Array.from(rounds.entries())
      .sort(([a], [b]) => a - b)
      .forEach(([roundNum, responses]) => {
        md += `### Round ${roundNum}\n\n`;
        responses.forEach(r => {
          const participant = debate.participants[r.participantId];
          md += `**${participant.config.displayName}**:\n\n${r.content}\n\n`;
        });
      });

    if (debate.judge.finalVerdict) {
      md += `## Final Verdict\n\n`;
      md += `${debate.judge.finalVerdict.summary}\n\n`;

      if (debate.judge.finalVerdict.winner) {
        const winner = debate.participants[debate.judge.finalVerdict.winner.participantId];
        md += `**Winner**: ${winner.config.displayName}\n\n`;
        md += `${debate.judge.finalVerdict.winner.reasoning}\n\n`;
      }
    }

    return md;
  }
}

export const debateHistory = new DebateHistory();
```

---

## 8. Real-Time State Synchronization

### 8.1 Subscription Pattern for State Changes

```typescript
// hooks/useDebateSubscription.ts
import { useEffect } from 'react';
import { useStore } from '../stores/debateStore';

export const useDebateSubscription = (
  debateId: string,
  callbacks: {
    onRoundStart?: (roundNumber: number) => void;
    onResponseComplete?: (participantId: string, response: Response) => void;
    onJudgeAssessment?: (assessment: RoundAssessment) => void;
    onStatusChange?: (status: DebateStatus) => void;
    onError?: (error: ParticipantError) => void;
  }
) => {
  useEffect(() => {
    // Subscribe to specific state changes
    const unsubscribe = useStore.subscribe(
      (state) => state.debates[debateId],
      (debate, prevDebate) => {
        if (!debate || !prevDebate) return;

        // Round start detection
        if (debate.currentRound !== prevDebate.currentRound) {
          callbacks.onRoundStart?.(debate.currentRound);
        }

        // Response completion detection
        Object.entries(debate.participants).forEach(([id, participant]) => {
          const prevParticipant = prevDebate.participants[id];
          if (
            participant.responseHistory.length > prevParticipant.responseHistory.length
          ) {
            const newResponse = participant.responseHistory[participant.responseHistory.length - 1];
            callbacks.onResponseComplete?.(id, newResponse);
          }
        });

        // Judge assessment detection
        if (debate.judge.assessments.length > prevDebate.judge.assessments.length) {
          const newAssessment = debate.judge.assessments[debate.judge.assessments.length - 1];
          callbacks.onJudgeAssessment?.(newAssessment);
        }

        // Status change detection
        if (debate.status !== prevDebate.status) {
          callbacks.onStatusChange?.(debate.status);
        }

        // Error detection
        Object.entries(debate.participants).forEach(([id, participant]) => {
          const prevParticipant = prevDebate.participants[id];
          if (participant.errors.length > prevParticipant.errors.length) {
            const newError = participant.errors[participant.errors.length - 1];
            callbacks.onError?.(newError);
          }
        });
      },
      { equalityFn: shallow }
    );

    return unsubscribe;
  }, [debateId, callbacks]);
};

// Usage example
const MyDebateComponent = ({ debateId }) => {
  useDebateSubscription(debateId, {
    onRoundStart: (round) => {
      console.log(`Round ${round} started`);
      // Trigger animations, sound effects, etc.
    },
    onResponseComplete: (participantId, response) => {
      // Scroll to response, highlight, etc.
    },
    onJudgeAssessment: (assessment) => {
      if (assessment.flags.diminishingReturns) {
        showNotification('Judge detected diminishing returns');
      }
    },
    onStatusChange: (status) => {
      if (status === 'completed') {
        showConfetti();
      }
    },
    onError: (error) => {
      showErrorNotification(error.message);
    },
  });

  // Component render logic
};
```

### 8.2 Broadcast Channel for Multi-Tab Sync

```typescript
// services/broadcastSync.ts
class BroadcastSync {
  private channel: BroadcastChannel | null = null;
  private enabled = typeof BroadcastChannel !== 'undefined';

  initialize() {
    if (!this.enabled) return;

    this.channel = new BroadcastChannel('quorum-sync');

    this.channel.onmessage = (event) => {
      const { type, payload } = event.data;

      switch (type) {
        case 'debate-updated':
          // Sync debate state across tabs
          useStore.getState().syncDebate(payload.debateId, payload.updates);
          break;

        case 'provider-added':
          // Sync API key across tabs
          useStore.getState().addProvider(payload.provider);
          break;

        case 'settings-changed':
          // Sync user preferences
          useStore.getState().updateSettings(payload.settings);
          break;
      }
    };
  }

  broadcast(type: string, payload: any) {
    if (!this.channel) return;
    this.channel.postMessage({ type, payload });
  }

  close() {
    this.channel?.close();
  }
}

export const broadcastSync = new BroadcastSync();

// Initialize on app start
broadcastSync.initialize();

// Broadcast state changes
useStore.subscribe(
  (state) => state.debates,
  (debates, prevDebates) => {
    Object.keys(debates).forEach(debateId => {
      if (debates[debateId] !== prevDebates[debateId]) {
        broadcastSync.broadcast('debate-updated', {
          debateId,
          updates: debates[debateId],
        });
      }
    });
  }
);
```

---

## 9. Testing Strategy

### 9.1 Unit Tests for Store

```typescript
// stores/__tests__/debateStore.test.ts
import { renderHook, act } from '@testing-library/react';
import { useStore } from '../debateStore';

describe('debateStore', () => {
  beforeEach(() => {
    useStore.setState({
      debates: {},
      activeDebateId: null,
      ui: { /* reset state */ },
    });
  });

  test('should create a new debate', () => {
    const { result } = renderHook(() => useStore());

    act(() => {
      result.current.createDebate({
        topic: 'Test topic',
        format: 'free-form',
        mode: 'sequential',
        participants: [],
        judgeConfig: { /* ... */ },
      });
    });

    const debates = result.current.debates;
    expect(Object.keys(debates).length).toBe(1);

    const debate = Object.values(debates)[0];
    expect(debate.config.topic).toBe('Test topic');
    expect(debate.status).toBe('configuring');
  });

  test('should add streaming chunks incrementally', () => {
    const { result } = renderHook(() => useStore());
    const debateId = 'test-debate-id';
    const participantId = 'participant-1';

    // Setup
    act(() => {
      result.current.debates[debateId] = {
        participants: {
          [participantId]: {
            currentResponse: {
              content: '',
              startedAt: Date.now(),
              lastChunkAt: Date.now(),
              chunkCount: 0,
            },
          },
        },
      };
    });

    // Add chunks
    act(() => {
      result.current.addStreamChunk(debateId, participantId, 'Hello ');
      result.current.addStreamChunk(debateId, participantId, 'world');
    });

    const participant = result.current.debates[debateId].participants[participantId];
    expect(participant.currentResponse.content).toBe('Hello world');
    expect(participant.currentResponse.chunkCount).toBe(2);
  });

  test('should calculate total cost across participants', () => {
    const { result } = renderHook(() => useStore());
    const debateId = 'test-debate-id';

    act(() => {
      result.current.debates[debateId] = {
        participants: {
          'p1': { tokenUsage: { estimatedCost: 0.05 } },
          'p2': { tokenUsage: { estimatedCost: 0.03 } },
        },
      };
    });

    const totalCost = useTotalCost(debateId);
    expect(totalCost).toBe(0.08);
  });
});
```

### 9.2 State Machine Tests

```typescript
// machines/__tests__/debateMachine.test.ts
import { interpret } from 'xstate';
import { debateMachine } from '../debateMachine';

describe('debateMachine', () => {
  test('should transition from configuring to ready after validation', (done) => {
    const service = interpret(debateMachine)
      .onTransition((state) => {
        if (state.matches('ready')) {
          done();
        }
      })
      .start();

    service.send({
      type: 'SET_CONFIG',
      config: { /* valid config */ }
    });
    service.send('VALIDATE');
  });

  test('should not start debate without valid config', () => {
    const service = interpret(debateMachine).start();

    service.send({
      type: 'SET_CONFIG',
      config: { topic: '' } // invalid
    });
    service.send('START');

    expect(service.state.matches('ready')).toBe(false);
  });

  test('should end debate when round limit reached', (done) => {
    const service = interpret(
      debateMachine.withContext({
        config: { format: 'round-limited', roundLimit: 3 },
        currentRound: 3,
      })
    )
      .onTransition((state) => {
        if (state.matches('completing')) {
          done();
        }
      })
      .start();

    // ... trigger round completion
  });
});
```

### 9.3 Integration Tests

```typescript
// __tests__/integration/debate-flow.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DebateApp } from '../DebateApp';

describe('Debate Flow Integration', () => {
  test('complete debate lifecycle', async () => {
    const user = userEvent.setup();
    render(<DebateApp />);

    // Configure debate
    await user.type(screen.getByLabelText('Topic'), 'Should we colonize Mars?');
    await user.selectOptions(screen.getByLabelText('Format'), 'structured-rounds');

    // Add participants
    await user.click(screen.getByText('Add Participant'));
    await user.selectOptions(screen.getByLabelText('Model'), 'claude-3-5-sonnet');

    // Start debate
    await user.click(screen.getByText('Start Debate'));

    // Verify streaming
    await waitFor(() => {
      expect(screen.getByText(/streaming/i)).toBeInTheDocument();
    }, { timeout: 5000 });

    // Verify completion
    await waitFor(() => {
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    }, { timeout: 30000 });

    // Verify final verdict
    expect(screen.getByText(/final verdict/i)).toBeInTheDocument();
  });
});
```

---

## 10. Performance Optimization

### 10.1 Memoization Strategy

```typescript
// Use React.memo for expensive components
export const ParticipantCard = React.memo<{ debateId: string; participantId: string }>(
  ({ debateId, participantId }) => {
    const participant = useStore(state =>
      state.debates[debateId]?.participants[participantId]
    );

    // Component logic
  },
  (prev, next) =>
    prev.debateId === next.debateId &&
    prev.participantId === next.participantId
);

// Use useMemo for expensive computations
const sortedResponses = useMemo(() => {
  return responses.sort((a, b) => a.timestamp - b.timestamp);
}, [responses]);

// Use useCallback for event handlers
const handleStreamChunk = useCallback((chunk: string) => {
  addStreamChunk(debateId, participantId, chunk);
}, [debateId, participantId, addStreamChunk]);
```

### 10.2 Virtual Scrolling for Long Debates

```typescript
// components/DebateTimeline.tsx
import { useVirtualizer } from '@tanstack/react-virtual';

export const DebateTimeline: React.FC<{ debateId: string }> = ({ debateId }) => {
  const responses = useAllResponses(debateId);
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: responses.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 200, // Estimated height of response card
    overscan: 5,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <ResponseCard response={responses[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 10.3 Debounced State Updates

```typescript
// hooks/useDebouncedUpdate.ts
import { useCallback, useRef } from 'react';
import { debounce } from 'lodash-es';

export const useDebouncedUpdate = <T,>(
  updateFn: (value: T) => void,
  delay: number = 300
) => {
  const debouncedFn = useRef(
    debounce((value: T) => updateFn(value), delay)
  ).current;

  return useCallback(
    (value: T) => debouncedFn(value),
    [debouncedFn]
  );
};

// Usage: debounce streaming updates to reduce re-renders
const debouncedAddChunk = useDebouncedUpdate(
  (chunk: string) => addStreamChunk(debateId, participantId, chunk),
  100
);
```

---

## 11. Code Examples - Key Operations

### 11.1 Starting a Debate

```typescript
// services/debateOrchestrator.ts
import { useMachine } from '@xstate/react';
import { debateMachine } from '../machines/debateMachine';
import { useStore } from '../stores/debateStore';

export const useDebateOrchestrator = (debateId: string) => {
  const [state, send] = useMachine(debateMachine, {
    services: {
      validateConfiguration: async (context) => {
        // Validate all API keys
        const providers = context.config.participants.map(p => p.providerId);
        const validations = await Promise.all(
          providers.map(id => useStore.getState().validateProvider(id))
        );

        if (validations.some(v => !v)) {
          throw new Error('Invalid API keys');
        }

        return true;
      },

      initializeDebate: async (context) => {
        const { config } = context;

        // Auto-assign personas if needed
        const participantsWithPersonas = await Promise.all(
          config.participants.map(async (p) => {
            if (p.personaMode === 'auto-assign') {
              const position = await assignPersona(config.topic, p);
              return { ...p, assignedPosition: position };
            }
            return p;
          })
        );

        // Initialize participant state
        const participants = {};
        participantsWithPersonas.forEach(pConfig => {
          participants[pConfig.id] = {
            id: pConfig.id,
            config: pConfig,
            status: 'idle',
            responseHistory: [],
            tokenUsage: {
              promptTokens: 0,
              completionTokens: 0,
              totalTokens: 0,
              estimatedCost: 0,
            },
            errors: [],
            retryCount: 0,
          };
        });

        // Initialize judge
        const judge = {
          config: config.judgeConfig,
          status: 'idle',
          assessments: [],
          tokenUsage: {
            promptTokens: 0,
            completionTokens: 0,
            totalTokens: 0,
            estimatedCost: 0,
          },
          errors: [],
        };

        // Update store
        useStore.getState().updateDebate(debateId, {
          participants,
          judge,
          status: 'running',
          startedAt: Date.now(),
        });

        return { participants, judge };
      },

      streamResponses: async (context) => {
        const { config, participants, currentRound } = context;
        const mode = config.mode;

        if (mode === 'simultaneous') {
          // Parallel streaming
          const promises = Object.entries(participants).map(([id, p]) => {
            const prompt = buildDebaterPrompt(p, context);
            const streamHook = useStreamResponse(debateId, id);
            return streamHook.mutateAsync({ prompt, context: [] });
          });

          await Promise.allSettled(promises);
        } else {
          // Sequential streaming
          for (const [id, p] of Object.entries(participants)) {
            const prompt = buildDebaterPrompt(p, context);
            const streamHook = useStreamResponse(debateId, id);

            try {
              await streamHook.mutateAsync({ prompt, context: [] });
            } catch (error) {
              // Handle individual failures
              if (!error.retryable) {
                throw error; // Stop debate
              }
              // Continue to next participant
            }
          }
        }
      },

      getJudgeAssessment: async (context) => {
        const { judge, participants, currentRound } = context;

        // Build judge prompt with all responses from current round
        const roundResponses = Object.values(participants)
          .flatMap(p => p.responseHistory)
          .filter(r => r.roundNumber === currentRound);

        const judgePrompt = buildJudgePrompt(
          judge.config,
          roundResponses,
          context.config.format
        );

        // Stream judge assessment
        const assessment = await getJudgeResponse(judgePrompt);

        return assessment;
      },

      getFinalVerdict: async (context) => {
        const { judge, participants } = context;

        const verdictPrompt = buildFinalVerdictPrompt(
          judge.config,
          participants,
          judge.assessments
        );

        const verdict = await getJudgeResponse(verdictPrompt);

        return verdict;
      },
    },

    guards,
    actions,
  });

  const startDebate = useCallback(() => {
    send('START');
  }, [send]);

  const pauseDebate = useCallback(() => {
    send('PAUSE');
  }, [send]);

  const resumeDebate = useCallback(() => {
    send('RESUME');
  }, [send]);

  const forceStop = useCallback(() => {
    send('FORCE_STOP');
  }, [send]);

  return {
    state: state.value,
    context: state.context,
    startDebate,
    pauseDebate,
    resumeDebate,
    forceStop,
  };
};
```

### 11.2 Handling Context Window Overflow

```typescript
// services/contextManager.ts
interface ContextWindow {
  maxTokens: number;
  currentTokens: number;
  messages: ContextMessage[];
}

class ContextManager {
  private tokenCounter = new TokenCounter();

  buildContext(
    participant: Participant,
    debate: DebateState
  ): ContextWindow {
    const modelInfo = getModelInfo(participant.config.modelId);
    const maxTokens = modelInfo.contextWindow;

    // System prompt
    const systemPrompt = buildSystemPrompt(participant);
    let currentTokens = this.tokenCounter.count(systemPrompt);

    // Conversation history (newest first)
    const messages: ContextMessage[] = [
      { role: 'system', content: systemPrompt },
    ];

    // Add responses in reverse chronological order
    const allResponses = this.getAllResponsesChronological(debate);

    for (const response of allResponses.reverse()) {
      const tokenCount = this.tokenCounter.count(response.content);

      if (currentTokens + tokenCount > maxTokens * 0.8) {
        // Approaching limit: summarize or truncate
        break;
      }

      messages.unshift({
        role: response.participantId === participant.id ? 'assistant' : 'user',
        content: response.content,
        participantId: response.participantId,
      });

      currentTokens += tokenCount;
    }

    return { maxTokens, currentTokens, messages };
  }

  private getAllResponsesChronological(debate: DebateState): Response[] {
    const responses: Response[] = [];

    Object.values(debate.participants).forEach(p => {
      responses.push(...p.responseHistory);
    });

    return responses.sort((a, b) => a.timestamp - b.timestamp);
  }

  async summarizeIfNeeded(
    context: ContextWindow,
    threshold: number = 0.8
  ): Promise<ContextWindow> {
    const ratio = context.currentTokens / context.maxTokens;

    if (ratio < threshold) {
      return context; // No summarization needed
    }

    // Summarize older messages
    const recentMessages = context.messages.slice(-10); // Keep last 10
    const oldMessages = context.messages.slice(0, -10);

    const summary = await this.summarizeMessages(oldMessages);

    return {
      ...context,
      messages: [
        { role: 'system', content: summary },
        ...recentMessages,
      ],
      currentTokens: this.tokenCounter.count(
        summary + recentMessages.map(m => m.content).join('')
      ),
    };
  }

  private async summarizeMessages(messages: ContextMessage[]): Promise<string> {
    // Use a separate LLM call to summarize
    const summaryPrompt = `Summarize the following debate discussion concisely:\n\n${
      messages.map(m => `${m.participantId}: ${m.content}`).join('\n\n')
    }`;

    // Call summarization endpoint
    const summary = await callSummarizationAPI(summaryPrompt);
    return `[Previous discussion summary: ${summary}]`;
  }
}

export const contextManager = new ContextManager();
```

### 11.3 Export Functionality

```typescript
// services/exportService.ts
import { debateHistory } from './debateHistory';

class ExportService {
  async exportDebate(
    debateId: string,
    format: 'markdown' | 'json' | 'html' | 'pdf'
  ): Promise<void> {
    const content = await debateHistory.export(debateId, format);

    const blob = new Blob([content], {
      type: this.getMimeType(format),
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `debate-${debateId}.${format}`;
    link.click();

    URL.revokeObjectURL(url);
  }

  private getMimeType(format: string): string {
    const mimeTypes = {
      markdown: 'text/markdown',
      json: 'application/json',
      html: 'text/html',
      pdf: 'application/pdf',
    };
    return mimeTypes[format] || 'text/plain';
  }

  async shareDebate(debateId: string): Promise<string> {
    // Generate shareable link (future feature)
    const debate = await debateHistory.getDebate(debateId);
    const encoded = btoa(JSON.stringify(debate));

    const shareUrl = `${window.location.origin}/share/${encoded}`;

    // Copy to clipboard
    await navigator.clipboard.writeText(shareUrl);

    return shareUrl;
  }
}

export const exportService = new ExportService();
```

---

## 12. Recommendations Summary

### Architecture Decision Records

**ADR-001: State Management Library**
- **Decision**: Zustand + XState hybrid
- **Rationale**: Balance simplicity (Zustand) with state machine rigor (XState)
- **Trade-offs**: Two libraries vs one, but each optimized for its domain

**ADR-002: Streaming Management**
- **Decision**: React Query for async/streaming state
- **Rationale**: Built-in retry, caching, and request management
- **Trade-offs**: Additional dependency, but worth it for robust streaming

**ADR-003: Persistence Layer**
- **Decision**: IndexedDB with LocalStorage fallback
- **Rationale**: Better performance for large debates, structured queries
- **Trade-offs**: More complex than localStorage, but necessary for scale

**ADR-004: API Key Storage**
- **Decision**: Encrypted storage with AES-256
- **Rationale**: Balance security with client-side convenience
- **Trade-offs**: Not perfectly secure, but acceptable for MVP with disclaimers

### Implementation Roadmap

**Phase 1: Foundation** (Week 1-2)
1. Set up Zustand store structure
2. Implement basic state slices (debate, participants, UI)
3. Add persistence middleware
4. Create type definitions

**Phase 2: State Machine** (Week 2-3)
1. Implement XState debate lifecycle machine
2. Add guards and actions
3. Integrate with Zustand store
4. Add state visualizer for debugging

**Phase 3: Streaming** (Week 3-4)
1. Set up React Query
2. Implement streaming hooks
3. Add rate limiting and queue management
4. Build error recovery patterns

**Phase 4: Persistence** (Week 4-5)
1. Implement IndexedDB adapter
2. Add encrypted key storage
3. Build debate history service
4. Add export functionality

**Phase 5: Optimization** (Week 5-6)
1. Add performance monitoring
2. Implement virtual scrolling
3. Optimize selectors and memoization
4. Add context window management

**Phase 6: Testing** (Week 6-7)
1. Unit tests for stores
2. State machine tests
3. Integration tests
4. E2E tests for critical paths

### Maintenance Considerations

1. **State Schema Versioning**: Plan for state migration as schema evolves
2. **DevTools Integration**: Leverage Zustand/XState devtools for debugging
3. **Documentation**: Generate state machine visualizations for contributors
4. **Monitoring**: Add telemetry for state transitions and errors (opt-in)
5. **Performance Budgets**: Set limits for state size and update frequency

---

## Conclusion

This state management architecture provides a robust foundation for Quorum's complex real-time debate system. The hybrid approach leverages the strengths of multiple libraries while maintaining simplicity for contributors:

- **Zustand** for straightforward global state
- **XState** for complex lifecycle management
- **React Query** for streaming and API state
- **IndexedDB** for scalable persistence

The design emphasizes:
- Type safety throughout
- Predictable state transitions
- Resilient error handling
- Optimized performance
- Developer-friendly patterns

This architecture scales from MVP to advanced features while remaining maintainable for an open-source community.
