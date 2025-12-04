/**
 * DebateStatsSidebar Component
 * Left sidebar with stats, participants, and control buttons
 */
'use client';

import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { StatSection } from './StatSection';
import { RoundIndicator } from './RoundIndicator';
import { ParticipantCard } from './ParticipantCard';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';
import { Pause, Play, Square } from 'lucide-react';

interface DebateStatsSidebarProps {
  debate: UseSequentialDebateReturn;
}

function getStateBadge(stateValue: string) {
  switch (stateValue) {
    case 'running':
      return <Badge className="bg-green-500">Running</Badge>;
    case 'paused':
      return <Badge className="bg-yellow-500">Paused</Badge>;
    case 'completed':
      return <Badge className="bg-blue-500">Completed</Badge>;
    case 'error':
      return <Badge variant="destructive">Error</Badge>;
    default:
      return <Badge variant="outline">{stateValue}</Badge>;
  }
}

export function DebateStatsSidebar({ debate }: DebateStatsSidebarProps) {
  const {
    context,
    stateValue,
    isRunning,
    isPaused,
    isCompleted,
    pauseDebate,
    resumeDebate,
    stopDebate,
  } = debate;

  const totalCost = context.totalCost || 0;
  const totalTokens = context.totalTokens || 0;
  const currentRound = context.currentRound || 0;
  const maxRounds = context.config?.max_rounds || 0;
  const costThreshold = context.config?.cost_warning_threshold || 1.0;
  const costPercent = (totalCost / costThreshold) * 100;

  return (
    <div className="h-full flex flex-col bg-muted/30">
      {/* Header - Fixed */}
      <div className="p-4 border-b bg-background/50">
        <h2 className="text-lg font-bold mb-2">Debate Stats</h2>
        {getStateBadge(stateValue)}
      </div>

      {/* Scrollable Stats */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Progress Section */}
          {context.config && (
            <StatSection title="Progress">
              <RoundIndicator current={currentRound} max={maxRounds} />
              {isRunning && context.config.participants[context.currentTurn] && (
                <div className="text-sm text-muted-foreground mt-2">
                  Current turn:{' '}
                  <span className="font-medium text-foreground">
                    {context.config.participants[context.currentTurn].name}
                  </span>
                </div>
              )}
            </StatSection>
          )}

          {/* Cost Section */}
          <StatSection title="Cost Tracking">
            <div className="space-y-2">
              <div className="flex items-baseline gap-2">
                <div className="text-3xl font-bold">${totalCost.toFixed(4)}</div>
                <div className="text-xs text-muted-foreground">
                  / ${costThreshold.toFixed(2)}
                </div>
              </div>
              <Progress
                value={Math.min(costPercent, 100)}
                className={costPercent > 100 ? 'bg-red-500/20' : 'bg-primary/20'}
              />
              {costPercent > 80 && (
                <Badge variant={costPercent > 100 ? 'destructive' : 'default'} className="text-xs">
                  {costPercent > 100 ? 'Over Threshold' : 'Approaching Threshold'}
                </Badge>
              )}
            </div>
          </StatSection>

          {/* Token Usage */}
          <StatSection title="Token Usage">
            <div className="text-sm">
              <span className="font-medium">{totalTokens.toLocaleString()}</span>
              <span className="text-muted-foreground ml-1">tokens</span>
            </div>
          </StatSection>

          {/* Participants Section */}
          {context.config && context.config.participants.length > 0 && (
            <StatSection title="Participants">
              {context.config.participants.map((participant, index) => (
                <ParticipantCard
                  key={index}
                  name={participant.name}
                  model={participant.model}
                  index={index}
                  isActive={isRunning && index === context.currentTurn}
                />
              ))}
            </StatSection>
          )}

          {/* Round Costs */}
          {context.rounds.length > 0 && (
            <StatSection title="Round Costs">
              <div className="space-y-1">
                {context.rounds.map((round) => (
                  <div
                    key={round.round_number}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted-foreground">
                      Round {round.round_number}
                    </span>
                    <span className="font-medium">
                      ${round.cost_estimate.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            </StatSection>
          )}
        </div>
      </ScrollArea>

      {/* Control Buttons - Fixed Bottom */}
      <div className="p-4 border-t bg-background/50 space-y-2">
        {isPaused ? (
          <Button onClick={resumeDebate} className="w-full" size="sm">
            <Play className="h-4 w-4 mr-2" />
            Resume
          </Button>
        ) : (
          <Button
            onClick={pauseDebate}
            disabled={!isRunning}
            variant="outline"
            className="w-full"
            size="sm"
          >
            <Pause className="h-4 w-4 mr-2" />
            Pause
          </Button>
        )}

        <Button
          onClick={stopDebate}
          disabled={!isRunning && !isPaused}
          variant="destructive"
          className="w-full"
          size="sm"
        >
          <Square className="h-4 w-4 mr-2" />
          Stop Debate
        </Button>
      </div>
    </div>
  );
}
