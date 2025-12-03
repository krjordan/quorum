/**
 * Debate Arena Component - Multi-participant streaming layout
 * Phase 2 Implementation
 */

"use client";

import { useDebateStore } from "@/stores/debate-store";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  User,
  Scale,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { useState } from "react";
import type { Participant } from "@/types/debate";

interface ParticipantPanelProps {
  participant: Participant;
  isStreaming: boolean;
  streamText: string;
  tokens: number;
  isComplete: boolean;
}

function ParticipantPanel({
  participant,
  isStreaming,
  streamText,
  tokens,
  isComplete,
}: ParticipantPanelProps) {
  return (
    <Card className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="border-b p-3 bg-muted/30">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: participant.color }}
            />
            <span className="font-medium text-sm">{participant.model.name}</span>
          </div>
          {isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-green-600" />
          ) : isStreaming ? (
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          ) : (
            <Circle className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {participant.persona.split(" ").slice(0, 3).join(" ")}...
          </Badge>
          {tokens > 0 && (
            <Badge variant="secondary" className="text-xs font-mono">
              {tokens} tokens
            </Badge>
          )}
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 p-4">
        {isStreaming || streamText ? (
          <div className="prose prose-sm max-w-none">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {streamText}
              {isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
              )}
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center">
              <User className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Waiting to respond...</p>
            </div>
          </div>
        )}
      </ScrollArea>
    </Card>
  );
}

interface JudgeVerdictPanelProps {
  roundNumber: number;
  verdict?: {
    winner?: string;
    reasoning: string;
    consensus: boolean;
    confidence: number;
  };
  participants: Participant[];
}

function JudgeVerdictPanel({ roundNumber, verdict, participants }: JudgeVerdictPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!verdict) return null;

  const winner = participants.find(p => p.id === verdict.winner);

  return (
    <Card className="mt-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-purple-600" />
          <span className="font-semibold">Judge&apos;s Verdict - Round {roundNumber}</span>
          {verdict.consensus && (
            <Badge variant="default" className="bg-green-600">
              Consensus Reached
            </Badge>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5" />
        ) : (
          <ChevronDown className="w-5 h-5" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 border-t space-y-3">
          {winner && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Winner:</span>
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: winner.color }}
                />
                <span className="font-medium">{winner.model.name}</span>
              </div>
            </div>
          )}

          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">Confidence:</span>
            <div className="flex items-center gap-2">
              <Progress value={verdict.confidence * 100} className="flex-1" />
              <span className="text-sm font-mono">{(verdict.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">Reasoning:</span>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {verdict.reasoning}
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}

export function DebateArena() {
  const { config, rounds, currentRound, activeStreams, status } = useDebateStore();

  if (!config) {
    return (
      <Card className="p-8">
        <div className="text-center text-muted-foreground">
          <p>No debate configured. Please configure a debate to begin.</p>
        </div>
      </Card>
    );
  }

  const currentRoundData = rounds.find(r => r.number === currentRound);
  const participantCount = config.participants.length;

  // Calculate grid layout
  const gridCols = participantCount === 2
    ? "grid-cols-2"
    : participantCount === 3
    ? "grid-cols-3"
    : "grid-cols-2";

  return (
    <div className="space-y-4">
      {/* Round Indicator */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-lg px-3 py-1">
              Round {currentRound}
              {config.maxRounds && ` / ${config.maxRounds}`}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {status === "RUNNING" ? "In Progress" : status === "COMPLETED" ? "Completed" : "Paused"}
            </span>
          </div>
          <div className="text-sm text-muted-foreground">
            <span className="font-medium">{config.format}</span> format
          </div>
        </div>
      </Card>

      {/* Participant Grid */}
      <div className={`grid ${gridCols} gap-4 min-h-[500px]`}>
        {config.participants.map((participant) => {
          const streamText = activeStreams.get(participant.id) || "";
          const isStreaming = activeStreams.has(participant.id);

          // Find response in current round
          const response = currentRoundData?.responses.find(
            r => r.participantId === participant.id
          );

          const displayText = response ? response.content : streamText;
          const tokens = response?.metadata.tokens || 0;
          const isComplete = !!response;

          return (
            <ParticipantPanel
              key={participant.id}
              participant={participant}
              isStreaming={isStreaming}
              streamText={displayText}
              tokens={tokens}
              isComplete={isComplete}
            />
          );
        })}
      </div>

      {/* Judge Verdict (if exists for current round) */}
      {currentRoundData?.verdict && (
        <JudgeVerdictPanel
          roundNumber={currentRound}
          verdict={currentRoundData.verdict}
          participants={config.participants}
        />
      )}

      {/* Previous Rounds */}
      {rounds
        .filter(r => r.number < currentRound && r.completed)
        .reverse()
        .map(round => (
          <div key={round.number} className="space-y-4">
            <Card className="p-4 bg-muted/20">
              <h3 className="font-semibold text-sm text-muted-foreground mb-3">
                Previous Round {round.number}
              </h3>
              <div className="space-y-2">
                {round.responses.map(response => {
                  const participant = config.participants.find(
                    p => p.id === response.participantId
                  );
                  if (!participant) return null;

                  return (
                    <div
                      key={response.participantId}
                      className="text-sm p-2 rounded bg-background"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: participant.color }}
                        />
                        <span className="font-medium text-xs">
                          {participant.model.name}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {response.content}
                      </p>
                    </div>
                  );
                })}
              </div>
            </Card>

            {round.verdict && (
              <JudgeVerdictPanel
                roundNumber={round.number}
                verdict={round.verdict}
                participants={config.participants}
              />
            )}
          </div>
        ))}
    </div>
  );
}
