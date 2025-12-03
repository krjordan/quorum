/**
 * Debate Arena V2
 * Sequential turn-based debate visualization
 * Shows current speaker streaming, previous responses, and turn order
 */
'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';
import { Loader2 } from 'lucide-react';

interface DebateArenaV2Props {
  debate: UseSequentialDebateReturn;
}

export function DebateArenaV2({ debate }: DebateArenaV2Props) {
  const { context, isRunning, isCompleted } = debate;

  if (!context.config) {
    return null;
  }

  const currentParticipant = context.config.participants[context.currentTurn];

  return (
    <div className="space-y-4">
      {/* Current Turn Indicator */}
      {isRunning && currentParticipant && context.isStreaming && (
        <Card className="p-4 bg-primary/5 border-primary">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="font-medium text-primary">
              {currentParticipant.name} is responding...
            </span>
            <Badge variant="outline">{currentParticipant.model}</Badge>
          </div>
          <div className="text-sm whitespace-pre-wrap">
            {context.accumulatedText}
            <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
          </div>
        </Card>
      )}

      {/* Debate Rounds */}
      <ScrollArea className="h-[600px]">
        <div className="space-y-6">
          {context.rounds.map((round) => (
            <div key={round.round_number} className="space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">Round {round.round_number}</h3>
                <Badge variant="secondary">
                  ${round.cost_estimate.toFixed(4)}
                </Badge>
              </div>

              {/* Responses in sequential order */}
              <div className="space-y-3">
                {round.responses.map((response) => (
                  <Card
                    key={response.participant_index}
                    className="p-4"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {response.participant_name}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {response.model}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {response.tokens_used} tokens •{' '}
                        {response.response_time_ms.toFixed(0)}ms
                      </div>
                    </div>
                    <div className="text-sm whitespace-pre-wrap">
                      {response.content}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}

          {/* Waiting for next participant (if not streaming) */}
          {isRunning && !context.isStreaming && currentParticipant && (
            <Card className="p-4 bg-muted/50">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">
                  Waiting for {currentParticipant.name}...
                </span>
              </div>
            </Card>
          )}

          {/* Completed State */}
          {isCompleted && (
            <Card className="p-4 bg-green-500/10 border-green-500">
              <div className="text-center text-green-700 dark:text-green-400">
                ✅ Debate Completed
              </div>
            </Card>
          )}
        </div>
      </ScrollArea>

      {/* Turn Order Indicator */}
      {context.config && !isCompleted && (
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-2">Turn Order:</div>
          <div className="flex gap-2">
            {context.config.participants.map((participant, index) => (
              <Badge
                key={index}
                variant={index === context.currentTurn ? 'default' : 'outline'}
                className="text-xs"
              >
                {participant.name}
              </Badge>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
