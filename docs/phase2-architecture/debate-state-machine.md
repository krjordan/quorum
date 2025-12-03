# Phase 2: XState Debate State Machine Architecture

## Overview

The debate state machine orchestrates multi-LLM debates with deterministic state transitions, error handling, and cost tracking. Built on XState v5 for TypeScript-first state management.

## State Machine Diagram

```
                    ┌─────────────────┐
                    │      IDLE       │ (initial)
                    └────────┬────────┘
                             │ START_DEBATE
                             ▼
                    ┌─────────────────┐
                    │  INITIALIZING   │
                    └────────┬────────┘
                             │ INIT_COMPLETE
                             ▼
              ┌──────────────────────────┐
              │   AWAITING_ARGUMENTS     │
              └──────────┬───────────────┘
                         │ ARGUMENTS_READY
                         ▼
              ┌──────────────────────────┐
         ┌────│   DEBATING_ROUND_1       │────┐
         │    └──────────────────────────┘    │
         │             │ ROUND_COMPLETE        │
         │             ▼                       │
         │    ┌──────────────────────────┐    │
         │    │   DEBATING_ROUND_N       │    │ (2-10 rounds)
         │    └──────────┬───────────────┘    │
         │               │ ALL_ROUNDS_COMPLETE │
         │               ▼                     │
         │    ┌──────────────────────────┐    │
         │    │    JUDGE_EVALUATING      │    │
         │    └──────────┬───────────────┘    │
         │               │ VERDICT_READY      │
         │               ▼                     │
         │    ┌──────────────────────────┐    │
         └───▶│      COMPLETED           │◀───┘
              └──────────┬───────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
     ┌────────────────┐    ┌────────────────┐
     │     ERROR      │    │     PAUSED     │
     └────────────────┘    └────────────────┘
              │                     │ RESUME
              │ RETRY               ▼
              └────────────▶ (return to last state)
```

## State Definitions

### States

```typescript
type DebateState =
  | 'idle'
  | 'initializing'
  | 'awaitingArguments'
  | 'debating'
  | 'judgeEvaluating'
  | 'completed'
  | 'paused'
  | 'error';
```

### State Details

#### 1. IDLE (Initial State)
- **Description**: Waiting for debate configuration
- **Entry Actions**: None
- **Exit Conditions**: Valid debate config provided
- **Next States**: `initializing`, `error`

#### 2. INITIALIZING
- **Description**: Setting up debate participants, validating models, initializing cost tracking
- **Entry Actions**:
  - Validate debate configuration
  - Initialize participant LLM clients
  - Create cost tracking context
  - Store debate metadata
- **Exit Conditions**: All participants initialized successfully
- **Next States**: `awaitingArguments`, `error`
- **Error Handling**: Model unavailable, invalid config, API errors

#### 3. AWAITING_ARGUMENTS
- **Description**: Waiting for initial arguments from all debaters
- **Entry Actions**:
  - Prompt each debater for opening statement
  - Start SSE streams for each participant
  - Initialize token counters
- **Exit Conditions**: All opening arguments received
- **Next States**: `debating`, `error`, `paused`
- **Timeout**: 120 seconds per debater

#### 4. DEBATING
- **Description**: Active debate rounds in progress
- **Entry Actions**:
  - Increment round counter
  - Provide context from previous rounds
  - Track token usage per model
- **Substates**:
  - `collectingResponses`: Gathering rebuttals from all participants
  - `processingRound`: Validating and storing round data
- **Exit Conditions**:
  - Max rounds reached (configurable, default 5)
  - Manual stop triggered
  - Cost limit exceeded
- **Next States**: `debating` (next round), `judgeEvaluating`, `paused`, `error`

#### 5. JUDGE_EVALUATING
- **Description**: Judge LLM analyzing debate and providing verdict
- **Entry Actions**:
  - Compile full debate transcript
  - Invoke judge model with evaluation prompt
  - Track judge token usage
- **Exit Conditions**: Verdict received with scores
- **Next States**: `completed`, `error`
- **Timeout**: 180 seconds

#### 6. COMPLETED
- **Description**: Debate finished with final verdict
- **Entry Actions**:
  - Calculate total costs
  - Store final results
  - Emit completion event
- **Final State**: Yes
- **Persist**: Full debate transcript, verdict, costs

#### 7. PAUSED
- **Description**: Debate temporarily suspended
- **Entry Actions**:
  - Save current state snapshot
  - Cancel active streams
- **Exit Conditions**: User resumes or cancels
- **Next States**: Previous active state, `completed`, `error`

#### 8. ERROR
- **Description**: Unrecoverable error occurred
- **Entry Actions**:
  - Log error details
  - Cleanup active connections
  - Calculate costs up to error point
- **Exit Conditions**: User retries or abandons
- **Next States**: `initializing` (retry), `completed` (abandon)

