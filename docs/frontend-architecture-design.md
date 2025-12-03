# Quorum Frontend Architecture Design - Phase 1 Chat Interface

**Date:** November 30, 2025
**Author:** Analyst Agent (Hive Mind Swarm)
**Phase:** Phase 1 - Foundation & Chat Interface
**Status:** Design Complete

---

## Executive Summary

This document provides a comprehensive frontend architecture design for Quorum's Phase 1 chat interface, built with Next.js 15, React 19, and modern streaming technologies. The architecture prioritizes real-time streaming performance, clean separation of concerns, and scalability for future debate features.

**Key Technology Decisions:**
- **Framework:** Next.js 15 App Router with React 19 Server Components
- **State Management:** Zustand (primary) + TanStack Query (server state)
- **UI Components:** shadcn/ui + Tailwind CSS
- **Streaming:** Server-Sent Events (SSE) via FastAPI backend
- **Type Safety:** TypeScript strict mode throughout

---

## 1. Next.js 15 App Router Structure

### 1.1 Directory Structure

```
frontend/
├── app/
│   ├── (chat)/                          # Chat route group
│   │   ├── layout.tsx                   # Chat-specific layout
│   │   ├── page.tsx                     # Chat interface (main page)
│   │   └── loading.tsx                  # Streaming skeleton
│   │
│   ├── api/                             # Client-side API routes (optional)
│   │   └── health/
│   │       └── route.ts                 # Health check endpoint
│   │
│   ├── layout.tsx                       # Root layout
│   ├── page.tsx                         # Landing/redirect to chat
│   ├── globals.css                      # Global styles + Tailwind
│   ├── providers.tsx                    # Client-side providers wrapper
│   └── error.tsx                        # Global error boundary
│
├── components/
│   ├── ui/                              # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── scroll-area.tsx
│   │   ├── badge.tsx
│   │   ├── avatar.tsx
│   │   └── ...
│   │
│   ├── chat/
│   │   ├── ChatInterface.tsx            # Main chat container
│   │   ├── MessageList.tsx              # Virtualized message list
│   │   ├── MessageBubble.tsx            # Individual message component
│   │   ├── StreamingMessage.tsx         # Real-time streaming message
│   │   ├── MessageInput.tsx             # Text input with send button
│   │   ├── ParticipantIndicator.tsx     # Typing/streaming indicators
│   │   └── MessageTimestamp.tsx         # Timestamp display
│   │
│   └── providers/
│       └── StreamingProvider.tsx        # SSE connection context
│
├── lib/
│   ├── api/
│   │   ├── client.ts                    # API client configuration
│   │   └── endpoints.ts                 # API endpoint definitions
│   │
│   ├── streaming/
│   │   ├── sse-client.ts                # SSE connection manager
│   │   └── message-buffer.ts            # Message buffering logic
│   │
│   └── utils.ts                         # Utility functions
│
├── hooks/
│   ├── useStreamingText.ts              # Custom streaming hook
│   ├── useSSEConnection.ts              # SSE connection hook
│   ├── useMessageBuffer.ts              # Message buffering hook
│   └── useScrollToBottom.ts             # Auto-scroll behavior
│
├── stores/
│   ├── chat-store.ts                    # Zustand chat state
│   └── ui-store.ts                      # Zustand UI state
│
├── types/
│   ├── chat.ts                          # Chat type definitions
│   ├── message.ts                       # Message type definitions
│   └── api.ts                           # API type definitions
│
└── public/
    └── avatars/                         # User avatar images
```

### 1.2 App Router Configuration

**app/layout.tsx (Root Layout):**
```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Quorum - AI Debate Platform',
  description: 'Real-time multi-LLM debates',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
```

**app/providers.tsx (Client-Side Providers):**
```typescript
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        retry: 3,
        refetchOnWindowFocus: false,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**app/(chat)/page.tsx (Main Chat Interface):**
```typescript
import { ChatInterface } from '@/components/chat/ChatInterface';

export default function ChatPage() {
  return (
    <main className="flex h-screen flex-col">
      <ChatInterface />
    </main>
  );
}
```

---

## 2. Zustand Store Architecture

### 2.1 Chat Store Design

**stores/chat-store.ts:**
```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// Types
export interface Message {
  id: string;
  participantId: string;
  participantName: string;
  content: string;
  timestamp: number;
  isStreaming: boolean;
  metadata?: {
    model?: string;
    tokens?: number;
  };
}

