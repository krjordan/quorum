/**
 * ParticipantCard Component
 * Displays participant info in sidebar with active state
 */
'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const AGENT_COLORS = [
  'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
  'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
  'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20',
  'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20',
];

interface ParticipantCardProps {
  name: string;
  model: string;
  index: number;
  isActive: boolean;
}

export function ParticipantCard({ name, model, index, isActive }: ParticipantCardProps) {
  const colorClass = AGENT_COLORS[index % AGENT_COLORS.length];

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-2 rounded-lg border transition-all',
        isActive ? 'bg-primary/5 border-primary' : 'bg-card border-border'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded flex items-center justify-center text-sm font-semibold flex-shrink-0',
          colorClass
        )}
      >
        {name[0].toUpperCase()}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm truncate">{name}</div>
        <Badge variant="outline" className="text-xs mt-0.5">
          {model}
        </Badge>
      </div>

      {/* Active Indicator */}
      {isActive && (
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse flex-shrink-0" />
      )}
    </div>
  );
}
