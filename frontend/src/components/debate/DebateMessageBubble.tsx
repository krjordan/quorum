/**
 * DebateMessageBubble Component
 * Slack-style message display with agent colors and metadata
 */
'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { DebateMessage } from '@/types/debate-thread';
import { memo } from 'react';

const AGENT_COLORS = [
  'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  'bg-green-500/10 text-green-700 dark:text-green-400',
  'bg-purple-500/10 text-purple-700 dark:text-purple-400',
  'bg-orange-500/10 text-orange-700 dark:text-orange-400',
];

interface DebateMessageBubbleProps {
  message: DebateMessage;
}

function formatTime(timestamp?: string): string {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function DebateMessageBubbleComponent({ message }: DebateMessageBubbleProps) {
  const {
    participantName,
    participantIndex,
    model,
    content,
    tokens,
    responseTime,
    timestamp,
    isStreaming,
  } = message;

  const colorClass = AGENT_COLORS[participantIndex % AGENT_COLORS.length];

  // Subtle alternating background colors for better separation
  const bgClass = participantIndex % 2 === 0
    ? 'bg-muted/20 hover:bg-muted/40'
    : 'bg-muted/10 hover:bg-muted/30';

  return (
    <div className={cn(
      "group rounded-lg px-4 py-3 transition-colors border-b border-border/50",
      bgClass
    )}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        {/* Avatar */}
        <div
          className={cn(
            'w-8 h-8 rounded flex items-center justify-center text-sm font-semibold',
            colorClass
          )}
        >
          {participantName[0].toUpperCase()}
        </div>

        {/* Name */}
        <span className="font-semibold text-sm">{participantName}</span>

        {/* Model Badge */}
        <Badge variant="outline" className="text-xs">
          {model}
        </Badge>

        {/* Timestamp */}
        {timestamp && (
          <span className="text-xs text-muted-foreground ml-auto">
            {formatTime(timestamp)}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="ml-10 text-sm whitespace-pre-wrap break-words">
        {content}
        {isStreaming && (
          <span className="inline-block w-0.5 h-4 bg-primary animate-pulse ml-1 align-middle" />
        )}
      </div>

      {/* Metadata (on hover) */}
      {(tokens !== undefined || responseTime !== undefined) && (
        <div className="ml-10 mt-1 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          {tokens !== undefined && `${tokens.toLocaleString()} tokens`}
          {tokens !== undefined && responseTime !== undefined && ' • '}
          {responseTime !== undefined && `${responseTime.toFixed(0)}ms`}
        </div>
      )}
    </div>
  );
}

// Memoize to prevent re-renders on rapid streaming
export const DebateMessageBubble = memo(DebateMessageBubbleComponent);