export interface Participant {
  id: string;
  name: string;
  model: string;
  provider: string;
  color: string;
  status: 'idle' | 'typing' | 'streaming' | 'complete' | 'error';
}

interface ChatState {
  // State
  messages: Message[];
  participants: Record<string, Participant>;
  activeParticipantId: string | null;
  isConnected: boolean;
  connectionError: string | null;

  // Actions
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  updateStreamingContent: (id: string, content: string) => void;
  finalizeMessage: (id: string) => void;
  addParticipant: (participant: Participant) => void;
  updateParticipantStatus: (id: string, status: Participant['status']) => void;
  setActiveParticipant: (id: string | null) => void;
  setConnectionStatus: (connected: boolean, error?: string) => void;
  clearMessages: () => void;
  reset: () => void;
}

// Initial state
const initialState = {
  messages: [],
  participants: {},
  activeParticipantId: null,
  isConnected: false,
  connectionError: null,
};

// Store
export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      immer((set) => ({
        ...initialState,

        addMessage: (message) =>
          set((state) => {
            state.messages.push(message);
          }),

        updateMessage: (id, updates) =>
          set((state) => {
            const message = state.messages.find((m) => m.id === id);
            if (message) {
              Object.assign(message, updates);
            }
          }),

        updateStreamingContent: (id, content) =>
          set((state) => {
            const message = state.messages.find((m) => m.id === id);
            if (message) {
              message.content = content;
              message.isStreaming = true;
            }
          }),

        finalizeMessage: (id) =>
          set((state) => {
            const message = state.messages.find((m) => m.id === id);
            if (message) {
              message.isStreaming = false;
              message.timestamp = Date.now();
            }
          }),

        addParticipant: (participant) =>
          set((state) => {
            state.participants[participant.id] = participant;
          }),

        updateParticipantStatus: (id, status) =>
          set((state) => {
            if (state.participants[id]) {
              state.participants[id].status = status;
            }
          }),

        setActiveParticipant: (id) =>
          set((state) => {
            state.activeParticipantId = id;
          }),

        setConnectionStatus: (connected, error) =>
          set((state) => {
            state.isConnected = connected;
            state.connectionError = error || null;
          }),

        clearMessages: () =>
          set((state) => {
            state.messages = [];
          }),

        reset: () => set(initialState),
      })),
      {
        name: 'quorum-chat-storage',
        partialize: (state) => ({
          // Only persist participants, not messages
          participants: state.participants,
        }),
      }
    )
  )
);

// Selectors
export const selectMessages = (state: ChatState) => state.messages;
export const selectParticipants = (state: ChatState) => state.participants;
export const selectActiveParticipant = (state: ChatState) =>
  state.activeParticipantId
    ? state.participants[state.activeParticipantId]
    : null;
export const selectIsConnected = (state: ChatState) => state.isConnected;
```

### 2.2 UI Store Design

**stores/ui-store.ts:**
```typescript
import { create } from 'zustand';

interface UIState {
  // State
  isSidebarOpen: boolean;
  isMessageInputFocused: boolean;
  showScrollToBottom: boolean;

  // Actions
  toggleSidebar: () => void;
  setMessageInputFocused: (focused: boolean) => void;
  setShowScrollToBottom: (show: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isSidebarOpen: true,
  isMessageInputFocused: false,
  showScrollToBottom: false,

  toggleSidebar: () =>
    set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  setMessageInputFocused: (focused) =>
    set({ isMessageInputFocused: focused }),

  setShowScrollToBottom: (show) =>
    set({ showScrollToBottom: show }),
}));
```

---

## 3. SSE Client Implementation

### 3.1 SSE Connection Manager

**lib/streaming/sse-client.ts:**
```typescript
export interface SSEConnectionOptions {
  endpoint: string;
  onMessage: (data: any) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private options: Required<SSEConnectionOptions>;

  constructor(options: SSEConnectionOptions) {
    this.options = {
      onError: () => {},
      onOpen: () => {},
      onClose: () => {},
      reconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      ...options,
    };
  }

