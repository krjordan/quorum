/**
 * CitationTracker Component
 * Displays citations with verification status and source links
 */
'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { ExternalLink, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export type CitationStatus = 'verified' | 'unverified' | 'pending';

export interface Citation {
  id: string;
  text: string;
  source?: {
    title: string;
    url: string;
    author?: string;
  };
  status: CitationStatus;
  timestamp?: string;
}

interface CitationTrackerProps {
  citations: Citation[];
  className?: string;
}

export function CitationTracker({ citations, className }: CitationTrackerProps) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-2', className)}>
      {citations.map((citation) => (
        <CitationItem key={citation.id} citation={citation} />
      ))}
    </div>
  );
}

interface CitationItemProps {
  citation: Citation;
}

function CitationItem({ citation }: CitationItemProps) {
  const { text, source, status } = citation;

  // Status configuration
  const statusConfig = {
    verified: {
      icon: CheckCircle2,
      badge: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
      iconColor: 'text-green-500',
      label: 'Verified',
    },
    unverified: {
      icon: AlertCircle,
      badge: 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20',
      iconColor: 'text-orange-500',
      label: 'Unverified',
    },
    pending: {
      icon: Loader2,
      badge: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
      iconColor: 'text-blue-500',
      label: 'Checking...',
    },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;

  return (
    <div className="flex items-start gap-2 p-2 rounded-md bg-muted/30 border border-border/50">
      {/* Status Badge */}
      <Badge variant="outline" className={cn('text-xs flex items-center gap-1', config.badge)}>
        <StatusIcon
          className={cn('h-3 w-3', config.iconColor, status === 'pending' && 'animate-spin')}
        />
        {config.label}
      </Badge>

      {/* Citation Content */}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground italic leading-relaxed mb-1">
          &quot;{text}&quot;
        </p>

        {/* Source Information */}
        {source && (
          <div className="flex items-center gap-2 mt-1">
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
              >
                {source.title}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              <span className="text-xs font-medium">{source.title}</span>
            )}
            {source.author && (
              <span className="text-xs text-muted-foreground">by {source.author}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