## Context Structure

```typescript
interface DebateContext {
  // Configuration
  config: DebateConfig;

  // Participants
  participants: DebateParticipant[];
  judge: JudgeParticipant;

  // Runtime State
  currentRound: number;
  maxRounds: number;
  rounds: DebateRound[];

  // Streaming
  activeStreams: Map<string, ReadableStream>;

  // Cost Tracking
  costTracker: CostTracker;
  tokenUsage: Map<string, ModelTokenUsage>;

  // Results
  verdict?: JudgeVerdict;

  // Error Handling
  lastError?: DebateError;
  retryCount: number;
}

interface DebateConfig {
  id: string;
  topic: string;
  format: 'oxford' | 'lincoln-douglas' | 'roundtable';
  maxRounds: number;
  timeoutPerRound: number; // seconds
  costLimit?: number; // USD
  warnAtCost?: number; // USD
}

interface DebateParticipant {
  id: string;
  name: string;
  model: LLMModel;
  position: 'for' | 'against' | 'neutral';
  systemPrompt: string;
  color: string; // UI color coding
}

interface JudgeParticipant {
  id: string;
  name: string;
  model: LLMModel;
  evaluationCriteria: string[];
}

interface LLMModel {
  provider: 'anthropic' | 'openai' | 'google' | 'mistral';
  modelId: string;
  apiKey: string;
  temperature: number;
  maxTokens: number;
}

interface DebateRound {
  roundNumber: number;
  timestamp: Date;
  responses: DebateResponse[];
  tokensUsed: number;
  costThisRound: number;
}

interface DebateResponse {
  participantId: string;
  content: string;
  tokensUsed: number;
  latencyMs: number;
  timestamp: Date;
}

interface CostTracker {
  totalCost: number;
  costByModel: Map<string, number>;
  warningThreshold: number;
  limitThreshold?: number;
  warnings: CostWarning[];
}

interface ModelTokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalCost: number;
  requestCount: number;
}

interface JudgeVerdict {
  winner?: string; // participant ID
  scores: Map<string, number>; // participant ID -> score (0-100)
  reasoning: string;
  criteria: Map<string, string>; // criterion -> evaluation
  tokensUsed: number;
  timestamp: Date;
}

interface DebateError {
  type: 'model_error' | 'timeout' | 'cost_limit' | 'validation' | 'network';
  message: string;
  participantId?: string;
  retryable: boolean;
  timestamp: Date;
}

interface CostWarning {
  threshold: number;
  currentCost: number;
  timestamp: Date;
  acknowledged: boolean;
}
```

## Event Types

```typescript
type DebateEvent =
  | { type: 'START_DEBATE'; config: DebateConfig }
  | { type: 'INIT_COMPLETE'; participants: DebateParticipant[] }
  | { type: 'ARGUMENTS_READY'; responses: DebateResponse[] }
  | { type: 'ROUND_COMPLETE'; round: DebateRound }
  | { type: 'ALL_ROUNDS_COMPLETE' }
  | { type: 'VERDICT_READY'; verdict: JudgeVerdict }
  | { type: 'PAUSE' }
  | { type: 'RESUME' }
  | { type: 'STOP' }
  | { type: 'ERROR'; error: DebateError }
  | { type: 'RETRY' }
  | { type: 'COST_WARNING'; warning: CostWarning }
  | { type: 'ACKNOWLEDGE_WARNING' }
  | { type: 'STREAM_CHUNK'; participantId: string; chunk: string }
  | { type: 'STREAM_COMPLETE'; participantId: string };
```

## Guard Conditions

```typescript
const guards = {
  // Check if all participants initialized
  allParticipantsReady: (context: DebateContext) => {
    return context.participants.every(p => p.model !== null);
  },

  // Check if all arguments received
  allArgumentsReceived: (context: DebateContext) => {
    return context.activeStreams.size === 0 &&
           context.rounds[0]?.responses.length === context.participants.length;
  },

  // Check if max rounds reached
  maxRoundsReached: (context: DebateContext) => {
    return context.currentRound >= context.maxRounds;
  },

  // Check if cost limit exceeded
  costLimitExceeded: (context: DebateContext) => {
    return context.config.costLimit !== undefined &&
           context.costTracker.totalCost >= context.config.costLimit;
  },

  // Check if cost warning threshold reached
  costWarningThreshold: (context: DebateContext) => {
    return context.config.warnAtCost !== undefined &&
           context.costTracker.totalCost >= context.config.warnAtCost &&
           !context.costTracker.warnings.some(w => w.acknowledged);
  },

  // Check if error is retryable
  canRetry: (context: DebateContext) => {
    return context.lastError?.retryable === true &&
           context.retryCount < 3;
  },

  // Check if debate should auto-stop
  shouldAutoStop: (context: DebateContext) => {
    return context.costTracker.limitThreshold !== undefined &&
           context.costTracker.totalCost >= context.costTracker.limitThreshold;
  }
};
```