  connect(): void {
    try {
      this.eventSource = new EventSource(this.options.endpoint);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.options.onOpen();
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.options.onMessage(data);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };

      this.eventSource.onerror = (error) => {
        this.handleError(error);
      };

      // Custom event listeners
      this.eventSource.addEventListener('chunk', (event: any) => {
        try {
          const data = JSON.parse(event.data);
          this.options.onMessage({ type: 'chunk', ...data });
        } catch (error) {
          console.error('Failed to parse chunk event:', error);
        }
      });

      this.eventSource.addEventListener('done', () => {
        this.options.onMessage({ type: 'done' });
        this.disconnect();
      });

    } catch (error) {
      this.handleError(error as Error);
    }
  }

  private handleError(error: Error | Event): void {
    const err = error instanceof Error ? error : new Error('SSE connection error');
    this.options.onError(err);

    if (this.options.reconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
      this.reconnect();
    } else {
      this.disconnect();
    }
  }

  private reconnect(): void {
    this.reconnectAttempts++;
    console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      this.disconnect();
      this.connect();
    }, this.options.reconnectInterval * this.reconnectAttempts);
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.options.onClose();
    }
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }
}
```

### 3.2 Custom Streaming Hook

**hooks/useStreamingText.ts:**
```typescript
import { useState, useEffect, useRef } from 'react';
import { SSEClient } from '@/lib/streaming/sse-client';

export interface UseStreamingTextOptions {
  endpoint: string | null;
  onComplete?: (content: string) => void;
  onError?: (error: Error) => void;
  bufferDelay?: number;
}

export function useStreamingText(options: UseStreamingTextOptions) {
  const { endpoint, onComplete, onError, bufferDelay = 50 } = options;

  const [displayedText, setDisplayedText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const bufferRef = useRef('');
  const clientRef = useRef<SSEClient | null>(null);
  const updateTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Flush buffer to displayed text periodically
  useEffect(() => {
    if (!isStreaming) return;

    updateTimerRef.current = setInterval(() => {
      if (bufferRef.current) {
        setDisplayedText(bufferRef.current);
      }
    }, bufferDelay);

    return () => {
      if (updateTimerRef.current) {
        clearInterval(updateTimerRef.current);
      }
    };
  }, [isStreaming, bufferDelay]);

  // Manage SSE connection
  useEffect(() => {
    if (!endpoint) return;

    const client = new SSEClient({
      endpoint,
      onMessage: (data) => {
        if (data.type === 'chunk') {
          bufferRef.current += data.content || '';
        } else if (data.type === 'done') {
          setDisplayedText(bufferRef.current);
          setIsStreaming(false);
          onComplete?.(bufferRef.current);
        }
      },
      onOpen: () => {
        setIsStreaming(true);
        setError(null);
      },
      onError: (err) => {
        setError(err);
        setIsStreaming(false);
        onError?.(err);
      },
      onClose: () => {
        setIsStreaming(false);
      },
    });

    client.connect();
    clientRef.current = client;

    return () => {
      client.disconnect();
    };
  }, [endpoint, onComplete, onError]);

  const reset = () => {
    bufferRef.current = '';
    setDisplayedText('');
    setError(null);
  };

  return {
    displayedText,
    isStreaming,
    error,
    reset,
  };
}
```

---

## 4. React Component Hierarchy

### 4.1 Main Chat Interface

**components/chat/ChatInterface.tsx:**
```typescript
'use client';

import { useChatStore } from '@/stores/chat-store';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ParticipantIndicator } from './ParticipantIndicator';

export function ChatInterface() {
  const participants = useChatStore((state) => state.participants);
  const isConnected = useChatStore((state) => state.isConnected);
  const connectionError = useChatStore((state) => state.connectionError);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="border-b bg-white p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Quorum Chat</h1>
          <div className="flex items-center gap-2">
            {Object.values(participants).map((participant) => (
              <ParticipantIndicator key={participant.id} participant={participant} />
            ))}
          </div>
        </div>
        {!isConnected && connectionError && (
          <div className="mt-2 rounded bg-red-50 p-2 text-sm text-red-600">
            Connection error: {connectionError}
          </div>
        )}
      </header>

      {/* Message List */}
      <MessageList />

      {/* Input Area */}
      <MessageInput />
    </div>
  );
}
```

### 4.2 Message List with Virtualization

**components/chat/MessageList.tsx:**
```typescript
'use client';

import { useRef, useEffect } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useChatStore } from '@/stores/chat-store';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useScrollToBottom } from '@/hooks/useScrollToBottom';

