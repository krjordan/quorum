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
  const { send, context, isRunning, isReady, isPaused, isCompleted, stateValue } = machine;

  const eventSourceRef = useRef<EventSource | null>(null);
  const debateIdRef = useRef<string | null>(null);
  const accumulatedTextRef = useRef<string>('');

  // Debug logging for state changes
  console.log('[useSequentialDebate] State:', stateValue);
  console.log('[useSequentialDebate] Context:', {
    debateId: context.debateId,
    currentRound: context.currentRound,
    currentTurn: context.currentTurn,
    isStreaming: context.isStreaming
  });

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
    console.log('[requestNextTurn] Called with debateId:', debateId);
    // Close existing connection if any
    if (eventSourceRef.current) {
      console.log('[requestNextTurn] Closing existing SSE connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Clear accumulated text for new turn
    accumulatedTextRef.current = '';

    // Send NEXT_TURN event to machine
    console.log('[requestNextTurn] Sending NEXT_TURN event to machine');
    send({ type: 'NEXT_TURN' });

    // Open SSE connection
    console.log('[requestNextTurn] Opening new SSE connection');
    const eventSource = new EventSource(
      `${API_BASE}/api/v1/debates/v2/${debateId}/next-turn`
    );

    eventSource.onmessage = (event) => {
      try {
        const turnEvent: SequentialTurnEvent = JSON.parse(event.data);
        console.log('[SSE] Received event:', turnEvent.event_type, turnEvent);

        switch (turnEvent.event_type) {
          case 'debate_start':
            // Debate started
            console.log('[SSE] Debate started:', turnEvent.data);
            break;

          case 'round_start':
            console.log('[SSE] Round started:', turnEvent.round_number);
            break;

          case 'participant_start':
            console.log('[SSE] Participant start, sending STREAM_START');
            // Clear accumulated text for new participant
            accumulatedTextRef.current = '';
            send({
              type: 'STREAM_START',
              participantName: turnEvent.data.participant_name,
            });
            break;

          case 'chunk':
            // Ignore streaming chunks - we'll show loading indicator instead
            // Just accumulate for participant_complete event
            accumulatedTextRef.current += turnEvent.data.text;
            break;

          case 'participant_complete':
            console.log('[SSE] Participant complete, sending STREAM_COMPLETE');
            console.log('[SSE] accumulatedTextRef.current length:', accumulatedTextRef.current.length);
            console.log('[SSE] accumulatedTextRef.current preview:', accumulatedTextRef.current.substring(0, 100));
            // Create ParticipantResponse object using ref (fixes stale closure issue)
            const response: ParticipantResponse = {
              participant_name: turnEvent.data.participant_name,
              participant_index: turnEvent.turn_index,
              model: context.config?.participants[turnEvent.turn_index]?.model || '',
              content: accumulatedTextRef.current, // Use ref instead of stale context
              tokens_used: turnEvent.data.tokens_used,
              response_time_ms: turnEvent.data.response_time_ms,
              timestamp: turnEvent.timestamp,
            };

            console.log('[SSE] Created response object, content length:', response.content.length);
            console.log('[SSE] Sending STREAM_COMPLETE event');
            send({
              type: 'STREAM_COMPLETE',
              response,
            });

            // Close this connection
            console.log('[SSE] Closing SSE connection');
            eventSource.close();
            eventSourceRef.current = null;

            // Auto-advance is now handled by useEffect
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
              costData: turnEvent.data as any,
            });
            break;

          case 'quality_update':
            // Handle quality monitoring events from backend
            console.log('[SSE] Quality update received:', turnEvent.data);

            if (turnEvent.data.quality_type === 'health_score') {
              send({
                type: 'HEALTH_SCORE_UPDATE',
                score: turnEvent.data.score,
                trend: turnEvent.data.trend,
                recommendation: turnEvent.data.recommendation,
              });
            } else if (turnEvent.data.quality_type === 'contradiction') {
              send({
                type: 'CONTRADICTION_DETECTED',
                contradiction: {
                  id: turnEvent.data.id || `contradiction_${Date.now()}`,
                  severity: turnEvent.data.severity || 'medium',
                  statement1: turnEvent.data.statement1,
                  statement2: turnEvent.data.statement2,
                  similarityScore: turnEvent.data.similarity_score,
                  timestamp: turnEvent.timestamp,
                },
              });
            } else if (turnEvent.data.quality_type === 'loop_detected') {
              send({
                type: 'LOOP_DETECTED',
                patternLength: turnEvent.data.pattern_length || 0,
                repetitions: turnEvent.data.repetitions || 0,
              });
            }
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
   * Auto-advance to next turn when in ready state
   */
  useEffect(() => {
    console.log('[AUTO-ADVANCE] Effect triggered:', { isReady, hasDebateId: !!debateIdRef.current, isCompleted });
    if (isReady && debateIdRef.current && !isCompleted) {
      console.log('[AUTO-ADVANCE] Scheduling next turn request in 100ms');
      // Small delay to ensure state has settled
      const timer = setTimeout(() => {
        console.log('[AUTO-ADVANCE] Requesting next turn now');
        requestNextTurn(debateIdRef.current!);
      }, 100);
      return () => {
        console.log('[AUTO-ADVANCE] Cleanup - clearing timer');
        clearTimeout(timer);
      };
    }
  }, [isReady, isCompleted, requestNextTurn]);

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
