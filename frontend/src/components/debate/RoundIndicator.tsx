/**
 * RoundIndicator Component
 * Shows current round progress with visual indicator
 */
'use client';

import { Progress } from '@/components/ui/progress';

interface RoundIndicatorProps {
  current: number;
  max: number;
}

export function RoundIndicator({ current, max }: RoundIndicatorProps) {
  const progress = max > 0 ? (current / max) * 100 : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">Round Progress</span>
        <span className="text-muted-foreground">
          {current} / {max}
        </span>
      </div>
      <Progress value={progress} className="h-2" />
    </div>
  );
}
