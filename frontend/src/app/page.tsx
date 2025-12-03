"use client";

import { useSequentialDebate } from "@/hooks/useSequentialDebate";
import { DebateConfigPanelV2 } from "@/components/debate/DebateConfigPanelV2";
import { DebateArenaV2 } from "@/components/debate/DebateArenaV2";
import { DebateControls } from "@/components/debate/DebateControls";
import { CostTrackerV2 } from "@/components/debate/CostTrackerV2";
import { DebateSummary } from "@/components/debate/DebateSummary";

export default function Home() {
  const debate = useSequentialDebate();
  const { context, isConfiguring, isRunning, isCompleted, isPaused, isReady, isCheckingProgress, isError, stateValue } = debate;

  // Debug logging
  console.log('[HOME] State:', stateValue);
  console.log('[HOME] Flags:', { isConfiguring, isRunning, isCompleted, isPaused, isReady, isCheckingProgress, isError });
  console.log('[HOME] Context:', { debateId: context.debateId, currentRound: context.currentRound, currentTurn: context.currentTurn });
  if (context.error) {
    console.log('[HOME] ERROR:', context.error);
  }

  // Show debate arena when active (running, paused, ready, checking progress, or error)
  const showDebateArena = isRunning || isPaused || isCheckingProgress || isError || (isReady && context.debateId);
  console.log('[HOME] showDebateArena:', showDebateArena);

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <header className="mb-8 text-center">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Quorum
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Multi-LLM Debate Platform
            </p>
          </header>

          {isConfiguring && <DebateConfigPanelV2 debate={debate} />}

          {showDebateArena && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <DebateControls debate={debate} />
                <CostTrackerV2 debate={debate} />
              </div>

              <DebateArenaV2 debate={debate} />
            </div>
          )}

          {isCompleted && <DebateSummary debate={debate} />}
        </div>
      </div>
    </main>
  );
}
