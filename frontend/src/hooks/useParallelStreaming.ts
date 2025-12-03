/**
 * Parallel Streaming Hook - Manage multiple SSE connections simultaneously
 * Phase 2 Implementation
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { SSEClient } from "@/lib/streaming/sse-client";
import type { ParallelStreamConfig } from "@/types/debate";

interface ParallelStreamState {
  streams: Map<string, string>; // participantId -> current text
  isStreaming: boolean;
  errors: Map<string, Error>; // participantId -> error
  completedStreams: Set<string>;
}

interface UseParallelStreamingOptions {
  onStreamUpdate?: (participantId: string, text: string) => void;
  onStreamComplete?: (participantId: string) => void;
  onStreamError?: (participantId: string, error: Error) => void;
  onAllComplete?: () => void;
  bufferDelay?: number; // ms to wait before flushing updates (default: 50)
}

export function useParallelStreaming(options: UseParallelStreamingOptions = {}) {
  const [state, setState] = useState<ParallelStreamState>({
    streams: new Map(),
    isStreaming: false,
    errors: new Map(),
    completedStreams: new Set(),
  });

  const sseClientsRef = useRef<Map<string, SSEClient>>(new Map());
  const bufferRef = useRef<Map<string, string>>(new Map());
  const bufferTimerRef = useRef<NodeJS.Timeout | null>(null);
  const expectedStreamsRef = useRef<number>(0);

  const bufferDelay = options.bufferDelay || 50;

  // Flush all buffers and update state
  const flushBuffers = useCallback(() => {
    if (bufferRef.current.size === 0) return;

    setState((prev) => {
      const newStreams = new Map(prev.streams);

      bufferRef.current.forEach((text, participantId) => {
        const currentText = newStreams.get(participantId) || "";
        const updatedText = currentText + text;
        newStreams.set(participantId, updatedText);

        // Notify callback
        options.onStreamUpdate?.(participantId, updatedText);
      });

      bufferRef.current.clear();

      return {
        ...prev,
        streams: newStreams,
      };
    });
  }, [options]);

  // Schedule buffer flush (debounced)
  const scheduleFlush = useCallback(() => {
    if (bufferTimerRef.current) {
      clearTimeout(bufferTimerRef.current);
    }

    bufferTimerRef.current = setTimeout(() => {
      flushBuffers();
    }, bufferDelay);
  }, [flushBuffers, bufferDelay]);

  // Start multiple streams in parallel
  const startStreaming = useCallback(
    async (configs: ParallelStreamConfig[]) => {
      // Reset state
      setState({
        streams: new Map(),
        isStreaming: true,
        errors: new Map(),
        completedStreams: new Set(),
      });

      bufferRef.current.clear();
      sseClientsRef.current.clear();
      expectedStreamsRef.current = configs.length;

      // Initialize stream placeholders
      const initialStreams = new Map<string, string>();
      configs.forEach(config => {
        initialStreams.set(config.participantId, "");
      });

      setState(prev => ({
        ...prev,
        streams: initialStreams,
      }));

      // Start all streams in parallel
      const streamPromises = configs.map(async (config) => {
        const { participantId, endpoint } = config;

        try {
          // Create SSE client for this participant
          const client = new SSEClient({
            onChunk: (chunk: string) => {
              // Add to buffer
              const current = bufferRef.current.get(participantId) || "";
              bufferRef.current.set(participantId, current + chunk);

              // Schedule flush
              scheduleFlush();
            },
            onComplete: () => {
              // Flush any remaining buffer
              flushBuffers();

              setState(prev => {
                const newCompleted = new Set(prev.completedStreams);
                newCompleted.add(participantId);

                // Check if all streams completed
                const allComplete = newCompleted.size === expectedStreamsRef.current;

                if (allComplete) {
                  options.onAllComplete?.();
                  return {
                    ...prev,
                    isStreaming: false,
                    completedStreams: newCompleted,
                  };
                }

                return {
                  ...prev,
                  completedStreams: newCompleted,
                };
              });

              options.onStreamComplete?.(participantId);
              sseClientsRef.current.delete(participantId);
            },
            onError: (error: Error) => {
              setState(prev => {
                const newErrors = new Map(prev.errors);
                newErrors.set(participantId, error);

                const newCompleted = new Set(prev.completedStreams);
                newCompleted.add(participantId);

                const allComplete = newCompleted.size === expectedStreamsRef.current;

                return {
                  ...prev,
                  errors: newErrors,
                  completedStreams: newCompleted,
                  isStreaming: !allComplete,
                };
              });

              options.onStreamError?.(participantId, error);
              sseClientsRef.current.delete(participantId);
            },
          });

          sseClientsRef.current.set(participantId, client);

          // Make the API request
          const response = await fetch(endpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(config),
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          await client.connect(response);
        } catch (error) {
          const err = error instanceof Error ? error : new Error(String(error));

          setState(prev => {
            const newErrors = new Map(prev.errors);
            newErrors.set(participantId, err);

            const newCompleted = new Set(prev.completedStreams);
            newCompleted.add(participantId);

            return {
              ...prev,
              errors: newErrors,
              completedStreams: newCompleted,
            };
          });

          options.onStreamError?.(participantId, err);
        }
      });

      // Wait for all streams to complete or fail
      await Promise.allSettled(streamPromises);
    },
    [options, scheduleFlush, flushBuffers]
  );

  // Stop all active streams
  const stopStreaming = useCallback(() => {
    flushBuffers();

    sseClientsRef.current.forEach((client) => {
      client.disconnect();
    });

    sseClientsRef.current.clear();

    setState(prev => ({
      ...prev,
      isStreaming: false,
    }));

    if (bufferTimerRef.current) {
      clearTimeout(bufferTimerRef.current);
    }
  }, [flushBuffers]);

  // Reset hook state
  const reset = useCallback(() => {
    stopStreaming();
    setState({
      streams: new Map(),
      isStreaming: false,
      errors: new Map(),
      completedStreams: new Set(),
    });
    bufferRef.current.clear();
  }, [stopStreaming]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, [stopStreaming]);

  return {
    streams: state.streams,
    isStreaming: state.isStreaming,
    errors: state.errors,
    completedStreams: state.completedStreams,
    startStreaming,
    stopStreaming,
    reset,
  };
}
