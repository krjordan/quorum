/**
 * Type definitions for debate thread view
 * Used by DebateThreadView and DebateMessageBubble components
 */

import type { Citation, Contradiction } from './conversation-quality';

export interface DebateMessage {
  id: string;
  participantName: string;
  participantIndex: number;
  model: string;
  content: string;
  tokens?: number;
  responseTime?: number;
  timestamp?: string;
  roundNumber?: number;
  isStreaming: boolean;
  // Quality metadata
  citations?: Citation[];
  contradictions?: Contradiction[];
}

export interface DebateThread {
  messages: DebateMessage[];
  totalMessages: number;
  isEmpty: boolean;
}
