/**
 * Debate State Machine (XState v5)
 * Sequential turn-based multi-LLM debate orchestration
 * Phase 2 implementation without AI judge
 */
import { setup, assign, fromPromise } from 'xstate';

// ===== Types =====

export interface ParticipantConfig {
  name: string;
  model: string;
  system_prompt: string;
  temperature?: number;
}

export interface DebateConfig {
  topic: string;
  participants: ParticipantConfig[];
  max_rounds: number;
  context_window_rounds?: number;
  cost_warning_threshold?: number;
}

export interface ParticipantResponse {
  participant_name: string;
  participant_index: number;
  model: string;
  content: string;
  tokens_used: number;
  response_time_ms: number;
  timestamp: string;
}

export interface DebateRound {
  round_number: number;
  responses: ParticipantResponse[];
  tokens_used: Record<string, number>;
  cost_estimate: number;
  timestamp: string;
}

export interface CostData {
  total_cost: number;
  round_cost: number;
  total_tokens: Record<string, number>;
  warning_threshold: number;
}

// ===== Context =====

export interface DebateMachineContext {
  // Configuration
  config: DebateConfig | null;

  // Debate state
  debateId: string | null;
  currentRound: number;
  currentTurn: number;

  // Streaming state
  isStreaming: boolean;
  currentParticipantName: string | null;
  accumulatedText: string;

  // Debate data
  rounds: DebateRound[];

  // Cost tracking
  totalCost: number;
  totalTokens: Record<string, number>;

  // Quality tracking
  healthScore: {
    score: number;
    trend?: 'improving' | 'stable' | 'declining';
    lastUpdate?: string;
    recommendation?: string;
  };
  contradictions: Array<{
    id: string;
    severity: 'high' | 'medium' | 'low';
    statement1: {
      participantName: string;
      content: string;
      messageId: string;
    };
    statement2: {
      participantName: string;
      content: string;
      messageId: string;
    };
    similarityScore?: number;
    timestamp: string;
  }>;
  loopDetected: boolean;

  // Errors
  error: string | null;
}

// ===== Events =====

export type DebateMachineEvent =
  | { type: 'SET_CONFIG'; config: DebateConfig }
  | { type: 'START_DEBATE' }
  | { type: 'NEXT_TURN' }
  | { type: 'PAUSE' }
  | { type: 'RESUME' }
  | { type: 'STOP' }
  | { type: 'STREAM_START'; participantName: string }
  | { type: 'STREAM_CHUNK'; text: string }
  | { type: 'STREAM_COMPLETE'; response: ParticipantResponse }
  | { type: 'ROUND_COMPLETE'; roundNumber: number }
  | { type: 'COST_UPDATE'; costData: CostData }
  | { type: 'ERROR'; error: string }
  | { type: 'DEBATE_COMPLETE' }
  | { type: 'HEALTH_SCORE_UPDATE'; score: number; trend?: 'improving' | 'stable' | 'declining'; recommendation?: string }
  | { type: 'CONTRADICTION_DETECTED'; contradiction: {
      id: string;
      severity: 'high' | 'medium' | 'low';
      statement1: { participantName: string; content: string; messageId: string };
      statement2: { participantName: string; content: string; messageId: string };
      similarityScore?: number;
      timestamp: string;
    }}
  | { type: 'LOOP_DETECTED'; patternLength: number; repetitions: number }
  | { type: 'DISMISS_CONTRADICTION'; contradictionId: string };

// ===== Guards =====

const canStartDebate = ({ context }: { context: DebateMachineContext }) => {
  if (!context.config) return false;

  const { topic, participants, max_rounds } = context.config;

  return (
    topic.trim().length > 0 &&
    participants.length >= 2 &&
    participants.length <= 4 &&
    max_rounds >= 1 &&
    max_rounds <= 5 &&
    participants.every(p => p.name.trim().length > 0 && p.model.trim().length > 0)
  );
};

const hasMoreTurns = ({ context }: { context: DebateMachineContext }) => {
  if (!context.config) return false;

  // Check if there are more participants in this round
  return context.currentTurn < context.config.participants.length;
};