export function MessageList() {
  const messages = useChatStore((state) => state.messages);
  const parentRef = useRef<HTMLDivElement>(null);

  const { shouldAutoScroll, scrollToBottom } = useScrollToBottom(parentRef);

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
    overscan: 5,
  });

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (shouldAutoScroll) {
      scrollToBottom();
    }
  }, [messages.length, shouldAutoScroll, scrollToBottom]);

  return (
    <ScrollArea ref={parentRef} className="flex-1 p-4">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const message = messages[virtualItem.index];

          return (
            <div
              key={virtualItem.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {message.isStreaming ? (
                <StreamingMessage message={message} />
              ) : (
                <MessageBubble message={message} />
              )}
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
```

### 4.3 Streaming Message Component

**components/chat/StreamingMessage.tsx:**
```typescript
'use client';

import { useChatStore } from '@/stores/chat-store';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface StreamingMessageProps {
  message: {
    id: string;
    participantId: string;
    participantName: string;
    content: string;
  };
}

export function StreamingMessage({ message }: StreamingMessageProps) {
  const participant = useChatStore(
    (state) => state.participants[message.participantId]
  );

  if (!participant) return null;

  return (
    <div className="mb-4 flex items-start gap-3">
      <Avatar className={cn('border-2', `border-${participant.color}-500`)}>
        <AvatarFallback className={`bg-${participant.color}-100 text-${participant.color}-700`}>
          {participant.name[0]}
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{participant.name}</span>
          <Badge variant="outline" className="text-xs">
            {participant.model}
          </Badge>
        </div>

        <div className="rounded-lg bg-gray-50 p-3">
          <div className="whitespace-pre-wrap">
            {message.content}
            <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-gray-900" />
          </div>
        </div>
      </div>
    </div>
  );
}
```

### 4.4 Message Input Component

**components/chat/MessageInput.tsx:**
```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send } from 'lucide-react';
import { useChatStore } from '@/stores/chat-store';

export function MessageInput() {
  const [message, setMessage] = useState('');
  const isConnected = useChatStore((state) => state.isConnected);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !isConnected) return;

    // Send message to backend
    try {
      const response = await fetch('http://localhost:8000/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: message }),
      });

      if (response.ok) {
        setMessage('');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <footer className="border-t bg-white p-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={isConnected ? "Type a message..." : "Connecting..."}
          disabled={!isConnected}
          className="flex-1"
        />
        <Button type="submit" disabled={!message.trim() || !isConnected}>
          <Send className="h-4 w-4" />
          <span className="sr-only">Send message</span>
        </Button>
      </form>
    </footer>
  );
}
```

---

## 5. shadcn/ui Components Needed

### 5.1 Core Components List

**Install via shadcn/ui CLI:**

```bash
# UI primitives
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add card
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add avatar
npx shadcn-ui@latest add scroll-area

# Layout components
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add sheet

# Feedback components
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add alert

# Form components (for future settings)
npx shadcn-ui@latest add select
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add dialog
```

### 5.2 Custom Component Variants

**components/ui/message-bubble.tsx (Custom):**
```typescript
import * as React from 'react';
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const messageBubbleVariants = cva(
  'rounded-lg p-3 max-w-[80%]',
  {
    variants: {
      variant: {
        sent: 'bg-blue-500 text-white ml-auto',
        received: 'bg-gray-100 text-gray-900',
        system: 'bg-yellow-50 text-yellow-900 border border-yellow-200',
      },
    },
    defaultVariants: {
      variant: 'received',
    },
  }
);

export interface MessageBubbleProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof messageBubbleVariants> {}

const MessageBubble = React.forwardRef<HTMLDivElement, MessageBubbleProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(messageBubbleVariants({ variant }), className)}
        {...props}
      />
    );
  }
);
MessageBubble.displayName = 'MessageBubble';

export { MessageBubble, messageBubbleVariants };
```

---

## 6. State Management Flow

### 6.1 Message Flow Diagram

```
User sends message
       │
       ▼
MessageInput component
       │
       ▼
POST /api/chat/send
       │
       ▼
Backend processes & starts SSE stream
       │
       ▼
SSE Client receives chunks
       │
       ▼
useStreamingText hook buffers content
       │
       ▼
Zustand store updates message state
       │
       ▼
MessageList re-renders with new content
       │
       ▼
Auto-scroll to bottom (if user at bottom)
       │
       ▼
Stream completes → finalizeMessage()
```

### 6.2 Connection State Management

```typescript
// stores/chat-store.ts - Connection state flow

// 1. Initial connection attempt
setConnectionStatus(false, null);

// 2. SSE client opens connection
onOpen: () => {
  setConnectionStatus(true, null);
}

// 3. Error occurs
onError: (error) => {
  setConnectionStatus(false, error.message);
}

