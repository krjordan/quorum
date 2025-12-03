/**
 * Cost Tracker V2
 * Real-time cost tracking from XState machine context
 * Phase 2 implementation
 */
'use client';

import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';
import { AlertCircle, TrendingUp } from 'lucide-react';

interface CostTrackerV2Props {
  debate: UseSequentialDebateReturn;
}

export function CostTrackerV2({ debate }: CostTrackerV2Props) {
  const { context } = debate;

  if (!context.config) {
    return null;
  }

  const threshold = context.config.cost_warning_threshold || 1.0;
  const percentage = Math.min((context.totalCost / threshold) * 100, 100);
  const warningLevel =
    context.totalCost >= threshold
      ? 'critical'
      : context.totalCost >= threshold * 0.75
      ? 'warning'
      : 'normal';

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Cost Tracking</h3>
        {warningLevel === 'critical' && (
          <Badge variant="destructive" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            Over Threshold
          </Badge>
        )}
        {warningLevel === 'warning' && (
          <Badge variant="secondary" className="gap-1">
            <TrendingUp className="h-3 w-3" />
            Approaching Threshold
          </Badge>
        )}
      </div>

      {/* Total Cost */}
      <div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-3xl font-bold">
            ${context.totalCost.toFixed(4)}
          </span>
          <span className="text-sm text-muted-foreground">
            / ${threshold.toFixed(2)} threshold
          </span>
        </div>
        <Progress
          value={percentage}
          className={
            warningLevel === 'critical'
              ? '[&>div]:bg-destructive'
              : warningLevel === 'warning'
              ? '[&>div]:bg-amber-500'
              : ''
          }
        />
      </div>

      {/* Token Breakdown */}
      {Object.keys(context.totalTokens).length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Token Usage by Model</div>
          <div className="space-y-1">
            {Object.entries(context.totalTokens).map(([model, tokens]) => (
              <div
                key={model}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-muted-foreground">{model}:</span>
                <span className="font-mono">{tokens.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Round Cost (if available) */}
      {context.rounds.length > 0 && (
        <div className="border-t pt-3">
          <div className="text-sm font-medium mb-2">Cost per Round</div>
          <div className="space-y-1">
            {context.rounds.map((round) => (
              <div
                key={round.round_number}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-muted-foreground">
                  Round {round.round_number}:
                </span>
                <span className="font-mono">
                  ${round.cost_estimate.toFixed(4)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
