/**
 * useSequentialDebate Hook
 * Orchestrates XState machine with backend API for sequential debates
 * Handles SSE streaming, API calls, and event routing
 */
import { useEffect, useRef, useCallback } from 'react';
import { useDebateMachine, type UseDebateMachineReturn } from './useDebateMachine';
import type { DebateConfig, ParticipantResponse } from '@/lib/debate/debate-machine';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SequentialTurnEvent {
  event_type: string;
  debate_id: string;
  round_number: number;
  turn_index: number;
  data: Record<string, any>;
  timestamp: string;
}

export function useSequentialDebate() {
  const machine = useDebateMachine();
  const { send, context, isRunning, isReady, isPaused } = machine;

  const eventSourceRef = useRef<EventSource | null>(null);
  const debateIdRef = useRef<string | null>(null);

  /**
   * Start a new debate
   */
  const startDebate = useCallback(async (config: DebateConfig) => {
    try {
      // Create debate via API
      const response = await fetch(`${API_BASE}/api/v1/debates/v2`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create debate');
      }

      const debate = await response.json();
      debateIdRef.current = debate.id;

      // Send START_DEBATE event to machine
      send({ type: 'START_DEBATE' });

      // Wait a bit for state to update
      await new Promise(resolve => setTimeout(resolve, 50));

      // Start first turn
      requestNextTurn(debate.id);

    } catch (error) {
      console.error('Error starting debate:', error);
      send({
        type: 'ERROR',
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }, [send]);

  /**
   * Request next participant's turn via SSE
   */
  const requestNextTurn = useCallback((debateId: string) => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Send NEXT_TURN event to machine
    send({ type: 'NEXT_TURN' });

    // Open SSE connection
    const eventSource = new EventSource(
      `${API_BASE}/api/v1/debates/v2/${debateId}/next-turn`
    );

    eventSource.onmessage = (event) => {
      try {
        const turnEvent: SequentialTurnEvent = JSON.parse(event.data);

        switch (turnEvent.event_type) {
          case 'debate_start':
            // Debate started
            console.log('Debate started:', turnEvent.data);
            break;

          case 'round_start':
            console.log('Round started:', turnEvent.round_number);
            break;

          case 'participant_start':
            send({
              type: 'STREAM_START',
              participantName: turnEvent.data.participant_name,
            });
            break;

          case 'chunk':
            send({
              type: 'STREAM_CHUNK',
              text: turnEvent.data.text,
            });
            break;

          case 'participant_complete':
            // Create ParticipantResponse object from context
            const response: ParticipantResponse = {
              participant_name: turnEvent.data.participant_name,
              participant_index: turnEvent.turn_index,
              model: context.config?.participants[turnEvent.turn_index]?.model || '',
              content: context.accumulatedText,
              tokens_used: turnEvent.data.tokens_used,
              response_time_ms: turnEvent.data.response_time_ms,
              timestamp: turnEvent.timestamp,
            };

            send({
              type: 'STREAM_COMPLETE',
              response,
            });

            // Close this connection
            eventSource.close();
            eventSourceRef.current = null;

            // Check if we need to request next turn
            setTimeout(() => {
              // If machine is in ready state, request next turn
              if (machine.isReady && !machine.isCompleted) {
                requestNextTurn(debateId);
              }
            }, 100);
            break;

          case 'round_complete':
            send({
              type: 'ROUND_COMPLETE',
              roundNumber: turnEvent.round_number,
            });
            break;

          case 'debate_complete':
            send({ type: 'DEBATE_COMPLETE' });
            eventSource.close();
            eventSourceRef.current = null;
            break;

          case 'cost_update':
            send({
              type: 'COST_UPDATE',
              costData: turnEvent.data,
            });
            break;

          case 'error':
            send({
              type: 'ERROR',
              error: turnEvent.data.error || 'Unknown error',
            });
            eventSource.close();
            eventSourceRef.current = null;
            break;
        }
      } catch (error) {
        console.error('Error parsing SSE event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
      eventSourceRef.current = null;

      send({
        type: 'ERROR',
        error: 'Connection to server lost',
      });
    };

    eventSourceRef.current = eventSource;
  }, [send, context, machine]);

  /**
   * Pause the debate
   */
  const pauseDebate = useCallback(async () => {
    if (!debateIdRef.current) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/debates/v2/${debateIdRef.current}/pause`,
        { method: 'POST' }
      );

      if (response.ok) {
        send({ type: 'PAUSE' });

        // Close SSE connection
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      }
    } catch (error) {
      console.error('Error pausing debate:', error);
    }
  }, [send]);

  /**
   * Resume the debate
   */
  const resumeDebate = useCallback(async () => {
    if (!debateIdRef.current) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/debates/v2/${debateIdRef.current}/resume`,
        { method: 'POST' }
      );

      if (response.ok) {
        send({ type: 'RESUME' });

        // Wait for state to update, then request next turn
        setTimeout(() => {
          if (debateIdRef.current) {
            requestNextTurn(debateIdRef.current);
          }
        }, 100);
      }
    } catch (error) {
      console.error('Error resuming debate:', error);
    }
  }, [send, requestNextTurn]);

  /**
   * Stop the debate manually
   */
  const stopDebate = useCallback(async () => {
    if (!debateIdRef.current) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/debates/v2/${debateIdRef.current}/stop`,
        { method: 'POST' }
      );

      if (response.ok) {
        send({ type: 'STOP' });

        // Close SSE connection
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      }
    } catch (error) {
      console.error('Error stopping debate:', error);
    }
  }, [send]);

  /**
   * Get debate summary
   */
  const getSummary = useCallback(async () => {
    if (!debateIdRef.current) return null;

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/debates/v2/${debateIdRef.current}/summary`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch summary');
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching summary:', error);
      return null;
    }
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  return {
    ...machine,
    startDebate,
    pauseDebate,
    resumeDebate,
    stopDebate,
    getSummary,
    debateId: debateIdRef.current,
  };
}

export type UseSequentialDebateReturn = ReturnType<typeof useSequentialDebate>;