// 4. Reconnection attempts
// SSEClient handles retry logic internally

// 5. Connection closed
onClose: () => {
  setConnectionStatus(false, 'Connection closed');
}
```

---

## 7. Integration with Backend

### 7.1 API Client Configuration

**lib/api/client.ts:**
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = {
  async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  },

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  },

  getSSEEndpoint(path: string): string {
    return `${API_BASE_URL}${path}`;
  },
};
```

### 7.2 Backend API Endpoints

**Expected FastAPI endpoints:**

```python
# POST /api/chat/send
# Start a new chat message, returns SSE endpoint for streaming

# GET /api/chat/stream/{message_id}
# SSE endpoint for streaming LLM response

# GET /api/chat/history
# Get message history (for initial load)

# POST /api/chat/clear
# Clear chat history
```

---

## 8. Performance Optimizations

### 8.1 Code Splitting Strategy

```typescript
// app/(chat)/page.tsx
import dynamic from 'next/dynamic';

// Lazy load heavy components
const MessageList = dynamic(() => import('@/components/chat/MessageList'), {
  loading: () => <MessageListSkeleton />,
  ssr: false, // Client-side only
});

const MessageInput = dynamic(() => import('@/components/chat/MessageInput'));
```

### 8.2 Memoization Strategy

```typescript
// components/chat/MessageBubble.tsx
import { memo } from 'react';

export const MessageBubble = memo(
  ({ message }: MessageBubbleProps) => {
    // Component implementation
  },
  (prev, next) => {
    // Only re-render if message content or id changes
    return prev.message.id === next.message.id &&
           prev.message.content === next.message.content;
  }
);
```

### 8.3 Virtual Scrolling Configuration

```typescript
// Optimized virtualizer config for chat
const virtualizer = useVirtualizer({
  count: messages.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 100,        // Average message height
  overscan: 5,                     // Render 5 extra messages
  scrollMargin: parentRef.current?.offsetTop ?? 0,
  gap: 8,                          // Gap between messages
});
```

---

## 9. TypeScript Type Definitions

### 9.1 Core Types

**types/chat.ts:**
```typescript
export type ParticipantStatus =
  | 'idle'
  | 'typing'
  | 'streaming'
  | 'complete'
  | 'error';

export type MessageType = 'user' | 'assistant' | 'system';

export interface Participant {
  id: string;
  name: string;
  model: string;
  provider: 'anthropic' | 'openai' | 'google' | 'mistral';
  color: string;
  status: ParticipantStatus;
  avatar?: string;
}

export interface Message {
  id: string;
  participantId: string;
  participantName: string;
  type: MessageType;
  content: string;
  timestamp: number;
  isStreaming: boolean;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  model?: string;
  tokens?: {
    prompt: number;
    completion: number;
    total: number;
  };
  duration?: number;
  error?: string;
}
```

**types/api.ts:**
```typescript
export interface SendMessageRequest {
  content: string;
  participantId?: string;
}

export interface SendMessageResponse {
  messageId: string;
  streamEndpoint: string;
}

export interface SSEChunkData {
  type: 'chunk' | 'done' | 'error';
  content?: string;
  error?: string;
  metadata?: Record<string, any>;
}
```

---

## 10. Environment Configuration

### 10.1 Environment Variables

**.env.local:**
```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature flags
NEXT_PUBLIC_ENABLE_VIRTUAL_SCROLL=true
NEXT_PUBLIC_MESSAGE_BUFFER_DELAY=50

# Development
NODE_ENV=development
```

### 10.2 Next.js Configuration

**next.config.js:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Optimize for production
  swcMinify: true,

  // Image optimization (for avatars)
  images: {
    domains: ['localhost'],
  },

  // Experimental features
  experimental: {
    serverActions: true,
  },
};

module.exports = nextConfig;
```

---

## 11. Testing Strategy

### 11.1 Component Testing

```typescript
// __tests__/components/MessageBubble.test.tsx
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '@/components/chat/MessageBubble';

