/**
 * Cost Tracker Component
 * Phase 2 Implementation - Real-time cost monitoring with warnings
 */

"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, DollarSign, TrendingUp } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

const COST_THRESHOLDS = {
  WARNING: 0.50,
  HIGH: 1.00,
  CRITICAL: 2.00,
};

export function CostTracker() {
  const { metrics, stopDebate, status } = useDebateStore();
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [hasShownHighWarning, setHasShownHighWarning] = useState(false);

  const totalCost = metrics.totalCost;
  const totalTokens = metrics.totalTokens;

  // Determine warning level
  const getWarningLevel = (cost: number) => {
    if (cost >= COST_THRESHOLDS.CRITICAL) return "critical";
    if (cost >= COST_THRESHOLDS.HIGH) return "high";
    if (cost >= COST_THRESHOLDS.WARNING) return "warning";
    return "normal";
  };

  const warningLevel = getWarningLevel(totalCost);

  // Auto-stop at critical threshold
  useEffect(() => {
    if (totalCost >= COST_THRESHOLDS.CRITICAL && status === "RUNNING") {
      setShowStopDialog(true);
    }
  }, [totalCost, status]);

  // Show warning dialog at $1.00
  useEffect(() => {
    if (totalCost >= COST_THRESHOLDS.HIGH && !hasShownHighWarning && status === "RUNNING") {
      setHasShownHighWarning(true);
      setShowStopDialog(true);
    }
  }, [totalCost, hasShownHighWarning, status]);

  const handleForceStop = () => {
    stopDebate();
    setShowStopDialog(false);
  };

  const handleContinue = () => {
    setShowStopDialog(false);
  };

  const costPercentage = Math.min((totalCost / COST_THRESHOLDS.CRITICAL) * 100, 100);

  return (
    <>
      <Card className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-muted-foreground" />
            <h3 className="font-semibold">Cost Tracker</h3>
          </div>
          <Badge
            variant={
              warningLevel === "critical" || warningLevel === "high"
                ? "destructive"
                : warningLevel === "warning"
                ? "default"
                : "secondary"
            }
          >
            ${totalCost.toFixed(4)}
          </Badge>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Progress to limit</span>
            <span>{costPercentage.toFixed(0)}%</span>
          </div>
          <Progress
            value={costPercentage}
            className={
              warningLevel === "critical" || warningLevel === "high"
                ? "bg-red-200 [&>div]:bg-red-600"
                : warningLevel === "warning"
                ? "bg-yellow-200 [&>div]:bg-yellow-600"
                : ""
            }
          />
        </div>

        {/* Token Count */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Total Tokens</span>
          <span className="font-mono">{totalTokens.toLocaleString()}</span>
        </div>

        {/* Warnings */}
        {warningLevel === "warning" && (
          <Alert variant="warning">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Cost Warning</AlertTitle>
            <AlertDescription>
              Debate cost has exceeded ${COST_THRESHOLDS.WARNING.toFixed(2)}
            </AlertDescription>
          </Alert>
        )}

        {(warningLevel === "high" || warningLevel === "critical") && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>High Cost Alert</AlertTitle>
            <AlertDescription>
              Debate cost is ${totalCost.toFixed(4)}. Consider stopping the debate.
            </AlertDescription>
          </Alert>
        )}

        {/* Per-Participant Breakdown */}
        {metrics.costByParticipant.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <TrendingUp className="w-4 h-4" />
              <span>Cost by Participant</span>
            </div>

            <div className="space-y-2">
              {metrics.costByParticipant.map((participant) => (
                <div
                  key={participant.participantId}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground truncate max-w-[150px]">
                      {participant.participantName}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground font-mono">
                      {participant.tokens.toLocaleString()} tokens
                    </span>
                    <span className="font-mono font-medium">
                      ${participant.cost.toFixed(4)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Stop Confirmation Dialog */}
      <Dialog open={showStopDialog} onOpenChange={setShowStopDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {totalCost >= COST_THRESHOLDS.CRITICAL
                ? "Critical Cost Limit Reached"
                : "High Cost Warning"}
            </DialogTitle>
            <DialogDescription>
              {totalCost >= COST_THRESHOLDS.CRITICAL ? (
                <>
                  The debate has reached the critical cost limit of $
                  {COST_THRESHOLDS.CRITICAL.toFixed(2)}. Current cost: $
                  {totalCost.toFixed(4)}.
                  <br />
                  <br />
                  Please stop the debate or override to continue at your own risk.
                </>
              ) : (
                <>
                  The debate cost has exceeded ${COST_THRESHOLDS.HIGH.toFixed(2)}.
                  Current cost: ${totalCost.toFixed(4)}.
                  <br />
                  <br />
                  Would you like to continue or stop the debate?
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleContinue}>
              {totalCost >= COST_THRESHOLDS.CRITICAL ? "Override & Continue" : "Continue"}
            </Button>
            <Button variant="destructive" onClick={handleForceStop}>
              Stop Debate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
