/**
 * useDebateMachine Hook
 * React hook wrapper for the debate XState machine
 * Provides state, context, and send function for debate management
 */
import { useMachine } from '@xstate/react';
import { debateMachine, type DebateMachineContext, type DebateMachineEvent } from '@/lib/debate/debate-machine';

export function useDebateMachine() {
  const [state, send] = useMachine(debateMachine);

  return {
    // Current state
    state,

    // State value for easy matching
    stateValue: state.value,

    // Context data
    context: state.context,

    // Send events to machine
    send,

    // Convenience state checkers
    isConfiguring: state.matches('configuring'),
    isReady: state.matches('ready'),
    isRunning: state.matches('running'),
    isPaused: state.matches('paused'),
    isCompleted: state.matches('completed'),
    isError: state.matches('error'),
    isCheckingProgress: state.matches('checkingProgress'),

    // Derived state
    canStart: state.can({ type: 'START_DEBATE' }),
    hasConfig: state.context.config !== null,
    hasError: state.context.error !== null,
  };
}

export type UseDebateMachineReturn = ReturnType<typeof useDebateMachine>;