describe('MessageBubble', () => {
  it('renders message content', () => {
    const message = {
      id: '1',
      participantId: 'p1',
      participantName: 'Claude',
      content: 'Hello world',
      timestamp: Date.now(),
      isStreaming: false,
    };

    render(<MessageBubble message={message} />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });
});
```

### 11.2 Store Testing

```typescript
// __tests__/stores/chat-store.test.ts
import { renderHook, act } from '@testing-library/react';
import { useChatStore } from '@/stores/chat-store';

describe('useChatStore', () => {
  it('adds message', () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.addMessage({
        id: '1',
        participantId: 'p1',
        participantName: 'Claude',
        content: 'Test',
        timestamp: Date.now(),
        isStreaming: false,
      });
    });

    expect(result.current.messages).toHaveLength(1);
  });
});
```

---

## 12. Deployment Configuration

### 12.1 Docker Configuration

**frontend/Dockerfile:**
```dockerfile
FROM node:20-alpine AS base

# Dependencies
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Builder
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# Runner
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

### 12.2 Docker Compose Integration

**docker-compose.yml (Root):**
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - quorum-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - quorum-network

networks:
  quorum-network:
    driver: bridge
```

---

## 13. Development Workflow

### 13.1 Package Scripts

**package.json:**
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch",
    "format": "prettier --write \"**/*.{ts,tsx,json,md}\""
  }
}
```

### 13.2 Development Setup Steps

```bash
# 1. Clone repository
git clone <repo-url>
cd quorum/frontend

# 2. Install dependencies
npm install

# 3. Set up environment
cp .env.example .env.local
# Edit .env.local with backend URL

# 4. Start development server
npm run dev

# 5. Backend should be running on localhost:8000
# Frontend runs on localhost:3000
```

---

## 14. Future Enhancements (Post-Phase 1)

### 14.1 Planned Features

1. **Multi-participant debates**
   - Extend to 2-4 simultaneous participants
   - Color-coded messages
   - Participant indicators

2. **Message reactions**
   - Like/dislike messages
   - Custom emoji reactions

3. **Search functionality**
   - Full-text search in message history
   - Filter by participant

4. **Export functionality**
   - Export chat as Markdown
   - Export as JSON

5. **Settings panel**
   - API key management
   - Theme customization
   - Notification preferences

### 14.2 Technical Debt Items

1. Add comprehensive error boundaries
2. Implement retry logic with exponential backoff
3. Add message persistence (IndexedDB)
4. Optimize bundle size analysis
5. Add E2E tests with Playwright

---

## 15. Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Next.js 15 App Router | Server components, streaming support, modern React features |
| State Management | Zustand | Lightweight, TypeScript-first, minimal boilerplate |
| Server State | TanStack Query | Industry standard, built-in caching and retry logic |
| UI Components | shadcn/ui | Copy-paste components, full customization, Radix UI primitives |
| Styling | Tailwind CSS | Utility-first, rapid development, excellent Next.js integration |
| Streaming | SSE (EventSource) | One-way communication, automatic reconnection, native browser API |
| Virtualization | TanStack Virtual | Handles long message lists efficiently |
| Type Safety | TypeScript strict | Catch errors at compile time, better DX |

---

## 16. Dependencies

### 16.1 Production Dependencies

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-virtual": "^3.0.0",
    "zustand": "^4.4.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.294.0"
  }
}
```

### 16.2 Development Dependencies

```json
{
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "^14.0.0",
    "prettier": "^3.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "jest": "^29.0.0",
    "jest-environment-jsdom": "^29.0.0"
  }
}
```

---

## 17. Success Metrics

### 17.1 Performance Targets

- **Time to Interactive (TTI):** < 2s
- **First Contentful Paint (FCP):** < 1s
- **Streaming latency:** First token < 500ms
- **Message render time:** < 16ms (60 FPS)
- **Bundle size:** < 200KB (gzipped)

### 17.2 Quality Metrics

- **Type coverage:** 100%
- **Test coverage:** > 80%
- **Accessibility:** WCAG 2.2 AA compliant
- **Browser support:** Chrome, Firefox, Safari, Edge (latest 2 versions)

---

## Conclusion

This frontend architecture provides a solid foundation for Quorum's Phase 1 chat interface. The design prioritizes:

1. **Performance** - SSE streaming, virtual scrolling, optimized rendering
2. **Developer Experience** - TypeScript, modular components, clear separation of concerns
3. **Scalability** - Easy to extend for future debate features
4. **Maintainability** - Well-documented, tested, and follows best practices

**Next Steps:**
1. Review and approve this architecture
2. Set up development environment
3. Implement core components (Week 1-2)
4. Integrate with backend SSE endpoints (Week 2-3)
5. Add polish and testing (Week 3-4)

---

**Document Version:** 1.0
**Last Updated:** November 30, 2025
**Author:** Analyst Agent (Hive Mind Swarm)