const hasMoreRounds = ({ context }: { context: DebateMachineContext }) => {
  if (!context.config) return false;

  // Check if there are more rounds to complete
  return context.currentRound < context.config.max_rounds;
};

// ===== State Machine =====

export const debateMachine = setup({
  types: {
    context: {} as DebateMachineContext,
    events: {} as DebateMachineEvent,
  },
  guards: {
    canStartDebate,
    hasMoreTurns,
    hasMoreRounds,
  },
  actions: {
    setConfig: assign({
      config: ({ event }: any) => {
        if (event.type !== 'SET_CONFIG') return null;
        return event.config;
      },
      error: () => null,
    }),
    initializeDebate: assign({
      debateId: () => `debate_${Date.now()}`,
      currentRound: () => 1,
      currentTurn: () => 0,
      rounds: () => [],
      totalCost: () => 0,
      totalTokens: () => ({}),
      healthScore: () => ({
        score: 100,
        trend: 'stable' as const,
        lastUpdate: new Date().toISOString(),
      }),
      contradictions: () => [],
      loopDetected: () => false,
      error: () => null,
    }),
    startStreaming: assign({
      isStreaming: () => true,
      accumulatedText: () => '',
      currentParticipantName: ({ event }: any) => {
        if (event.type !== 'STREAM_START') return null;
        return event.participantName;
      },
    }),
    appendChunk: assign({
      accumulatedText: ({ context, event }: any) => {
        if (event.type !== 'STREAM_CHUNK') return context.accumulatedText;
        return context.accumulatedText + event.text;
      },
    }),
    completeParticipantResponse: assign(({ context, event }: any) => {
      if (event.type !== 'STREAM_COMPLETE') return context;

      const response = event.response;

      // Get or create current round
      let currentRoundObj = context.rounds[context.currentRound - 1];
      if (!currentRoundObj) {
        currentRoundObj = {
          round_number: context.currentRound,
          responses: [],
          tokens_used: {},
          cost_estimate: 0,
          timestamp: new Date().toISOString(),
        };
      }

      // Check if this participant already has a response in this round (prevent duplicates)
      const existingResponseIndex = currentRoundObj.responses.findIndex(
        (r: ParticipantResponse) => r.participant_index === response.participant_index
      );

      // Only add if not already present
      const updatedResponses = existingResponseIndex >= 0
        ? currentRoundObj.responses // Don't add duplicate
        : [...currentRoundObj.responses, response]; // Add new response

      // Add response to round
      const updatedRound = {
        ...currentRoundObj,
        responses: updatedResponses,
      };

      // Update rounds array
      const updatedRounds = [...context.rounds];
      updatedRounds[context.currentRound - 1] = updatedRound;

      return {
        rounds: updatedRounds,
        isStreaming: false,
        accumulatedText: '',
        currentParticipantName: null,
      };
    }),
    advanceTurn: assign(({ context }: any) => {
      const nextTurn = context.currentTurn + 1;

      // If we've gone through all participants, move to next round
      if (context.config && nextTurn >= context.config.participants.length) {
        return {
          currentTurn: 0,
          currentRound: context.currentRound + 1,
        };
      }

      return {
        currentTurn: nextTurn,
      };
    }),
    completeRound: assign(({ context, event }: any) => {
      if (event.type !== 'ROUND_COMPLETE') return context;

      // Round completion is already handled by advanceTurn
      // This is mainly for logging/debugging
      return context;
    }),
    updateCosts: assign(({ context, event }: any) => {
      if (event.type !== 'COST_UPDATE') return context;

      const { total_cost, round_cost, total_tokens } = event.costData;

      // Update the current round's cost estimate
      const updatedRounds = [...context.rounds];
      const currentRoundIndex = context.currentRound - 1;
      if (updatedRounds[currentRoundIndex]) {
        updatedRounds[currentRoundIndex] = {
          ...updatedRounds[currentRoundIndex],
          cost_estimate: round_cost,
        };
      }

      return {
        totalCost: total_cost,
        totalTokens: total_tokens,
        rounds: updatedRounds,
      };
    }),
    setError: assign({
      error: ({ event }: any) => {
        if (event.type !== 'ERROR') return null;
        return event.error;
      },
      isStreaming: () => false,
    }),
    clearError: assign({
      error: () => null,
    }),
    updateHealthScore: assign(({ context, event }: any) => {
      if (event.type !== 'HEALTH_SCORE_UPDATE') return context;

      return {
        healthScore: {
          score: event.score,
          trend: event.trend,
          lastUpdate: new Date().toISOString(),
          recommendation: event.recommendation,
        },
      };
    }),
    addContradiction: assign(({ context, event }: any) => {
      if (event.type !== 'CONTRADICTION_DETECTED') return context;

      return {
        contradictions: [...context.contradictions, event.contradiction],
      };
    }),
    dismissContradiction: assign(({ context, event }: any) => {
      if (event.type !== 'DISMISS_CONTRADICTION') return context;

      return {
        contradictions: context.contradictions.filter((c: any) => c.id !== event.contradictionId),
      };
    }),
    setLoopDetected: assign({
      loopDetected: () => true,
    }),
  },
}).createMachine({
  id: 'debate',
  initial: 'configuring',
  context: {
    config: null,
    debateId: null,
    currentRound: 1,
    currentTurn: 0,
    isStreaming: false,
    currentParticipantName: null,
    accumulatedText: '',
    rounds: [],
    totalCost: 0,
    totalTokens: {},
    healthScore: {
      score: 100,
      trend: 'stable' as const,
      lastUpdate: new Date().toISOString(),
    },
    contradictions: [],
    loopDetected: false,
    error: null,
  },
  states: {
    configuring: {
      on: {
        SET_CONFIG: {
          actions: 'setConfig',
        },
        START_DEBATE: {
          guard: 'canStartDebate',
          target: 'ready',
          actions: 'initializeDebate',
        },
      },
    },
    ready: {
      entry: 'clearError',
      on: {
        NEXT_TURN: {
          target: 'running',
        },
        SET_CONFIG: {
          target: 'configuring',
          actions: 'setConfig',
        },
      },
    },
    running: {
      entry: 'clearError',
      on: {
        STREAM_START: {
          actions: 'startStreaming',
        },
        STREAM_CHUNK: {
          actions: 'appendChunk',
        },
        STREAM_COMPLETE: {
          actions: ['completeParticipantResponse', 'advanceTurn'],
          target: 'checkingProgress',
        },
        COST_UPDATE: {
          actions: 'updateCosts',
        },
        HEALTH_SCORE_UPDATE: {
          actions: 'updateHealthScore',
        },
        CONTRADICTION_DETECTED: {
          actions: 'addContradiction',
        },
        LOOP_DETECTED: {
          actions: 'setLoopDetected',
        },
        DISMISS_CONTRADICTION: {
          actions: 'dismissContradiction',
        },
        PAUSE: {
          target: 'paused',
        },
        STOP: {
          target: 'completed',
        },
        ERROR: {
          target: 'error',
          actions: 'setError',
        },
      },
    },
    checkingProgress: {
      always: [
        {
          guard: ({ context }) => {
            if (!context.config) return false;
            // Check if round is complete and no more rounds
            return (
              context.currentTurn === 0 &&
              context.currentRound > context.config.max_rounds
            );
          },
          target: 'completed',
        },
        {
          guard: ({ context }) => {
            // Check if round is complete but more rounds remain
            return context.currentTurn === 0;
          },
          target: 'ready',
        },
        {
          // More turns in current round
          target: 'ready',
        },
      ],
    },
    paused: {
      on: {
        RESUME: {
          target: 'ready',
        },
        STOP: {
          target: 'completed',
        },
        SET_CONFIG: {
          target: 'configuring',
          actions: 'setConfig',
        },
      },
    },
    completed: {
      entry: 'clearError',
      type: 'final',
    },
    error: {
      on: {
        NEXT_TURN: {
          target: 'running',
          actions: 'clearError',
        },
        SET_CONFIG: {
          target: 'configuring',
          actions: ['setConfig', 'clearError'],
        },
        STOP: {
          target: 'completed',
        },
      },
    },
  },
});

export type DebateMachine = typeof debateMachine;
