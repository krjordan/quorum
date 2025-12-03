"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/stores/chat-store";
import { useStreamingText } from "@/hooks/useStreamingText";
import { chatApi } from "@/lib/api/chat-api";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { BackendStatus } from "./BackendStatus";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

export function ChatInterface() {
  const [input, setInput] = useState("");
  const activeMessageIdRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    messages,
    addMessage,
    updateStreamingMessage,
    completeStreamingMessage,
  } = useChatStore();

  const { isStreaming, error: streamError, startStreaming, reset } = useStreamingText({
    onChunk: (text) => {
      // Update immediately on each chunk using ref (no effect delay)
      if (activeMessageIdRef.current) {
        updateStreamingMessage(activeMessageIdRef.current, text);
      }
    },
    onComplete: () => {
      if (activeMessageIdRef.current) {
        completeStreamingMessage(activeMessageIdRef.current);
        activeMessageIdRef.current = null;
      }
    },
    onError: (error) => {
      console.error("Streaming error:", error);
      if (activeMessageIdRef.current) {
        updateStreamingMessage(
          activeMessageIdRef.current,
          `❌ Error: ${error.message}\n\nMake sure the backend is running at ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}`
        );
        completeStreamingMessage(activeMessageIdRef.current);
        activeMessageIdRef.current = null;
      }
    },
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput("");

    // Add user message first
    addMessage({
      role: "user",
      content: userMessage,
    });

    // Add placeholder for assistant message and capture the ID immediately
    const assistantMessageId = addMessage({
      role: "assistant",
      content: "",
    });

    // Set the active message ID in ref (synchronous, no re-render)
    activeMessageIdRef.current = assistantMessageId;

    // Start streaming
    reset();

    try {
      const response = await chatApi.streamMessage({
        message: userMessage,
        conversationHistory: messages, // Send all previous messages as context
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await startStreaming(response);
    } catch (error) {
      console.error("Failed to start stream:", error);
      if (activeMessageIdRef.current) {
        updateStreamingMessage(
          activeMessageIdRef.current,
          `❌ Error: Failed to connect to backend\n\n${error instanceof Error ? error.message : 'Unknown error'}`
        );
        completeStreamingMessage(activeMessageIdRef.current);
        activeMessageIdRef.current = null;
      }
    }
  };

  return (
    <Card className="flex flex-col h-[600px] overflow-hidden">
      <div className="border-b px-4 py-3">
        <BackendStatus />
      </div>

      {streamError && (
        <div className="bg-destructive/10 border-l-4 border-destructive p-4 m-4">
          <div className="flex">
            <div className="ml-3">
              <p className="text-sm text-destructive">
                <strong>Connection Error:</strong> {streamError.message}
              </p>
            </div>
          </div>
        </div>
      )}

      <ScrollArea className="flex-1 p-4">
        <MessageList messages={messages} />
        <div ref={messagesEndRef} />
      </ScrollArea>

      <MessageInput
        value={input}
        onChange={setInput}
        onSend={handleSendMessage}
        disabled={isStreaming}
        placeholder={isStreaming ? "Waiting for response..." : "Type your message..."}
      />
    </Card>
  );
}
