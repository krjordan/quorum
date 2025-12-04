/**
 * DebateThreadView Component
 * Main conversation view with flattened messages and auto-scroll
 */
'use client';

import { useEffect, useRef, useMemo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DebateMessageBubble } from './DebateMessageBubble';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';
import type { DebateMessage } from '@/types/debate-thread';

interface DebateThreadViewProps {
  debate: UseSequentialDebateReturn;
}

export function DebateThreadView({ debate }: DebateThreadViewProps) {
  const { context } = debate;
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Transform rounds array into flat message list
  const allMessages = useMemo<DebateMessage[]>(() => {
    const messages: DebateMessage[] = [];

    // Helper function to clean content by removing [Agent X]: prefix
    const cleanContent = (content: string, participantName: string): string => {
      // Remove patterns like "[Agent 1]:", "[Agent Name]:", etc.
      const prefixPattern = /^\[.*?\]:\s*/;
      return content.replace(prefixPattern, '').trim();
    };

    // Flatten all completed rounds
    context.rounds.forEach((round) => {
      console.log('[DebateThreadView] Processing round:', round.round_number, 'Responses:', round.responses.length);
      round.responses.forEach((response) => {
        console.log('[DebateThreadView] Adding completed message:', response.participant_name, 'Content length:', response.content.length);
        messages.push({
          id: `${round.round_number}-${response.participant_index}`,
          participantName: response.participant_name,
          participantIndex: response.participant_index,
          model: response.model,
          content: cleanContent(response.content, response.participant_name),
          tokens: response.tokens_used,
          responseTime: response.response_time_ms,
          timestamp: response.timestamp,
          roundNumber: round.round_number,
          isStreaming: false,
        });
      });
    });

    // Add current streaming message
    if (context.isStreaming && context.config) {
      const currentParticipant = context.config.participants[context.currentTurn];
      if (currentParticipant) {
        console.log('[DebateThreadView] Adding streaming message:', currentParticipant.name, 'Content length:', context.accumulatedText.length);
        messages.push({
          id: 'streaming',
          participantName: currentParticipant.name,
          participantIndex: context.currentTurn,
          model: currentParticipant.model,
          content: cleanContent(context.accumulatedText, currentParticipant.name),
          isStreaming: true,
        });
      }
    } else {
      console.log('[DebateThreadView] NOT adding streaming message. isStreaming:', context.isStreaming, 'hasConfig:', !!context.config);
    }

    console.log('[DebateThreadView] Total messages:', messages.length, 'Rounds:', context.rounds.length, 'isStreaming:', context.isStreaming);
    return messages;
  }, [context.rounds, context.isStreaming, context.accumulatedText, context.config, context.currentTurn]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [allMessages.length]);

  return (
    <ScrollArea className="h-full">
      <div className="min-h-full flex flex-col">
        {/* Empty State */}
        {allMessages.length === 0 && (
          <div className="flex-1 flex items-center justify-center text-center p-4">
            <div className="text-muted-foreground">
              <p className="text-lg font-medium mb-1">No messages yet</p>
              <p className="text-sm">The debate will appear here once started</p>
            </div>
          </div>
        )}

        {/* Messages - flush together with borders for separation */}
        {allMessages.map((message) => (
          <DebateMessageBubble key={message.id} message={message} />
        ))}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}
