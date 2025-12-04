/**
 * Debate Configuration Panel V2
 * Phase 2: Sequential turn-based debates without AI judge
 * Integrated with XState machine
 */
'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2, PlayCircle } from 'lucide-react';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';
import type { ParticipantConfig } from '@/lib/debate/debate-machine';

interface DebateConfigPanelV2Props {
  debate: UseSequentialDebateReturn;
}

// Available models - verified against LiteLLM docs (https://docs.litellm.ai/docs/providers/anthropic)
// Prioritizing cost-effective models (3.5/3.7 series)
const AVAILABLE_MODELS = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  {
    id: 'claude-3-7-sonnet-20250219',
    name: 'Claude 3.7 Sonnet',
    provider: 'Anthropic',
  },
  {
    id: 'claude-3-5-sonnet-20240620',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
  },
  {
    id: 'claude-3-haiku-20240307',
    name: 'Claude 3 Haiku (Fastest)',
    provider: 'Anthropic',
  },
  {
    id: 'claude-3-opus-20240229',
    name: 'Claude 3 Opus',
    provider: 'Anthropic',
  },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google' },
  { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', provider: 'Google' },
];

const DEFAULT_SYSTEM_PROMPT =
  'You are a thoughtful debate participant. Engage with the topic and other participants\' arguments carefully and respectfully.';

export function DebateConfigPanelV2({ debate }: DebateConfigPanelV2Props) {
  const { send, isConfiguring, canStart, startDebate } = debate;

  const [topic, setTopic] = useState('');
  const [maxRounds, setMaxRounds] = useState(3);
  const [participants, setParticipants] = useState<ParticipantConfig[]>([
    {
      name: 'Agent 1',
      model: AVAILABLE_MODELS[0].id, // GPT-4o
      system_prompt: DEFAULT_SYSTEM_PROMPT,
      temperature: 0.7,
    },
    {
      name: 'Agent 2',
      model: AVAILABLE_MODELS[1].id, // Claude 3.7 Sonnet
      system_prompt: DEFAULT_SYSTEM_PROMPT,
      temperature: 0.7,
    },
  ]);

  const addParticipant = () => {
    if (participants.length >= 4) return;

    setParticipants([
      ...participants,
      {
        name: `Agent ${participants.length + 1}`,
        model: AVAILABLE_MODELS[participants.length % AVAILABLE_MODELS.length].id,
        system_prompt: DEFAULT_SYSTEM_PROMPT,
        temperature: 0.7,
      },
    ]);
  };

  const removeParticipant = (index: number) => {
    if (participants.length <= 2) return;
    setParticipants(participants.filter((_, i) => i !== index));
  };

  const updateParticipant = (
    index: number,
    updates: Partial<ParticipantConfig>
  ) => {
    setParticipants(
      participants.map((p, i) => (i === index ? { ...p, ...updates } : p))
    );
  };

  const handleStartDebate = () => {
    if (!topic.trim()) {
      alert('Please enter a debate topic');
      return;
    }

    if (maxRounds < 1 || maxRounds > 5) {
      alert('Max rounds must be between 1 and 5');
      return;
    }

    if (participants.length < 2 || participants.length > 4) {
      alert('Must have 2-4 participants');
      return;
    }

    // Validate all participants
    const invalid = participants.find(
      (p) => !p.name.trim() || !p.model.trim()
    );
    if (invalid) {
      alert('All participants must have a name and model selected');
      return;
    }

    // Set config in machine
    send({
      type: 'SET_CONFIG',
      config: {
        topic: topic.trim(),
        participants,
        max_rounds: maxRounds,
      },
    });

    // Start debate
    setTimeout(() => {
      startDebate({
        topic: topic.trim(),
        participants,
        max_rounds: maxRounds,
      });
    }, 100);
  };

  return (
    <Card className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Configure Debate</h2>
        <p className="text-sm text-muted-foreground">
          Set up a sequential turn-based debate with 2-4 AI agents
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

      {/* Max Rounds (Required) */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          Number of Rounds (Required)
        </label>
        <Select
          value={maxRounds.toString()}
          onValueChange={(value) => setMaxRounds(parseInt(value))}
          disabled={!isConfiguring}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[1, 2, 3, 4, 5].map((n) => (
              <SelectItem key={n} value={n.toString()}>
                {n} {n === 1 ? 'Round' : 'Rounds'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Participants */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">
            Participants ({participants.length}/4)
          </label>
          <Button
            variant="outline"
            size="sm"
            onClick={addParticipant}
            disabled={participants.length >= 4 || !isConfiguring}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Participant
          </Button>
        </div>

        <div className="space-y-4">
          {participants.map((participant, index) => (
            <Card key={index} className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <Badge variant="outline">Agent {index + 1}</Badge>
                {participants.length > 2 && isConfiguring && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeParticipant(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>

              {/* Name */}
              <div>
                <label className="text-xs text-muted-foreground">Name</label>
                <Input
                  value={participant.name}
                  onChange={(e) =>
                    updateParticipant(index, { name: e.target.value })
                  }
                  placeholder="Agent name"
                  disabled={!isConfiguring}
                />
              </div>

              {/* Model Selection */}
              <div>
                <label className="text-xs text-muted-foreground">Model</label>
                <Select
                  value={participant.model}
                  onValueChange={(value) =>
                    updateParticipant(index, { model: value })
                  }
                  disabled={!isConfiguring}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_MODELS.map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.name} ({model.provider})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* System Prompt */}
              <div>
                <label className="text-xs text-muted-foreground">
                  System Prompt (Editable)
                </label>
                <Textarea
                  value={participant.system_prompt}
                  onChange={(e) =>
                    updateParticipant(index, { system_prompt: e.target.value })
                  }
                  placeholder="Custom system prompt..."
                  className="min-h-[80px] text-sm"
                  disabled={!isConfiguring}
                />
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Start Button */}
      <Button
        className="w-full"
        size="lg"
        onClick={handleStartDebate}
        disabled={!isConfiguring || !topic.trim()}
      >
        <PlayCircle className="h-5 w-5 mr-2" />
        Start Debate
      </Button>

      {/* Info */}
      <div className="text-xs text-muted-foreground space-y-1">
        <p>
          • Participants take turns sequentially (Agent 1 → 2 → 3 → 4 → 1...)
        </p>
        <p>• Each agent sees the full conversation history</p>
        <p>• You can pause, resume, or stop the debate at any time</p>
      </div>
    </Card>
  );
}
