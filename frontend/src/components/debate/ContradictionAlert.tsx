/**
 * ContradictionAlert Component
 * Displays detected contradictions with severity and resolution actions
 */
'use client';

import { useState } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { AlertTriangle, ChevronDown, ChevronUp, X, MessageSquare } from 'lucide-react';

export type ContradictionSeverity = 'high' | 'medium' | 'low';

export interface Contradiction {
  id: string;
  severity: ContradictionSeverity;
  statement1: {
    participantName: string;
    content: string;
    messageId: string;
  };
  statement2: {
    participantName: string;
    content: string;
    messageId: string;
  };
  similarityScore?: number;
  timestamp: string;
}

interface ContradictionAlertProps {
  contradiction: Contradiction;
  onRequestClarification?: (contradictionId: string) => void;
  onDismiss?: (contradictionId: string) => void;
  className?: string;
}

export function ContradictionAlert({
  contradiction,
  onRequestClarification,
  onDismiss,
  className,
}: ContradictionAlertProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { id, severity, statement1, statement2, similarityScore } = contradiction;

  // Severity styling
  const severityConfig = {
    high: {
      variant: 'destructive' as const,
      badge: 'bg-red-500 text-white',
      icon: 'text-red-600',
      label: 'High Severity',
    },
    medium: {
      variant: 'warning' as const,
      badge: 'bg-orange-500 text-white',
      icon: 'text-orange-600',
      label: 'Medium Severity',
    },
    low: {
      variant: 'default' as const,
      badge: 'bg-yellow-500 text-white',
      icon: 'text-yellow-600',
      label: 'Low Severity',
    },
  };

  const config = severityConfig[severity];

  return (
    <Alert variant={config.variant} className={cn('my-2', className)}>
      {/* Header */}
      <div className="flex items-start gap-2">
        <AlertTriangle className={cn('h-4 w-4 mt-0.5', config.icon)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <AlertTitle className="text-sm font-semibold">Contradiction Detected</AlertTitle>
            <Badge className={cn('text-xs', config.badge)}>{config.label}</Badge>
            {similarityScore !== undefined && (
              <span className="text-xs text-muted-foreground">
                {Math.round(similarityScore * 100)}% similarity
              </span>
            )}
          </div>
          <AlertDescription className="text-xs">
            Conflicting statements found between {statement1.participantName} and {statement2.participantName}
          </AlertDescription>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
            className="h-8 w-8 p-0"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          {onDismiss && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDismiss(id)}
              aria-label="Dismiss contradiction"
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Collapsible Details */}
      {isExpanded && (
        <div className="mt-3 space-y-3 pl-6">
          {/* Statement 1 */}
          <div className="p-3 rounded-md bg-muted/50 border">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold">{statement1.participantName}</span>
              <Badge variant="outline" className="text-xs">Statement 1</Badge>
            </div>
            <p className="text-xs leading-relaxed">{statement1.content}</p>
          </div>

          {/* Statement 2 */}
          <div className="p-3 rounded-md bg-muted/50 border">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold">{statement2.participantName}</span>
              <Badge variant="outline" className="text-xs">Statement 2</Badge>
            </div>
            <p className="text-xs leading-relaxed">{statement2.content}</p>
          </div>

          {/* Actions */}
          {onRequestClarification && (
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRequestClarification(id)}
                className="text-xs"
              >
                <MessageSquare className="h-3 w-3 mr-1" />
                Request Clarification
              </Button>
            </div>
          )}
        </div>
      )}
    </Alert>
  );
}