## XState Machine Definition

```typescript
import { createMachine, assign } from 'xstate';

export const debateMachine = createMachine({
  id: 'debate',
  initial: 'idle',
  types: {} as {
    context: DebateContext;
    events: DebateEvent;
  },
  context: {
    config: {} as DebateConfig,
    participants: [],
    judge: {} as JudgeParticipant,
    currentRound: 0,
    maxRounds: 5,
    rounds: [],
    activeStreams: new Map(),
    costTracker: {
      totalCost: 0,
      costByModel: new Map(),
      warningThreshold: 0,
      warnings: []
    },
    tokenUsage: new Map(),
    retryCount: 0
  },
  states: {
    idle: {
      on: {
        START_DEBATE: {
          target: 'initializing',
          actions: assign({
            config: ({ event }) => event.config,
            retryCount: 0
          })
        }
      }
    },

    initializing: {
      entry: ['initializeParticipants', 'setupCostTracking'],
      on: {
        INIT_COMPLETE: {
          target: 'awaitingArguments',
          guard: 'allParticipantsReady',
          actions: assign({
            participants: ({ event }) => event.participants
          })
        },
        ERROR: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => event.error
          })
        }
      }
    },

    awaitingArguments: {
      entry: ['promptOpeningArguments', 'startParticipantStreams'],
      on: {
        STREAM_CHUNK: {
          actions: 'updateStreamingContent'
        },
        STREAM_COMPLETE: {
          actions: 'recordCompletedStream'
        },
        ARGUMENTS_READY: {
          target: 'debating',
          guard: 'allArgumentsReceived',
          actions: assign({
            rounds: ({ context, event }) => [
              {
                roundNumber: 1,
                timestamp: new Date(),
                responses: event.responses,
                tokensUsed: event.responses.reduce((sum, r) => sum + r.tokensUsed, 0),
                costThisRound: calculateRoundCost(event.responses)
              }
            ],
            currentRound: 1
          })
        },
        PAUSE: 'paused',
        ERROR: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => event.error
          })
        }
      }
    },

    debating: {
      entry: ['startDebateRound', 'trackRoundCosts'],
      on: {
        STREAM_CHUNK: {
          actions: 'updateStreamingContent'
        },
        ROUND_COMPLETE: [
          {
            target: 'judgeEvaluating',
            guard: 'maxRoundsReached',
            actions: 'recordRound'
          },
          {
            target: 'debating',
            actions: ['recordRound', 'incrementRound']
          }
        ],
        COST_WARNING: {
          actions: 'displayCostWarning'
        },
        PAUSE: 'paused',
        STOP: 'judgeEvaluating',
        ERROR: {
          target: 'error',
          guard: 'canRetry',
          actions: assign({
            lastError: ({ event }) => event.error,
            retryCount: ({ context }) => context.retryCount + 1
          })
        }
      },
      always: [
        {
          target: 'error',
          guard: 'costLimitExceeded',
          actions: assign({
            lastError: () => ({
              type: 'cost_limit',
              message: 'Cost limit exceeded',
              retryable: false,
              timestamp: new Date()
            })
          })
        }
      ]
    },

    judgeEvaluating: {
      entry: ['compileTranscript', 'invokeJudge', 'trackJudgeCosts'],
      on: {
        VERDICT_READY: {
          target: 'completed',
          actions: assign({
            verdict: ({ event }) => event.verdict
          })
        },
        ERROR: {
          target: 'error',
          actions: assign({
            lastError: ({ event }) => event.error
          })
        }
      }
    },

    completed: {
      type: 'final',
      entry: ['calculateFinalCosts', 'persistDebateResults', 'emitCompletion']
    },

    paused: {
      entry: ['saveStateSnapshot', 'cancelActiveStreams'],
      on: {
        RESUME: {
          target: '#debate.debating',
          actions: 'restoreState'
        },
        STOP: 'completed'
      }
    },

    error: {
      entry: ['logError', 'cleanupConnections'],
      on: {
        RETRY: {
          target: 'initializing',
          guard: 'canRetry'
        },
        STOP: 'completed'
      }
    }
  }
});

// Helper function
function calculateRoundCost(responses: DebateResponse[]): number {
  // Token cost calculation based on model pricing
  return responses.reduce((sum, r) => {
    // Example: Claude Sonnet @ $3/$15 per 1M tokens
    const inputCost = (r.tokensUsed * 0.003) / 1000;
    const outputCost = (r.tokensUsed * 0.015) / 1000;
    return sum + inputCost + outputCost;
  }, 0);
}
```

## State Transition Examples

### Happy Path Flow

