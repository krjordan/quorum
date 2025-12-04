/**
 * TypingIndicator Component
 * Slack-style "Agent is typing..." indicator with animated dots
 */
'use client';

import { cn } from '@/lib/utils';

const AGENT_COLORS = [
  'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  'bg-green-500/10 text-green-700 dark:text-green-400',
  'bg-purple-500/10 text-purple-700 dark:text-purple-400',
  'bg-orange-500/10 text-orange-700 dark:text-orange-400',
];

interface TypingIndicatorProps {
  participantName: string;
  participantIndex: number;
  model: string;
}

export function TypingIndicator({
  participantName,
  participantIndex,
  model,
}: TypingIndicatorProps) {
  const colorClass = AGENT_COLORS[participantIndex % AGENT_COLORS.length];
  const bgClass = participantIndex % 2 === 0
    ? 'bg-muted/40'
    : 'bg-muted/20';

  return (
    <div className={cn(
      "px-4 py-3 border-b border-border",
      bgClass
    )}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
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
        <span className="text-xs text-muted-foreground px-2 py-0.5 rounded border border-border">
          {model}
        </span>
      </div>

      {/* Typing Animation */}
      <div className="ml-10 flex items-center gap-1">
        <span className="text-sm text-muted-foreground">typing</span>
        <div className="flex gap-1">
          <div className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}
