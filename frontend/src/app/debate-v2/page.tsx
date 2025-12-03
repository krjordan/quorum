/**
 * Debate V2 Page
 * Main page for sequential turn-based debates
 * Phase 2 implementation with XState machine
 */
'use client';

import { useSequentialDebate } from '@/hooks/useSequentialDebate';
import { DebateConfigPanelV2 } from '@/components/debate/DebateConfigPanelV2';
import { DebateControls } from '@/components/debate/DebateControls';
import { DebateArenaV2 } from '@/components/debate/DebateArenaV2';
import { CostTrackerV2 } from '@/components/debate/CostTrackerV2';
import { DebateSummary } from '@/components/debate/DebateSummary';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export default function DebateV2Page() {
  const debate = useSequentialDebate();

  const {
    isConfiguring,
    isReady,
    isRunning,
    isPaused,
    isCompleted,
    isError,
    context,
  } = debate;

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-4xl font-bold mb-2">AI Debate Arena V2</h1>
        <p className="text-muted-foreground">
          Sequential turn-based multi-LLM debates
        </p>
      </div>

      {/* Error Display */}
      {isError && context.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{context.error}</AlertDescription>
        </Alert>
      )}

      {/* Configuration Phase */}
      {isConfiguring && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <DebateConfigPanelV2 debate={debate} />
          </div>
          <div className="space-y-6">
            <div className="sticky top-4">
              <CostTrackerV2 debate={debate} />
            </div>
          </div>
        </div>
      )}

      {/* Debate Running/Paused/Ready */}
      {(isReady || isRunning || isPaused) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <DebateControls debate={debate} />
            <DebateArenaV2 debate={debate} />
          </div>
          <div className="space-y-6">
            <div className="sticky top-4">
              <CostTrackerV2 debate={debate} />
            </div>
          </div>
        </div>
      )}

      {/* Completed - Show Summary */}
      {isCompleted && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <DebateSummary debate={debate} />
          </div>
          <div className="space-y-6">
            <CostTrackerV2 debate={debate} />
            <Alert>
              <AlertDescription>
                Debate completed! View the summary and download the transcript.
              </AlertDescription>
            </Alert>
          </div>
        </div>
      )}
    </div>
  );
}
