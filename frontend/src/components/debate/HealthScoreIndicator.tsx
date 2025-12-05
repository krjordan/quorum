/**
 * HealthScoreIndicator Component
 * Displays conversation health score with circular progress and trend indicator
 */
'use client';

import { useMemo } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

export interface HealthScore {
  score: number; // 0-100
  trend?: 'improving' | 'stable' | 'declining';
  lastUpdate?: string;
  recommendation?: string;
}

interface HealthScoreIndicatorProps {
  healthScore: HealthScore;
  className?: string;
}

export function HealthScoreIndicator({ healthScore, className }: HealthScoreIndicatorProps) {
  const { score, trend, recommendation } = healthScore;

  // Determine color and status text based on score
  const { color, bgColor, textColor, status } = useMemo(() => {
    if (score >= 80) {
      return {
        color: 'stroke-green-500',
        bgColor: 'bg-green-500/10',
        textColor: 'text-green-700 dark:text-green-400',
        status: 'Excellent',
      };
    } else if (score >= 60) {
      return {
        color: 'stroke-blue-500',
        bgColor: 'bg-blue-500/10',
        textColor: 'text-blue-700 dark:text-blue-400',
        status: 'Good',
      };
    } else if (score >= 40) {
      return {
        color: 'stroke-yellow-500',
        bgColor: 'bg-yellow-500/10',
        textColor: 'text-yellow-700 dark:text-yellow-400',
        status: 'Fair',
      };
    } else if (score >= 20) {
      return {
        color: 'stroke-orange-500',
        bgColor: 'bg-orange-500/10',
        textColor: 'text-orange-700 dark:text-orange-400',
        status: 'Poor',
      };
    } else {
      return {
        color: 'stroke-red-500',
        bgColor: 'bg-red-500/10',
        textColor: 'text-red-700 dark:text-red-400',
        status: 'Critical',
      };
    }
  }, [score]);

  // Trend icon
  const TrendIcon = useMemo(() => {
    if (trend === 'improving') return TrendingUp;
    if (trend === 'declining') return TrendingDown;
    return Minus;
  }, [trend]);

  const trendColor = useMemo(() => {
    if (trend === 'improving') return 'text-green-500';
    if (trend === 'declining') return 'text-red-500';
    return 'text-muted-foreground';
  }, [trend]);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('flex items-center gap-3 p-3 rounded-lg border', bgColor, className)}>
            {/* Circular Progress */}
            <div className="relative w-16 h-16 flex-shrink-0">
              {/* Background circle */}
              <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 64 64">
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                  className="text-muted/20"
                />
                {/* Progress circle */}
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                  strokeDasharray={`${(score / 100) * 176} 176`}
                  className={cn(color, 'transition-all duration-500')}
                  strokeLinecap="round"
                />
              </svg>
              {/* Score text */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={cn('text-lg font-bold', textColor)}>{score}</span>
              </div>
            </div>

            {/* Status and Trend */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={cn('text-sm font-semibold', textColor)}>{status}</span>
                {trend && (
                  <TrendIcon className={cn('w-4 h-4', trendColor)} aria-label={`Trend: ${trend}`} />
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Conversation Health</p>
              {score < 40 && (
                <div className="flex items-center gap-1 mt-1">
                  <AlertTriangle className="w-3 h-3 text-orange-500" />
                  <span className="text-xs text-orange-600 dark:text-orange-400">Needs attention</span>
                </div>
              )}
            </div>
          </div>
        </TooltipTrigger>
        {recommendation && (
          <TooltipContent side="bottom" className="max-w-xs">
            <p className="text-sm">{recommendation}</p>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}
