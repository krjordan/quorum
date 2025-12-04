/**
 * Main Debate Page
 * Slack-like debate UI with left sidebar and conversation thread
 */
'use client';

import { useSequentialDebate } from '@/hooks/useSequentialDebate';
import { DebateConfigPanelV2 } from '@/components/debate/DebateConfigPanelV2';
import { DebateStatsSidebar } from '@/components/debate/DebateStatsSidebar';
import { DebateThreadView } from '@/components/debate/DebateThreadView';
import { DebateInputControls } from '@/components/debate/DebateInputControls';
import { DebateSummary } from '@/components/debate/DebateSummary';

export default function Home() {
  const debate = useSequentialDebate();
  const {
    context,
    isConfiguring,
    isRunning,
    isCompleted,
    isPaused,
    isReady,
    isCheckingProgress,
    isError,
  } = debate;

  // Show debate UI when active
  const showDebateUI =
    isRunning || isPaused || isCheckingProgress || isError || (isReady && context.debateId);

  // Configuring state - show config form
  if (isConfiguring) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
        <div className="max-w-4xl mx-auto">
          <header className="mb-8 text-center">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Quorum
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Multi-LLM Debate Platform
            </p>
          </header>
          <DebateConfigPanelV2 debate={debate} />
        </div>
      </div>
    );
  }

  // Completed state - show summary
  if (isCompleted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
        <div className="max-w-6xl mx-auto">
          <DebateSummary debate={debate} />
        </div>
      </div>
    );
  }

  // Active debate - show Slack-like UI
  if (showDebateUI) {
    return (
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Left Sidebar - 320px fixed */}
        <aside className="w-80 flex-shrink-0 border-r">
          <DebateStatsSidebar debate={debate} />
        </aside>

        {/* Main Area - fills remaining */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Thread - grows to fill */}
          <div className="flex-1 overflow-hidden">
            <DebateThreadView debate={debate} />
          </div>

          {/* Input - fixed bottom */}
          <div className="flex-shrink-0">
            <DebateInputControls debate={debate} />
          </div>
        </main>
      </div>
    );
  }

  // Fallback (should not reach here)
  return null;
}