```typescript
// 1. User configures debate
machine.send({
  type: 'START_DEBATE',
  config: {
    id: 'debate-123',
    topic: 'Should AI be regulated?',
    format: 'oxford',
    maxRounds: 5,
    timeoutPerRound: 60,
    costLimit: 5.0,
    warnAtCost: 3.0
  }
});
// State: idle → initializing

// 2. Participants initialized
machine.send({
  type: 'INIT_COMPLETE',
  participants: [/* ... */]
});
// State: initializing → awaitingArguments

// 3. Opening arguments received
machine.send({
  type: 'ARGUMENTS_READY',
  responses: [/* ... */]
});
// State: awaitingArguments → debating (round 1)

// 4. Each round completes
machine.send({ type: 'ROUND_COMPLETE', round: {/* ... */} });
// State: debating (round N) → debating (round N+1)

// 5. Final round triggers judge
machine.send({ type: 'ROUND_COMPLETE', round: {/* ... */} });
// State: debating → judgeEvaluating

// 6. Judge provides verdict
machine.send({
  type: 'VERDICT_READY',
  verdict: {/* ... */}
});
// State: judgeEvaluating → completed
```

### Error Recovery Flow

```typescript
// During debate, API timeout occurs
machine.send({
  type: 'ERROR',
  error: {
    type: 'timeout',
    message: 'Claude API timeout',
    participantId: 'debater-1',
    retryable: true,
    timestamp: new Date()
  }
});
// State: debating → error

// User retries
machine.send({ type: 'RETRY' });
// State: error → initializing → debating (resumes)
```

### Cost Warning Flow

```typescript
// Cost threshold reached during debate
machine.send({
  type: 'COST_WARNING',
  warning: {
    threshold: 3.0,
    currentCost: 3.15,
    timestamp: new Date(),
    acknowledged: false
  }
});
// State: debating (displays warning modal)

// User acknowledges and continues
machine.send({ type: 'ACKNOWLEDGE_WARNING' });
// State: debating (continues)

// OR user stops early
machine.send({ type: 'STOP' });
// State: debating → judgeEvaluating → completed
```

## Integration with React

```typescript
import { useMachine } from '@xstate/react';
import { debateMachine } from './debate-machine';

function DebateContainer() {
  const [state, send] = useMachine(debateMachine);

  const startDebate = (config: DebateConfig) => {
    send({ type: 'START_DEBATE', config });
  };

  const pauseDebate = () => {
    send({ type: 'PAUSE' });
  };

  const stopDebate = () => {
    send({ type: 'STOP' });
  };

  return (
    <div>
      <DebateStatus state={state.value} />
      <CostTracker
        totalCost={state.context.costTracker.totalCost}
        warning={state.context.costTracker.warnings[0]}
      />
      {state.matches('debating') && (
        <DebateArena
          participants={state.context.participants}
          currentRound={state.context.currentRound}
          rounds={state.context.rounds}
        />
      )}
      {state.matches('completed') && (
        <DebateResults verdict={state.context.verdict} />
      )}
    </div>
  );
}
```

## Testing State Machine

```typescript
import { createActor } from 'xstate';
import { describe, it, expect } from 'vitest';

describe('Debate State Machine', () => {
  it('should transition from idle to initializing', () => {
    const actor = createActor(debateMachine);
    actor.start();

    expect(actor.getSnapshot().value).toBe('idle');

    actor.send({
      type: 'START_DEBATE',
      config: mockDebateConfig
    });

    expect(actor.getSnapshot().value).toBe('initializing');
  });

  it('should handle cost limit exceeded', () => {
    const actor = createActor(debateMachine.provide({
      context: {
        ...debateMachine.context,
        costTracker: {
          totalCost: 5.5,
          costByModel: new Map(),
          warningThreshold: 3.0,
          limitThreshold: 5.0,
          warnings: []
        },
        config: {
          ...mockConfig,
          costLimit: 5.0
        }
      }
    }));
    actor.start();

    // Should auto-transition to error
    expect(actor.getSnapshot().value).toBe('error');
    expect(actor.getSnapshot().context.lastError?.type).toBe('cost_limit');
  });
});
```

## Performance Considerations

1. **State Persistence**: Serialize context to localStorage on each transition
2. **Stream Buffering**: Buffer chunks to reduce state updates (batch every 100ms)
3. **Cost Calculation**: Cache token pricing, update totals incrementally
4. **Memory Management**: Clear completed streams from activeStreams map
5. **Reconnection**: Store debate ID for SSE reconnection with Last-Event-ID

## Next Steps

1. Implement XState machine in `/frontend/src/machines/debate-machine.ts`
2. Create React hooks: `useDebateMachine`, `useDebateState`
3. Integrate with Zustand for UI state (separate from machine state)
4. Build backend endpoints to match state transitions
5. Add comprehensive unit tests for all transitions and guards
