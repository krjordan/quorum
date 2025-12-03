/**
 * Debate Page - Main Multi-LLM Debate Interface
 * Phase 2 Implementation
 * Route: /debate
 */

"use client";

import { useDebateStore } from "@/stores/debate-store";
import { DebateConfigPanel } from "@/components/debate/DebateConfigPanel";
import { DebateArena } from "@/components/debate/DebateArena";
import { CostTracker } from "@/components/debate/CostTracker";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Download,
  Pause,
  Play,
  RotateCcw,
  StopCircle,
  FileJson,
  FileText,
} from "lucide-react";
import { useState } from "react";

export default function DebatePage() {
  const {
    status,
    pauseDebate,
    resumeDebate,
    stopDebate,
    resetDebate,
    exportDebate,
  } = useDebateStore();

  const [exportFormat, setExportFormat] = useState<"markdown" | "json">("markdown");

  const handleExport = () => {
    const content = exportDebate(exportFormat);
    const blob = new Blob([content], {
      type: exportFormat === "json" ? "application/json" : "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `debate-export-${Date.now()}.${exportFormat === "json" ? "json" : "md"}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isRunning = status === "RUNNING";
  const isPaused = status === "PAUSED";
  const isCompleted = status === "COMPLETED";
  const isConfiguring = status === "CONFIGURING";

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-[1800px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Multi-LLM Debate Arena</h1>
          <p className="text-muted-foreground mt-1">
            Phase 2: Orchestrated debate between multiple language models
          </p>
        </div>

        {!isConfiguring && (
          <div className="flex items-center gap-2">
            {isRunning && (
              <Button variant="outline" onClick={pauseDebate}>
                <Pause className="w-4 h-4 mr-2" />
                Pause
              </Button>
            )}

            {isPaused && (
              <Button variant="outline" onClick={resumeDebate}>
                <Play className="w-4 h-4 mr-2" />
                Resume
              </Button>
            )}

            {(isRunning || isPaused) && (
              <Button variant="destructive" onClick={stopDebate}>
                <StopCircle className="w-4 h-4 mr-2" />
                Stop
              </Button>
            )}

            {isCompleted && (
              <>
                <div className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExportFormat("markdown")}
                    className={exportFormat === "markdown" ? "bg-muted" : ""}
                  >
                    <FileText className="w-4 h-4 mr-1" />
                    MD
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExportFormat("json")}
                    className={exportFormat === "json" ? "bg-muted" : ""}
                  >
                    <FileJson className="w-4 h-4 mr-1" />
                    JSON
                  </Button>
                </div>
                <Button onClick={handleExport}>
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
                <Button variant="outline" onClick={resetDebate}>
                  <RotateCcw className="w-4 h-4 mr-2" />
                  New Debate
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Status Banner */}
      {!isConfiguring && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`w-3 h-3 rounded-full ${
                  isRunning
                    ? "bg-green-500 animate-pulse"
                    : isPaused
                    ? "bg-yellow-500"
                    : isCompleted
                    ? "bg-blue-500"
                    : "bg-gray-500"
                }`}
              />
              <span className="font-medium">
                {isRunning
                  ? "Debate in Progress"
                  : isPaused
                  ? "Debate Paused"
                  : isCompleted
                  ? "Debate Completed"
                  : "Ready"}
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel: Configuration or Controls */}
        <div className="lg:col-span-1 space-y-6">
          {isConfiguring ? (
            <DebateConfigPanel />
          ) : (
            <>
              <CostTracker />
              {/* Additional controls or metrics can go here */}
            </>
          )}
        </div>

        {/* Right Panel: Debate Arena */}
        <div className="lg:col-span-2">
          {!isConfiguring ? (
            <DebateArena />
          ) : (
            <Card className="p-12">
              <div className="text-center text-muted-foreground space-y-2">
                <p className="text-lg">Configure your debate to begin</p>
                <p className="text-sm">
                  Select 2-4 LLM models, set a topic, and choose a debate format
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
