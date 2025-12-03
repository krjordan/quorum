export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentStreamingMessageId: string | null;
  addMessage: (message: Omit<Message, "id" | "timestamp">) => string;
  updateStreamingMessage: (id: string, content: string) => void;
  completeStreamingMessage: (id: string) => void;
  clearMessages: () => void;
}

export interface ChatRequest {
  message: string;
  conversationHistory?: Message[];
}

export interface StreamChunk {
  id: string;
  content: string;
  done: boolean;
}
