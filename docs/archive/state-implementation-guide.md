# Quorum State Management Implementation Guide

## Quick Start for Contributors

This guide provides practical, copy-paste ready code examples for implementing Quorum's state management architecture.

## Table of Contents

1. [Project Setup](#1-project-setup)
2. [Zustand Store Implementation](#2-zustand-store-implementation)
3. [XState Machine Setup](#3-xstate-machine-setup)
4. [React Query Integration](#4-react-query-integration)
5. [Custom Hooks Library](#5-custom-hooks-library)
6. [Component Integration Examples](#6-component-integration-examples)
7. [Testing Examples](#7-testing-examples)
8. [Common Patterns](#8-common-patterns)

---

## 1. Project Setup

### Install Dependencies

```bash
npm install zustand immer
npm install xstate @xstate/react
npm install @tanstack/react-query
npm install p-queue crypto-js
npm install @tanstack/react-virtual

# Dev dependencies
npm install -D @types/crypto-js
npm install -D @xstate/inspect
```

### Project Structure

```
src/
├── stores/
│   ├── debateStore.ts          # Main Zustand store
│   ├── slices/
│   │   ├── debateSlice.ts
│   │   ├── participantSlice.ts
│   │   ├── judgeSlice.ts
│   │   ├── providerSlice.ts
│   │   └── uiSlice.ts
│   └── selectors.ts            # Memoized selectors
├── machines/
│   ├── debateMachine.ts        # XState state machine
│   ├── guards.ts
│   ├── actions.ts
│   └── services.ts
├── hooks/
│   ├── useDebate.ts
│   ├── useStream.ts
│   ├── useJudge.ts
│   └── useProviders.ts
├── services/
│   ├── api/
│   │   ├── anthropic.ts
│   │   ├── openai.ts
│   │   ├── google.ts
│   │   └── mistral.ts
│   ├── storage.ts
│   ├── keyStorage.ts
│   ├── debateHistory.ts
│   ├── contextManager.ts
│   ├── rateLimitQueue.ts
│   └── circuitBreaker.ts
├── types/
│   ├── debate.ts
│   ├── participant.ts
│   ├── judge.ts
│   └── errors.ts
└── utils/
    ├── tokenCounter.ts
    ├── encryption.ts
    └── validators.ts
```

---

## 2. Zustand Store Implementation

### Basic Store Setup

```typescript
// stores/debateStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { createDebateSlice } from './slices/debateSlice';
import { createParticipantSlice } from './slices/participantSlice';
import { createJudgeSlice } from './slices/judgeSlice';
import { createProviderSlice } from './slices/providerSlice';
import { createUISlice } from './slices/uiSlice';

export const useStore = create(
  devtools(
    persist(
      immer((set, get, api) => ({
        // Combine all slices
        ...createDebateSlice(set, get, api),
        ...createParticipantSlice(set, get, api),
        ...createJudgeSlice(set, get, api),
        ...createProviderSlice(set, get, api),
        ...createUISlice(set, get, api),
      })),
      {
        name: 'quorum-storage',
        // Only persist specific slices
        partialize: (state) => ({
          debates: state.debates,
          providers: state.providers,
          ui: {
            activeView: state.ui.activeView,
            filters: state.ui.filters,
          },
        }),
      }
    ),
    {
      name: 'Quorum Store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Export type for TypeScript
export type StoreState = ReturnType<typeof useStore.getState>;
```

### Example Slice: Debate Slice

```typescript
// stores/slices/debateSlice.ts
import type { StateCreator } from 'zustand';
import type { DebateConfig, DebateState } from '../../types/debate';
import { generateId } from '../../utils/generators';

export interface DebateSlice {
  debates: Record<string, DebateState>;
  activeDebateId: string | null;

  createDebate: (config: DebateConfig) => string;
  updateDebateConfig: (debateId: string, updates: Partial<DebateConfig>) => void;
  setDebateStatus: (debateId: string, status: DebateStatus) => void;
  incrementRound: (debateId: string) => void;
  setActiveDebate: (debateId: string) => void;
  deleteDebate: (debateId: string) => void;
  getActiveDebate: () => DebateState | null;
}

export const createDebateSlice: StateCreator<
  DebateSlice,
  [['zustand/immer', never]],
  [],
  DebateSlice
> = (set, get) => ({
  debates: {},
  activeDebateId: null,

  createDebate: (config) => {
    const id = generateId();

    set((state) => {
      state.debates[id] = {
        id,
        status: 'configuring',
        config,
        currentRound: 0,
        participants: {},
        judge: {
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
        },
        timeline: [],
      };
      state.activeDebateId = id;
    });

    return id;
  },

  updateDebateConfig: (debateId, updates) =>
    set((state) => {
      if (state.debates[debateId]) {
        state.debates[debateId].config = {
          ...state.debates[debateId].config,
          ...updates,
        };
      }
    }),

  setDebateStatus: (debateId, status) =>
    set((state) => {
      if (state.debates[debateId]) {
        state.debates[debateId].status = status;

        // Add timeline event
        state.debates[debateId].timeline.push({
          id: generateId(),
          timestamp: Date.now(),
          type: 'status-change',
          data: { status },
        });
      }
    }),

  incrementRound: (debateId) =>
    set((state) => {
      if (state.debates[debateId]) {
        state.debates[debateId].currentRound += 1;

        state.debates[debateId].timeline.push({
          id: generateId(),
          timestamp: Date.now(),
          type: 'round-start',
          data: { roundNumber: state.debates[debateId].currentRound },
        });
      }
    }),

  setActiveDebate: (debateId) =>
    set((state) => {
      state.activeDebateId = debateId;
    }),

  deleteDebate: (debateId) =>
    set((state) => {
      delete state.debates[debateId];
      if (state.activeDebateId === debateId) {
        state.activeDebateId = null;
      }
    }),

  getActiveDebate: () => {
    const { debates, activeDebateId } = get();
    return activeDebateId ? debates[activeDebateId] : null;
  },
});
```

### Example Slice: Participant Slice

```typescript
// stores/slices/participantSlice.ts
import type { StateCreator } from 'zustand';
import type { Participant, Response, StreamingResponse } from '../../types/participant';

export interface ParticipantSlice {
  addParticipant: (debateId: string, participant: Participant) => void;
  updateParticipant: (debateId: string, participantId: string, updates: Partial<Participant>) => void;
  startStreaming: (debateId: string, participantId: string) => void;
  addStreamChunk: (debateId: string, participantId: string, chunk: string) => void;
  finalizeResponse: (debateId: string, participantId: string, tokenUsage: TokenUsage) => void;
  addError: (debateId: string, participantId: string, error: ParticipantError) => void;
}

export const createParticipantSlice: StateCreator<
  ParticipantSlice,
  [['zustand/immer', never]],
  [],
  ParticipantSlice
> = (set, get) => ({
  addParticipant: (debateId, participant) =>
    set((state) => {
      if (state.debates[debateId]) {
        state.debates[debateId].participants[participant.id] = participant;
      }
    }),

  updateParticipant: (debateId, participantId, updates) =>
    set((state) => {
      const participant = state.debates[debateId]?.participants[participantId];
      if (participant) {
        Object.assign(participant, updates);
      }
    }),

  startStreaming: (debateId, participantId) =>
    set((state) => {
      const participant = state.debates[debateId]?.participants[participantId];
      if (participant) {
        participant.status = 'streaming';
        participant.currentResponse = {
          content: '',
          startedAt: Date.now(),
          lastChunkAt: Date.now(),
          chunkCount: 0,
        };
      }
    }),

  addStreamChunk: (debateId, participantId, chunk) =>
    set((state) => {
      const participant = state.debates[debateId]?.participants[participantId];
      if (participant?.currentResponse) {
        participant.currentResponse.content += chunk;
        participant.currentResponse.lastChunkAt = Date.now();
        participant.currentResponse.chunkCount += 1;
      }
    }),

  finalizeResponse: (debateId, participantId, tokenUsage) =>
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

      // Update token usage
      participant.tokenUsage.promptTokens += tokenUsage.promptTokens;
      participant.tokenUsage.completionTokens += tokenUsage.completionTokens;
      participant.tokenUsage.totalTokens += tokenUsage.totalTokens;
      participant.tokenUsage.estimatedCost += tokenUsage.estimatedCost;

      // Add timeline event
      state.debates[debateId].timeline.push({
        id: generateId(),
        timestamp: Date.now(),
        type: 'response-complete',
        data: { participantId, response },
      });
    }),

  addError: (debateId, participantId, error) =>
    set((state) => {
      const participant = state.debates[debateId]?.participants[participantId];
      if (participant) {
        participant.errors.push(error);
        participant.status = 'error';
        participant.retryCount += 1;

        state.debates[debateId].timeline.push({
          id: generateId(),
          timestamp: Date.now(),
          type: 'error',
          data: { participantId, error },
        });
      }
    }),
});
```

### Optimized Selectors

```typescript
// stores/selectors.ts
import { useStore } from './debateStore';
import { shallow } from 'zustand/shallow';
import { useMemo } from 'react';

// Active debate selector
export const useActiveDebate = () =>
  useStore((state) => {
    const id = state.activeDebateId;
    return id ? state.debates[id] : null;
  });

// Debate participants (shallow compare for object stability)
export const useDebateParticipants = (debateId: string) =>
  useStore(
    (state) => state.debates[debateId]?.participants || {},
    shallow
  );

// Single participant
export const useParticipant = (debateId: string, participantId: string) =>
  useStore((state) => state.debates[debateId]?.participants[participantId]);

// Participant status only (granular selector)
export const useParticipantStatus = (debateId: string, participantId: string) =>
  useStore((state) => state.debates[debateId]?.participants[participantId]?.status);

// Streaming content only
export const useStreamingContent = (debateId: string, participantId: string) =>
  useStore(
    (state) =>
      state.debates[debateId]?.participants[participantId]?.currentResponse?.content || ''
  );

// Judge assessments
export const useJudgeAssessments = (debateId: string) =>
  useStore(
    (state) => state.debates[debateId]?.judge.assessments || [],
    shallow
  );

// Computed total cost
export const useTotalCost = (debateId: string) =>
  useStore((state) => {
    const participants = state.debates[debateId]?.participants;
    if (!participants) return 0;

    return Object.values(participants).reduce(
      (sum, p) => sum + p.tokenUsage.estimatedCost,
      0
    );
  });

// Computed total tokens
export const useTotalTokens = (debateId: string) =>
  useStore((state) => {
    const participants = state.debates[debateId]?.participants;
    if (!participants) return 0;

    return Object.values(participants).reduce(
      (sum, p) => sum + p.tokenUsage.totalTokens,
      0
    );
  });

// All responses in chronological order
export const useAllResponses = (debateId: string) =>
  useStore((state) => {
    const participants = state.debates[debateId]?.participants;
    if (!participants) return [];

    const responses: Response[] = [];
    Object.values(participants).forEach((p) => {
      responses.push(...p.responseHistory);
    });

    return responses.sort((a, b) => a.timestamp - b.timestamp);
  }, shallow);

// Responses for specific round
export const useRoundResponses = (debateId: string, roundNumber: number) =>
  useStore((state) => {
    const participants = state.debates[debateId]?.participants;
    if (!participants) return [];

    const responses: Response[] = [];
    Object.values(participants).forEach((p) => {
      const roundResponses = p.responseHistory.filter(
        (r) => r.roundNumber === roundNumber
      );
      responses.push(...roundResponses);
    });

    return responses;
  }, shallow);

// Active providers
export const useActiveProviders = () =>
  useStore(
    (state) => state.activeProviders.map((id) => state.providers[id]).filter(Boolean),
    shallow
  );

// Provider by ID
export const useProvider = (providerId: string) =>
  useStore((state) => state.providers[providerId]);

// Notifications
export const useNotifications = () =>
  useStore((state) => state.ui.notifications, shallow);
```

---

## 3. XState Machine Setup

### Core State Machine

```typescript
// machines/debateMachine.ts
import { createMachine, assign } from 'xstate';
import type { DebateConfig, DebateState } from '../types/debate';
import { createGuards } from './guards';
import { createActions } from './actions';
import { createServices } from './services';

export interface DebateMachineContext {
  debateId: string;
  config: DebateConfig | null;
  currentRound: number;
  errors: Error[];
}

export type DebateMachineEvent =
  | { type: 'SET_CONFIG'; config: DebateConfig }
  | { type: 'VALIDATE' }
  | { type: 'START' }
  | { type: 'PAUSE' }
  | { type: 'RESUME' }
  | { type: 'FORCE_STOP' }
  | { type: 'RETRY' }
  | { type: 'RESET' }
  | { type: 'RESPONSE_CHUNK'; participantId: string; chunk: string }
  | { type: 'RESPONSE_COMPLETE'; participantId: string; usage: TokenUsage }
  | { type: 'RESPONSE_ERROR'; participantId: string; error: ParticipantError };

export const debateMachine = createMachine(
  {
    id: 'debate',
    initial: 'configuring',
    context: {
      debateId: '',
      config: null,
      currentRound: 0,
      errors: [],
    },
    tsTypes: {} as import('./debateMachine.typegen').Typegen0,
    schema: {
      context: {} as DebateMachineContext,
      events: {} as DebateMachineEvent,
    },
    states: {
      configuring: {
        on: {
          SET_CONFIG: {
            actions: 'setConfig',
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
            actions: 'clearErrors',
          },
          onError: {
            target: 'configuring',
            actions: 'setErrors',
          },
        },
      },
      ready: {
        on: {
          START: {
            target: 'initializing',
            cond: 'hasValidConfig',
          },
          SET_CONFIG: {
            target: 'configuring',
          },
        },
      },
      initializing: {
        invoke: {
          src: 'initializeDebate',
          onDone: {
            target: 'running',
            actions: 'storeInitializedData',
          },
          onError: {
            target: 'error',
            actions: 'setErrors',
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
              onDone: {
                target: 'judging',
              },
            },
            on: {
              RESPONSE_CHUNK: {
                actions: 'handleResponseChunk',
              },
              RESPONSE_COMPLETE: {
                actions: 'handleResponseComplete',
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
                  actions: 'incrementRound',
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
          FORCE_STOP: 'completing',
        },
      },
      completing: {
        invoke: {
          src: 'getFinalVerdict',
          onDone: {
            target: 'completed',
            actions: 'storeFinalVerdict',
          },
          onError: {
            target: 'error',
            actions: 'setErrors',
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
            actions: 'clearErrors',
          },
          RESET: {
            target: 'configuring',
            actions: 'resetContext',
          },
        },
      },
    },
  },
  {
    guards: createGuards(),
    actions: createActions(),
    services: createServices(),
  }
);
```

### Guards

```typescript
// machines/guards.ts
import type { DebateMachineContext, DebateMachineEvent } from './debateMachine';

export const createGuards = () => ({
  hasValidConfig: (context: DebateMachineContext) => {
    const config = context.config;
    if (!config) return false;

    return (
      config.topic?.trim().length > 0 &&
      config.participants?.length >= 2 &&
      config.participants?.length <= 4 &&
      config.judgeConfig != null
    );
  },

  shouldEndDebate: (context: DebateMachineContext, event: any) => {
    const assessment = event.data;
    const config = context.config;

    if (!config) return true;

    // Round-limited format
    if (config.format === 'round-limited') {
      return context.currentRound >= (config.roundLimit || 0);
    }

    // Convergence-seeking format
    if (config.format === 'convergence-seeking') {
      return (
        assessment.flags?.convergenceReached ||
        assessment.flags?.diminishingReturns
      );
    }

    // Free-form and structured: judge decides
    return !assessment.shouldContinue;
  },

  canContinue: (context: DebateMachineContext) => {
    // Check if any non-retryable errors exist
    const hasBlockingErrors = context.errors.some(
      (err: any) => !err.retryable
    );

    return !hasBlockingErrors;
  },
});
```

### Actions

```typescript
// machines/actions.ts
import { assign } from 'xstate';
import { useStore } from '../stores/debateStore';
import type { DebateMachineContext, DebateMachineEvent } from './debateMachine';

export const createActions = () => ({
  setConfig: assign({
    config: (_, event: any) => event.config,
  }),

  clearErrors: assign({
    errors: () => [],
  }),

  setErrors: assign({
    errors: (_, event: any) => [event.data],
  }),

  storeInitializedData: assign({
    currentRound: () => 1,
  }),

  handleResponseChunk: (context: DebateMachineContext, event: any) => {
    useStore.getState().addStreamChunk(
      context.debateId,
      event.participantId,
      event.chunk
    );
  },

  handleResponseComplete: (context: DebateMachineContext, event: any) => {
    useStore.getState().finalizeResponse(
      context.debateId,
      event.participantId,
      event.usage
    );
  },

  handleResponseError: (context: DebateMachineContext, event: any) => {
    useStore.getState().addError(
      context.debateId,
      event.participantId,
      event.error
    );
  },

  storeAssessment: (context: DebateMachineContext, event: any) => {
    useStore.getState().addJudgeAssessment(context.debateId, event.data);
  },

  handleJudgeError: (context: DebateMachineContext, event: any) => {
    useStore.getState().addNotification({
      type: 'error',
      message: `Judge error: ${event.data.message}`,
      dismissible: true,
    });
  },

  incrementRound: assign({
    currentRound: (context) => context.currentRound + 1,
  }),

  storeFinalVerdict: (context: DebateMachineContext, event: any) => {
    useStore.getState().setFinalVerdict(context.debateId, event.data);
  },

  saveDebateToHistory: (context: DebateMachineContext) => {
    const debate = useStore.getState().debates[context.debateId];
    if (debate) {
      debateHistory.saveDebate(debate);
    }
  },

  resetContext: assign({
    config: () => null,
    currentRound: () => 0,
    errors: () => [],
  }),
});
```

### Services

```typescript
// machines/services.ts
import { useStore } from '../stores/debateStore';
import type { DebateMachineContext } from './debateMachine';

export const createServices = () => ({
  validateConfiguration: async (context: DebateMachineContext) => {
    const config = context.config;
    if (!config) throw new Error('No configuration provided');

    // Validate API keys
    const providers = config.participants.map((p) => p.providerId);
    const uniqueProviders = [...new Set(providers)];

    const validations = await Promise.all(
      uniqueProviders.map((id) => useStore.getState().validateProvider(id))
    );

    if (validations.some((v) => !v)) {
      throw new Error('One or more API keys are invalid');
    }

    return true;
  },

  initializeDebate: async (context: DebateMachineContext) => {
    const config = context.config;
    if (!config) throw new Error('No configuration');

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

    // Initialize participants in store
    participantsWithPersonas.forEach((pConfig) => {
      useStore.getState().addParticipant(context.debateId, {
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
      });
    });

    useStore.getState().setDebateStatus(context.debateId, 'running');

    return { success: true };
  },

  streamResponses: async (context: DebateMachineContext) => {
    const debate = useStore.getState().debates[context.debateId];
    const mode = debate.config.mode;

    if (mode === 'simultaneous') {
      // Parallel streaming
      const promises = Object.keys(debate.participants).map((participantId) =>
        streamParticipantResponse(context.debateId, participantId)
      );

      await Promise.allSettled(promises);
    } else {
      // Sequential streaming
      for (const participantId of Object.keys(debate.participants)) {
        try {
          await streamParticipantResponse(context.debateId, participantId);
        } catch (error: any) {
          if (!error.retryable) {
            throw error;
          }
          // Continue to next participant
        }
      }
    }
  },

  getJudgeAssessment: async (context: DebateMachineContext) => {
    const debate = useStore.getState().debates[context.debateId];

    // Get all responses from current round
    const roundResponses = Object.values(debate.participants)
      .flatMap((p) => p.responseHistory)
      .filter((r) => r.roundNumber === context.currentRound);

    const judgePrompt = buildJudgePrompt(
      debate.judge.config,
      roundResponses,
      debate.config.format
    );

    const assessment = await getJudgeResponse(judgePrompt);
    return assessment;
  },

  getFinalVerdict: async (context: DebateMachineContext) => {
    const debate = useStore.getState().debates[context.debateId];

    const verdictPrompt = buildFinalVerdictPrompt(
      debate.judge.config,
      debate.participants,
      debate.judge.assessments
    );

    const verdict = await getJudgeResponse(verdictPrompt);
    return verdict;
  },
});
```

---

## 4. React Query Integration

### Query Client Setup

```typescript
// main.tsx or App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 2,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <YourApp />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Streaming Hook

```typescript
// hooks/useStreamResponse.ts
import { useMutation } from '@tanstack/react-query';
import { useStore } from '../stores/debateStore';
import { providerQueue } from '../services/rateLimitQueue';
import { streamAPI } from '../services/api';

export const useStreamResponse = (debateId: string, participantId: string) => {
  const startStreaming = useStore((state) => state.startStreaming);
  const addStreamChunk = useStore((state) => state.addStreamChunk);
  const finalizeResponse = useStore((state) => state.finalizeResponse);
  const addError = useStore((state) => state.addError);

  return useMutation({
    mutationKey: ['stream', debateId, participantId],

    mutationFn: async ({
      prompt,
      context,
    }: {
      prompt: string;
      context: string[];
    }) => {
      const participant = useStore.getState().debates[debateId].participants[
        participantId
      ];
      const provider = useStore.getState().providers[participant.config.providerId];

      // Start streaming state
      startStreaming(debateId, participantId);

      // Enqueue to respect rate limits
      return providerQueue.enqueue(provider.id, async () => {
        const stream = await streamAPI(
          provider,
          participant.config.modelId,
          prompt,
          context
        );

        let fullContent = '';
        let tokenUsage = {
          promptTokens: 0,
          completionTokens: 0,
          totalTokens: 0,
          estimatedCost: 0,
        };

        for await (const chunk of stream) {
          if (chunk.type === 'content') {
            fullContent += chunk.text;
            addStreamChunk(debateId, participantId, chunk.text);
          } else if (chunk.type === 'usage') {
            tokenUsage = chunk.usage;
          }
        }

        return { content: fullContent, tokenUsage };
      });
    },

    onSuccess: (data) => {
      finalizeResponse(debateId, participantId, data.tokenUsage);
    },

    onError: (error: any) => {
      addError(debateId, participantId, {
        timestamp: Date.now(),
        type: error.type || 'network',
        message: error.message,
        retryable: error.retryable !== false,
      });
    },

    retry: (failureCount, error: any) => {
      // Don't retry non-retryable errors
      if (error.retryable === false) return false;

      // Max 3 retries
      return failureCount < 3;
    },

    retryDelay: (attemptIndex) => {
      // Exponential backoff: 1s, 2s, 4s
      return Math.min(1000 * 2 ** attemptIndex, 8000);
    },
  });
};
```

---

## 5. Custom Hooks Library

### useDebateOrchestrator

```typescript
// hooks/useDebateOrchestrator.ts
import { useMachine } from '@xstate/react';
import { debateMachine } from '../machines/debateMachine';
import { useStore } from '../stores/debateStore';

export const useDebateOrchestrator = (debateId: string) => {
  const [state, send] = useMachine(debateMachine, {
    context: {
      debateId,
      config: useStore.getState().debates[debateId]?.config || null,
      currentRound: 0,
      errors: [],
    },
  });

  const startDebate = () => send('START');
  const pauseDebate = () => send('PAUSE');
  const resumeDebate = () => send('RESUME');
  const stopDebate = () => send('FORCE_STOP');
  const retryDebate = () => send('RETRY');

  return {
    state: state.value,
    context: state.context,
    isConfiguring: state.matches('configuring'),
    isValidating: state.matches('validating'),
    isReady: state.matches('ready'),
    isRunning: state.matches('running'),
    isPaused: state.matches('paused'),
    isCompleted: state.matches('completed'),
    isError: state.matches('error'),
    startDebate,
    pauseDebate,
    resumeDebate,
    stopDebate,
    retryDebate,
  };
};
```

### useSimultaneousRound

```typescript
// hooks/useSimultaneousRound.ts
import { useCallback } from 'react';
import { useStore } from '../stores/debateStore';
import { useStreamResponse } from './useStreamResponse';

export const useSimultaneousRound = (debateId: string) => {
  const debate = useStore((state) => state.debates[debateId]);
  const addNotification = useStore((state) => state.addNotification);

  const executeRound = useCallback(async () => {
    if (!debate) return;

    const participantIds = Object.keys(debate.participants);
    const context = buildContextHistory(debate);

    // Create stream mutations for each participant
    const streamPromises = participantIds.map(async (participantId) => {
      const participant = debate.participants[participantId];
      const prompt = buildDebaterPrompt(participant, context);

      const streamMutation = useStreamResponse(debateId, participantId);
      return streamMutation.mutateAsync({ prompt, context });
    });

    // Execute all in parallel
    const results = await Promise.allSettled(streamPromises);

    // Handle failures
    const failures = results.filter((r) => r.status === 'rejected');
    if (failures.length > 0) {
      addNotification({
        type: 'warning',
        message: `${failures.length} participant(s) failed to respond`,
        dismissible: true,
      });
    }

    // Trigger judge if at least one succeeded
    const successCount = results.filter((r) => r.status === 'fulfilled').length;
    if (successCount > 0) {
      return triggerJudgeAssessment(debateId);
    }
  }, [debate, debateId, addNotification]);

  return { executeRound };
};
```

---

## 6. Component Integration Examples

### DebateSetup Component

```typescript
// components/DebateSetup.tsx
import React, { useState } from 'react';
import { useStore } from '../stores/debateStore';
import { useDebateOrchestrator } from '../hooks/useDebateOrchestrator';

export const DebateSetup: React.FC = () => {
  const [topic, setTopic] = useState('');
  const [format, setFormat] = useState<DebateFormat>('free-form');

  const createDebate = useStore((state) => state.createDebate);
  const activeProviders = useActiveProviders();

  const handleStart = () => {
    const debateId = createDebate({
      topic,
      format,
      mode: 'simultaneous',
      participants: [
        {
          id: 'p1',
          providerId: 'anthropic',
          modelId: 'claude-3-5-sonnet-20241022',
          personaMode: 'auto-assign',
          displayName: 'Claude',
          colorCode: '#6366f1',
        },
        {
          id: 'p2',
          providerId: 'openai',
          modelId: 'gpt-4',
          personaMode: 'auto-assign',
          displayName: 'GPT-4',
          colorCode: '#10b981',
        },
      ],
      judgeConfig: {
        providerId: 'anthropic',
        modelId: 'claude-3-5-sonnet-20241022',
        displayAssessments: false,
      },
      createdAt: Date.now(),
      id: '',
    });

    // Navigate to debate view
  };

  return (
    <div>
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Enter debate topic..."
      />

      <select value={format} onChange={(e) => setFormat(e.target.value as DebateFormat)}>
        <option value="free-form">Free-form</option>
        <option value="structured-rounds">Structured Rounds</option>
        <option value="round-limited">Round Limited</option>
        <option value="convergence-seeking">Convergence Seeking</option>
      </select>

      <button onClick={handleStart} disabled={!topic || activeProviders.length === 0}>
        Start Debate
      </button>
    </div>
  );
};
```

### ParticipantCard Component (Optimized)

```typescript
// components/ParticipantCard.tsx
import React from 'react';
import { useParticipant, useStreamingContent } from '../stores/selectors';

interface Props {
  debateId: string;
  participantId: string;
}

export const ParticipantCard = React.memo<Props>(
  ({ debateId, participantId }) => {
    const participant = useParticipant(debateId, participantId);
    const streamingContent = useStreamingContent(debateId, participantId);

    if (!participant) return null;

    return (
      <div style={{ borderLeft: `4px solid ${participant.config.colorCode}` }}>
        <h3>{participant.config.displayName}</h3>

        {participant.status === 'streaming' && (
          <div className="streaming-indicator">
            Typing... <span className="blink">|</span>
          </div>
        )}

        {streamingContent && (
          <div className="streaming-content">{streamingContent}</div>
        )}

        {participant.responseHistory.map((response) => (
          <div key={response.id} className="response">
            <div className="response-meta">
              Round {response.roundNumber} • {new Date(response.timestamp).toLocaleTimeString()}
            </div>
            <div className="response-content">{response.content}</div>
          </div>
        ))}

        <div className="token-usage">
          Tokens: {participant.tokenUsage.totalTokens} • Cost: $
          {participant.tokenUsage.estimatedCost.toFixed(4)}
        </div>
      </div>
    );
  },
  (prev, next) =>
    prev.debateId === next.debateId && prev.participantId === next.participantId
);
```

---

## 7. Testing Examples

### Store Test

```typescript
// stores/__tests__/debateSlice.test.ts
import { renderHook, act } from '@testing-library/react';
import { useStore } from '../debateStore';

describe('debateSlice', () => {
  beforeEach(() => {
    // Reset store
    useStore.setState({
      debates: {},
      activeDebateId: null,
    });
  });

  it('creates a new debate', () => {
    const { result } = renderHook(() => useStore());

    let debateId: string;

    act(() => {
      debateId = result.current.createDebate({
        topic: 'Test topic',
        format: 'free-form',
        mode: 'sequential',
        participants: [],
        judgeConfig: {} as any,
        createdAt: Date.now(),
        id: '',
      });
    });

    expect(result.current.debates[debateId!]).toBeDefined();
    expect(result.current.debates[debateId!].config.topic).toBe('Test topic');
    expect(result.current.activeDebateId).toBe(debateId!);
  });

  it('adds stream chunks incrementally', () => {
    const { result } = renderHook(() => useStore());

    const debateId = 'test-debate';
    const participantId = 'p1';

    // Setup initial state
    act(() => {
      useStore.setState({
        debates: {
          [debateId]: {
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
          } as any,
        },
      });
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
});
```

---

## 8. Common Patterns

### Pattern 1: Debounced State Updates

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedAddChunk = useDebouncedCallback(
  (chunk: string) => {
    addStreamChunk(debateId, participantId, chunk);
  },
  100
);
```

### Pattern 2: Optimistic Updates

```typescript
const mutation = useMutation({
  mutationFn: async (data) => {
    // Make API call
    return await api.post(data);
  },
  onMutate: async (newData) => {
    // Optimistically update UI
    useStore.getState().addOptimisticResponse(newData);
  },
  onError: (err, variables, context) => {
    // Rollback on error
    useStore.getState().removeOptimisticResponse(variables.id);
  },
  onSuccess: (data) => {
    // Replace optimistic with real data
    useStore.getState().replaceWithRealResponse(data);
  },
});
```

### Pattern 3: Subscription to State Changes

```typescript
useEffect(() => {
  const unsubscribe = useStore.subscribe(
    (state) => state.debates[debateId]?.status,
    (status, prevStatus) => {
      if (status === 'completed' && prevStatus !== 'completed') {
        // Debate just completed
        showCompletionAnimation();
      }
    }
  );

  return unsubscribe;
}, [debateId]);
```

This implementation guide provides practical, production-ready code that contributors can use immediately. Each section builds upon the previous one to create a cohesive state management system.
