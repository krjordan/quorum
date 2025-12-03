/**
 * Debate Controls Component
 * Pause, Resume, and Stop buttons for debate management
 * Displays current round and turn indicators
 */
'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Play, Pause, Square } from 'lucide-react';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';

interface DebateControlsProps {
  debate: UseSequentialDebateReturn;
}

export function DebateControls({ debate }: DebateControlsProps) {
  const {
    isRunning,
    isPaused,
    isCompleted,
    context,
    pauseDebate,
    resumeDebate,
    stopDebate,
  } = debate;

  const showControls = isRunning || isPaused;

  if (!showControls && !isCompleted) {
    return null;
  }

  const currentParticipant =
    context.config?.participants[context.currentTurn];

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        {/* Status and Progress */}
        <div className="flex items-center gap-4">
          {/* State Badge */}
          <Badge
            variant={
              isRunning ? 'default' : isPaused ? 'secondary' : 'outline'
            }
          >
            {isRunning && context.isStreaming && '⚡ Streaming'}
            {isRunning && !context.isStreaming && '🔄 Processing'}
            {isPaused && '⏸️ Paused'}
            {isCompleted && '✅ Completed'}
          </Badge>

          {/* Round Indicator */}
          {context.config && (
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">Round:</span> {context.currentRound}{' '}
              / {context.config.max_rounds}
            </div>
          )}

          {/* Turn Indicator */}
          {currentParticipant && !isCompleted && (
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">Current:</span>{' '}
              {currentParticipant.name}
            </div>
          )}

          {/* Cost Display */}
          <div className="text-sm text-muted-foreground">
            <span className="font-medium">Cost:</span> $
            {context.totalCost.toFixed(4)}
          </div>
        </div>

        {/* Control Buttons */}
        {!isCompleted && (
          <div className="flex items-center gap-2">
            {/* Pause/Resume */}
            {isRunning && (
              <Button
                variant="outline"
                size="sm"
                onClick={pauseDebate}
                disabled={context.isStreaming}
              >
                <Pause className="h-4 w-4 mr-2" />
                Pause
              </Button>
            )}

            {isPaused && (
              <Button variant="outline" size="sm" onClick={resumeDebate}>
                <Play className="h-4 w-4 mr-2" />
                Resume
              </Button>
            )}

            {/* Stop */}
            <Button
              variant="destructive"
              size="sm"
              onClick={stopDebate}
              disabled={context.isStreaming}
            >
              <Square className="h-4 w-4 mr-2" />
              Stop
            </Button>
          </div>
        )}
      </div>

      {/* Warning if approaching cost threshold */}
      {context.config &&
        context.totalCost >= context.config.cost_warning_threshold * 0.75 &&
        context.totalCost < context.config.cost_warning_threshold && (
          <div className="mt-2 text-sm text-amber-600">
            ⚠️ Approaching cost threshold ($
            {context.config.cost_warning_threshold.toFixed(2)})
          </div>
        )}

      {context.config &&
        context.totalCost >= context.config.cost_warning_threshold && (
          <div className="mt-2 text-sm text-red-600 font-medium">
            🚨 Cost threshold exceeded ($
            {context.config.cost_warning_threshold.toFixed(2)})
          </div>
        )}
    </Card>
  );
}
