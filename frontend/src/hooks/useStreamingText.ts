import { useState, useCallback, useRef } from "react";
import { SSEClient } from "@/lib/streaming/sse-client";

interface UseStreamingTextOptions {
  onChunk?: (text: string) => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
  bufferDelay?: number;
}

export function useStreamingText(options: UseStreamingTextOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const sseClientRef = useRef<SSEClient | null>(null);
  const accumulatedTextRef = useRef<string>("");
  const bufferRef = useRef<string>("");
  const bufferTimerRef = useRef<NodeJS.Timeout | null>(null);

  const flushBuffer = useCallback(() => {
    if (bufferRef.current) {
      accumulatedTextRef.current += bufferRef.current;
      // Call onChunk with the accumulated text so far
      options.onChunk?.(accumulatedTextRef.current);
      bufferRef.current = "";
    }
  }, [options]);

  const startStreaming = useCallback(
    async (response: Response) => {
      accumulatedTextRef.current = "";
      setIsStreaming(true);
      setError(null);
      bufferRef.current = "";

      const bufferDelay = options.bufferDelay || 50;

      sseClientRef.current = new SSEClient({
        onChunk: (chunk: string) => {
          bufferRef.current += chunk;

          // Debounce updates to reduce re-renders
          if (bufferTimerRef.current) {
            clearTimeout(bufferTimerRef.current);
          }

          bufferTimerRef.current = setTimeout(() => {
            flushBuffer();
          }, bufferDelay);
        },
        onComplete: () => {
          flushBuffer();
          setIsStreaming(false);
          options.onComplete?.();
        },
        onError: (err: Error) => {
          flushBuffer();
          setIsStreaming(false);
          setError(err);
          options.onError?.(err);
        },
      });

      await sseClientRef.current.connect(response);
    },
    [options, flushBuffer]
  );

  const stopStreaming = useCallback(() => {
    flushBuffer();
    sseClientRef.current?.disconnect();
    setIsStreaming(false);

    if (bufferTimerRef.current) {
      clearTimeout(bufferTimerRef.current);
    }
  }, [flushBuffer]);

  const reset = useCallback(() => {
    stopStreaming();
    accumulatedTextRef.current = "";
    setError(null);
  }, [stopStreaming]);

  return {
    isStreaming,
    error,
    startStreaming,
    stopStreaming,
    reset,
  };
}
