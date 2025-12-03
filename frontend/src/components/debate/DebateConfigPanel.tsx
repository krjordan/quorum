/**
 * Debate Configuration Panel Component
 * Phase 2 Implementation
 */

"use client";

import { useState } from "react";
import { useDebateStore } from "@/stores/debate-store";
import { AVAILABLE_MODELS, PARTICIPANT_COLORS, DEFAULT_PERSONAS } from "@/lib/debate/models";
import type { DebateFormat, Participant } from "@/types/debate";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, PlayCircle } from "lucide-react";

export function DebateConfigPanel() {
  const { setConfig, startDebate, status } = useDebateStore();

  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState<DebateFormat>("free-form");
  const [maxRounds, setMaxRounds] = useState<number>(5);
  const [autoAssignPersonas, setAutoAssignPersonas] = useState(true);
  const [judgeModelId, setJudgeModelId] = useState<string>("claude-3-5-sonnet-20241022");

  const [participants, setParticipants] = useState<Participant[]>([
    {
      id: crypto.randomUUID(),
      model: AVAILABLE_MODELS[0],
      persona: DEFAULT_PERSONAS.pro,
      color: PARTICIPANT_COLORS[0],
      position: "pro",
    },
    {
      id: crypto.randomUUID(),
      model: AVAILABLE_MODELS[1],
      persona: DEFAULT_PERSONAS.con,
      color: PARTICIPANT_COLORS[1],
      position: "con",
    },
  ]);

  const addParticipant = () => {
    if (participants.length >= 4) return;

    const newParticipant: Participant = {
      id: crypto.randomUUID(),
      model: AVAILABLE_MODELS[participants.length % AVAILABLE_MODELS.length],
      persona: DEFAULT_PERSONAS.neutral,
      color: PARTICIPANT_COLORS[participants.length % PARTICIPANT_COLORS.length],
    };

    setParticipants([...participants, newParticipant]);
  };

  const removeParticipant = (id: string) => {
    if (participants.length <= 2) return;
    setParticipants(participants.filter(p => p.id !== id));
  };

  const updateParticipant = (id: string, updates: Partial<Participant>) => {
    setParticipants(participants.map(p =>
      p.id === id ? { ...p, ...updates } : p
    ));
  };

  const handleStartDebate = async () => {
    if (!topic.trim()) {
      alert("Please enter a debate topic");
      return;
    }

    const judgeModel = AVAILABLE_MODELS.find(m => m.id === judgeModelId);
    if (!judgeModel) {
      alert("Please select a judge model");
      return;
    }

    const config = {
      topic: topic.trim(),
      participants,
      format,
      judgeModel,
      maxRounds: format === "round-limited" ? maxRounds : undefined,
      convergenceThreshold: format === "convergence" ? 0.8 : undefined,
      autoAssignPersonas,
    };

    setConfig(config);
    await startDebate();
  };

  const isConfiguring = status === "CONFIGURING";

  return (
    <Card className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Configure Debate</h2>
        <p className="text-sm text-muted-foreground">
          Set up a multi-LLM debate with 2-4 participants
        </p>
      </div>

      {/* Topic Input */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Debate Topic</label>
        <Textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter the debate topic or question..."
          className="min-h-[100px]"
          disabled={!isConfiguring}
        />
      </div>

      {/* Format Selection */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Debate Format</label>
        <Select
          value={format}
          onValueChange={(value) => setFormat(value as DebateFormat)}
          disabled={!isConfiguring}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="free-form">Free-form Discussion</SelectItem>
            <SelectItem value="structured">Structured (Opening → Rebuttal → Closing)</SelectItem>
            <SelectItem value="round-limited">Round-Limited</SelectItem>
            <SelectItem value="convergence">Convergence-based</SelectItem>
          </SelectContent>
        </Select>

        {format === "round-limited" && (
          <div className="flex items-center gap-2 mt-2">
            <label className="text-sm">Max Rounds:</label>
            <Input
              type="number"
              min={1}
              max={10}
              value={maxRounds}
              onChange={(e) => setMaxRounds(parseInt(e.target.value) || 1)}
              className="w-20"
              disabled={!isConfiguring}
            />
          </div>
        )}
      </div>

      {/* Participants */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Participants ({participants.length}/4)</label>
          <Button
            variant="outline"
            size="sm"
            onClick={addParticipant}
            disabled={participants.length >= 4 || !isConfiguring}
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Participant
          </Button>
        </div>

        {participants.map((participant, index) => (
          <Card key={participant.id} className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: participant.color }}
                />
                <span className="font-medium">Participant {index + 1}</span>
              </div>
              {participants.length > 2 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeParticipant(participant.id)}
                  disabled={!isConfiguring}
                >
                  <Trash2 className="w-4 h-4 text-destructive" />
                </Button>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">Model</label>
              <Select
                value={participant.model.id}
                onValueChange={(value) => {
                  const model = AVAILABLE_MODELS.find(m => m.id === value);
                  if (model) updateParticipant(participant.id, { model });
                }}
                disabled={!isConfiguring}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AVAILABLE_MODELS.map(model => (
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex items-center justify-between gap-4">
                        <span>{model.name}</span>
                        <Badge variant="outline" className="text-xs">
                          ${model.cost_per_1k_tokens}/1K
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">Persona</label>
              <Textarea
                value={participant.persona}
                onChange={(e) => updateParticipant(participant.id, { persona: e.target.value })}
                placeholder="Describe the participant's role or perspective..."
                className="min-h-[60px] text-sm"
                disabled={!isConfiguring}
              />
            </div>
          </Card>
        ))}
      </div>

      {/* Judge Model */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Judge Model</label>
        <Select
          value={judgeModelId}
          onValueChange={setJudgeModelId}
          disabled={!isConfiguring}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {AVAILABLE_MODELS.map(model => (
              <SelectItem key={model.id} value={model.id}>
                {model.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Auto-assign Personas */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="auto-persona"
          checked={autoAssignPersonas}
          onChange={(e) => setAutoAssignPersonas(e.target.checked)}
          disabled={!isConfiguring}
          className="rounded"
        />
        <label htmlFor="auto-persona" className="text-sm">
          Auto-assign personas based on format
        </label>
      </div>

      {/* Start Button */}
      <Button
        className="w-full"
        size="lg"
        onClick={handleStartDebate}
        disabled={!isConfiguring || !topic.trim()}
      >
        <PlayCircle className="w-5 h-5 mr-2" />
        Start Debate
      </Button>
    </Card>
  );
}
