# Phase 2: Frontend Component Architecture

## Overview

React component hierarchy for multi-LLM debate interface with real-time streaming, cost tracking, and state management via XState + Zustand.

## Component Tree Structure

```
app/
├── page.tsx
│   └── DebateContainer (Client Component)
│       ├── DebateConfigPanel
│       │   ├── TopicInput
│       │   ├── FormatSelector
│       │   ├── ParticipantConfigurator
│       │   │   └── ModelSelector
│       │   ├── JudgeConfigurator
│       │   └── AdvancedSettings
│       │       ├── RoundSlider
│       │       ├── CostLimitInput
│       │       └── TimeoutInput
│       │
│       ├── DebateArena (shown when state !== 'idle')
│       │   ├── DebateHeader
│       │   │   ├── TopicDisplay
│       │   │   ├── StateIndicator
│       │   │   └── RoundProgress
│       │   │
│       │   ├── ParticipantGrid
│       │   │   ├── ParticipantPanel (2-4 instances)
│       │   │   │   ├── ParticipantHeader
│       │   │   │   │   ├── Avatar
│       │   │   │   │   ├── NameBadge
│       │   │   │   │   └── ModelInfo
│       │   │   │   ├── StreamingResponse
│       │   │   │   │   ├── TypewriterText
│       │   │   │   │   └── StreamingIndicator
│       │   │   │   └── ParticipantMetrics
│       │   │   │       ├── TokenCounter
│       │   │   │       ├── LatencyBadge
│       │   │   │       └── CostDisplay
│       │   │   │
│       │   │   └── JudgePanel (shown in 'judge_evaluating' state)
│       │   │       ├── JudgeHeader
│       │   │       ├── StreamingVerdict
│       │   │       └── ScoreCards
│       │   │           └── ParticipantScore (per participant)
│       │   │
│       │   └── RoundTimeline
│       │       └── RoundCard[] (historical rounds)
│       │           ├── RoundNumber
│       │           ├── ResponsePreview[]
│       │           └── RoundMetrics
│       │
│       ├── CostTracker (floating overlay)
│       │   ├── TotalCostDisplay
│       │   ├── ModelBreakdown
│       │   │   └── ModelCostItem[]
│       │   ├── TokenUsageChart
│       │   ├── WarningIndicator
│       │   └── LimitProgressBar
│       │
│       ├── DebateControls
│       │   ├── StartButton
│       │   ├── PauseButton
│       │   ├── StopButton
│       │   ├── ResumeButton
│       │   └── ExportButton
│       │       └── ExportMenu
│       │           ├── ExportJSON
│       │           ├── ExportMarkdown
│       │           └── ExportHTML
│       │
│       └── ErrorBoundary
│           └── ErrorDisplay
│               ├── ErrorMessage
│               ├── RetryButton
│               └── DebugInfo

components/ui/ (shadcn components)
├── button.tsx
├── card.tsx
├── input.tsx
├── textarea.tsx
├── badge.tsx
├── slider.tsx
├── select.tsx
├── progress.tsx
├── separator.tsx
├── avatar.tsx
├── alert.tsx
├── dialog.tsx
└── tabs.tsx
```

## Component Specifications

### 1. DebateContainer (Root Component)

**Purpose**: Orchestrates entire debate UI and manages XState machine

**Props**: None (route-based)

**State Integration**:
- XState machine via `useMachine(debateMachine)`
- Zustand store via `useDebateStore()`

**Responsibilities**:
- Initialize XState debate machine
- Handle SSE connection lifecycle
- Route events to state machine
- Render different views based on state

```typescript
// frontend/src/components/debate/DebateContainer.tsx

'use client';

import { useMachine } from '@xstate/react';
import { debateMachine } from '@/machines/debate-machine';
import { useEffect } from 'react';

export function DebateContainer() {
  const [state, send] = useMachine(debateMachine);

  const isIdle = state.matches('idle');
  const isActive = !isIdle && !state.matches('completed') && !state.matches('error');
  const isCompleted = state.matches('completed');
  const hasError = state.matches('error');

  return (
    <div className="min-h-screen bg-background">
      {/* Always show config panel when idle */}
      {isIdle && (
        <DebateConfigPanel
          onStart={(config) => send({ type: 'START_DEBATE', config })}
        />
      )}

      {/* Show arena during active debate */}
      {isActive && (
        <DebateArena
          state={state.value as string}
          context={state.context}
          onPause={() => send({ type: 'PAUSE' })}
          onStop={() => send({ type: 'STOP' })}
          onResume={() => send({ type: 'RESUME' })}
        />
      )}

      {/* Show results when completed */}
      {isCompleted && (
        <DebateResults
          verdict={state.context.verdict}
          transcript={state.context.rounds}
          costs={state.context.costTracker}
          onNewDebate={() => send({ type: 'RESET' })}
        />
      )}

      {/* Error handling */}
      {hasError && (
        <ErrorDisplay
          error={state.context.lastError}
          canRetry={state.context.lastError?.retryable}
          onRetry={() => send({ type: 'RETRY' })}
          onDismiss={() => send({ type: 'RESET' })}
        />
      )}

      {/* Floating cost tracker (always visible when not idle) */}
      {!isIdle && (
        <CostTracker
          totalCost={state.context.costTracker.totalCost}
          costByModel={state.context.costTracker.costByModel}
          tokenUsage={state.context.tokenUsage}
          warnings={state.context.costTracker.warnings}
          limit={state.context.config.costLimit}
        />
      )}
    </div>
  );
}
```

---

### 2. DebateConfigPanel

**Purpose**: Configure debate parameters before starting

**Props**:
```typescript
interface DebateConfigPanelProps {
  onStart: (config: DebateConfig) => void;
}
```

**Features**:
- Topic input with character counter
- Format selection (Oxford, Lincoln-Douglas, Roundtable)
- 2-4 participant configuration with drag-to-reorder
- Judge configuration
- Advanced settings collapse panel
- Real-time validation

**Layout**: Centered card with sections

```typescript
// frontend/src/components/debate/DebateConfigPanel.tsx

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

export function DebateConfigPanel({ onStart }: DebateConfigPanelProps) {
  const [config, setConfig] = useState<Partial<DebateConfig>>({
    topic: '',
    format: 'oxford',
    participants: [],
    maxRounds: 5,
    timeoutPerRound: 90,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateConfig = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!config.topic || config.topic.length < 10) {
      newErrors.topic = 'Topic must be at least 10 characters';
    }

    if (config.participants.length < 2) {
      newErrors.participants = 'At least 2 participants required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleStart = () => {
    if (validateConfig()) {
      onStart(config as DebateConfig);
    }
  };

  return (
    <div className="container max-w-4xl mx-auto py-8">
      <Card className="p-6">
        <h1 className="text-3xl font-bold mb-6">Configure Debate</h1>

        {/* Topic Input */}
        <section className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Debate Topic *
          </label>
          <Textarea
            placeholder="e.g., Should AI development be regulated by government?"
            value={config.topic}
            onChange={(e) => setConfig({ ...config, topic: e.target.value })}
            maxLength={500}
            className={errors.topic ? 'border-red-500' : ''}
          />
          <div className="flex justify-between mt-1">
            <span className="text-sm text-red-500">{errors.topic}</span>
            <span className="text-sm text-muted-foreground">
              {config.topic?.length || 0}/500
            </span>
          </div>
        </section>

        {/* Format Selector */}
        <FormatSelector
          value={config.format}
          onChange={(format) => setConfig({ ...config, format })}
        />

        {/* Participant Configurator */}
        <ParticipantConfigurator
          participants={config.participants}
          onChange={(participants) => setConfig({ ...config, participants })}
          error={errors.participants}
        />

        {/* Judge Configurator */}
        <JudgeConfigurator
          judge={config.judge}
          onChange={(judge) => setConfig({ ...config, judge })}
        />

        {/* Advanced Settings */}
        <AdvancedSettings
          config={config}
          onChange={(updates) => setConfig({ ...config, ...updates })}
        />

        {/* Start Button */}
        <div className="mt-8">
          <Button
            size="lg"
            className="w-full"
            onClick={handleStart}
            disabled={!config.topic || config.participants.length < 2}
          >
            Start Debate
          </Button>
        </div>
      </Card>
    </div>
  );
}
```

---

### 3. DebateArena

**Purpose**: Main debate visualization during active rounds

**Props**:
```typescript
interface DebateArenaProps {
  state: string;              // XState current state
  context: DebateContext;
  onPause: () => void;
  onStop: () => void;
  onResume: () => void;
}
```

**Layout**: Grid layout with participants + judge panel

```typescript
// frontend/src/components/debate/DebateArena.tsx

export function DebateArena({ state, context, onPause, onStop, onResume }: DebateArenaProps) {
  const isPaused = state === 'paused';
  const isJudging = state === 'judgeEvaluating';

  return (
    <div className="container max-w-7xl mx-auto py-4">
      {/* Header */}
      <DebateHeader
        topic={context.config.topic}
        state={state}
        currentRound={context.currentRound}
        maxRounds={context.maxRounds}
      />

      {/* Participant Grid */}
      <ParticipantGrid
        participants={context.participants}
        currentRound={context.currentRound}
        rounds={context.rounds}
        activeStreams={context.activeStreams}
        isJudging={isJudging}
      />

      {/* Judge Panel (shown during evaluation) */}
      {isJudging && context.judge && (
        <JudgePanel
          judge={context.judge}
          verdict={context.verdict}
        />
      )}

      {/* Round Timeline (collapsible history) */}
      <RoundTimeline rounds={context.rounds} />

      {/* Controls */}
      <DebateControls
        isPaused={isPaused}
        onPause={onPause}
        onStop={onStop}
        onResume={onResume}
        debateId={context.config.id}
      />
    </div>
  );
}
```

---

### 4. ParticipantPanel

**Purpose**: Display individual debater's responses with streaming

**Props**:
```typescript
interface ParticipantPanelProps {
  participant: DebateParticipant;
  currentRound: number;
  responses: DebateResponse[];      // Historical responses
  streamingContent?: string;        // Current streaming text
  isStreaming: boolean;
  metrics: {
    totalTokens: number;
    averageLatency: number;
    totalCost: number;
  };
}
```

**Features**:
- Color-coded border matching participant
- Model badge with icon
- Typewriter effect for streaming text
- Token/cost/latency metrics
- Scroll to latest response

```typescript
// frontend/src/components/debate/ParticipantPanel.tsx

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar } from '@/components/ui/avatar';
import { useEffect, useRef } from 'react';

export function ParticipantPanel({
  participant,
  currentRound,
  responses,
  streamingContent,
  isStreaming,
  metrics
}: ParticipantPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamingContent, responses]);

  return (
    <Card
      className="p-4 h-[600px] flex flex-col"
      style={{ borderTopColor: participant.color, borderTopWidth: '4px' }}
    >
      {/* Header */}
      <ParticipantHeader participant={participant} />

      {/* Response Container */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 mb-4"
      >
        {responses.map((response, idx) => (
          <div key={idx} className="border-l-2 pl-3" style={{ borderColor: participant.color }}>
            <div className="text-xs text-muted-foreground mb-1">
              Round {response.roundNumber}
            </div>
            <div className="text-sm whitespace-pre-wrap">
              {response.content}
            </div>
          </div>
        ))}

        {/* Streaming content */}
        {isStreaming && streamingContent && (
          <div className="border-l-2 pl-3 animate-pulse" style={{ borderColor: participant.color }}>
            <div className="text-xs text-muted-foreground mb-1">
              Round {currentRound}
              <StreamingIndicator />
            </div>
            <TypewriterText text={streamingContent} />
          </div>
        )}
      </div>

      {/* Metrics */}
      <ParticipantMetrics metrics={metrics} />
    </Card>
  );
}
```

---

### 5. JudgePanel

**Purpose**: Display judge evaluation and verdict

**Props**:
```typescript
interface JudgePanelProps {
  judge: JudgeParticipant;
  verdict?: JudgeVerdict;
  streamingContent?: string;
  isStreaming: boolean;
}
```

**Layout**: Prominent card with score visualization

```typescript
// frontend/src/components/debate/JudgePanel.tsx

export function JudgePanel({ judge, verdict, streamingContent, isStreaming }: JudgePanelProps) {
  return (
    <Card className="p-6 my-6 border-yellow-500 border-2">
      <JudgeHeader judge={judge} />

      {/* Streaming verdict */}
      {isStreaming && (
        <div className="my-4">
          <StreamingIndicator />
          <TypewriterText text={streamingContent || ''} />
        </div>
      )}

      {/* Final verdict */}
      {verdict && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold">Verdict</h3>

          {/* Winner announcement */}
          {verdict.winner && (
            <div className="bg-yellow-50 dark:bg-yellow-950 p-4 rounded-lg">
              <p className="text-lg">
                Winner: <strong>{verdict.winner}</strong>
              </p>
            </div>
          )}

          {/* Score cards */}
          <ScoreCards scores={verdict.scores} />

          {/* Reasoning */}
          <div>
            <h4 className="font-medium mb-2">Reasoning</h4>
            <p className="text-sm whitespace-pre-wrap">{verdict.reasoning}</p>
          </div>

          {/* Criteria breakdown */}
          <div>
            <h4 className="font-medium mb-2">Evaluation Criteria</h4>
            {Object.entries(verdict.criteria).map(([criterion, evaluation]) => (
              <div key={criterion} className="mb-2">
                <strong className="text-sm">{criterion}:</strong>
                <p className="text-sm text-muted-foreground">{evaluation}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
```

---

### 6. CostTracker (Floating Overlay)

**Purpose**: Real-time cost monitoring and warnings

**Props**:
```typescript
interface CostTrackerProps {
  totalCost: number;
  costByModel: Map<string, number>;
  tokenUsage: Map<string, ModelTokenUsage>;
  warnings: CostWarning[];
  limit?: number;
}
```

**Features**:
- Minimizable floating card (bottom-right)
- Color-coded progress bar (green → yellow → red)
- Modal warning on threshold breach
- Detailed breakdown on expand

```typescript
// frontend/src/components/debate/CostTracker.tsx

import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useState } from 'react';

export function CostTracker({
  totalCost,
  costByModel,
  tokenUsage,
  warnings,
  limit
}: CostTrackerProps) {
  const [expanded, setExpanded] = useState(false);
  const percentOfLimit = limit ? (totalCost / limit) * 100 : 0;

  const getColorClass = () => {
    if (!limit) return 'bg-blue-500';
    if (percentOfLimit < 60) return 'bg-green-500';
    if (percentOfLimit < 85) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <>
      {/* Warning modal */}
      {warnings.length > 0 && !warnings[0].acknowledged && (
        <CostWarningModal warning={warnings[0]} />
      )}

      {/* Floating tracker */}
      <div className="fixed bottom-4 right-4 z-50">
        <Card
          className={`p-4 cursor-pointer transition-all ${
            expanded ? 'w-80' : 'w-48'
          }`}
          onClick={() => setExpanded(!expanded)}
        >
          {/* Minimized view */}
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground">Total Cost</div>
              <div className="text-2xl font-bold">
                ${totalCost.toFixed(3)}
              </div>
            </div>
            {limit && (
              <Badge variant={percentOfLimit > 85 ? 'destructive' : 'secondary'}>
                {percentOfLimit.toFixed(0)}%
              </Badge>
            )}
          </div>

          {/* Progress bar */}
          {limit && (
            <Progress
              value={percentOfLimit}
              className={`mt-2 ${getColorClass()}`}
            />
          )}

          {/* Expanded view */}
          {expanded && (
            <div className="mt-4 space-y-3">
              <ModelBreakdown
                costByModel={costByModel}
                tokenUsage={tokenUsage}
              />
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
```

---

### 7. DebateControls

**Purpose**: Control debate flow (pause, resume, stop, export)

**Props**:
```typescript
interface DebateControlsProps {
  isPaused: boolean;
  onPause: () => void;
  onStop: () => void;
  onResume: () => void;
  debateId: string;
}
```

**Layout**: Fixed bottom toolbar

```typescript
// frontend/src/components/debate/DebateControls.tsx

import { Button } from '@/components/ui/button';
import { Pause, Play, Square, Download } from 'lucide-react';

export function DebateControls({
  isPaused,
  onPause,
  onStop,
  onResume,
  debateId
}: DebateControlsProps) {
  const handleExport = async (format: 'json' | 'markdown' | 'html') => {
    const url = `/api/v1/debates/${debateId}/transcript?format=${format}`;
    const response = await fetch(url);
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `debate-${debateId}.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    a.remove();
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4">
      <div className="container max-w-7xl mx-auto flex justify-center gap-4">
        {isPaused ? (
          <Button onClick={onResume} size="lg">
            <Play className="mr-2 h-4 w-4" />
            Resume
          </Button>
        ) : (
          <Button onClick={onPause} size="lg" variant="secondary">
            <Pause className="mr-2 h-4 w-4" />
            Pause
          </Button>
        )}

        <Button onClick={onStop} size="lg" variant="destructive">
          <Square className="mr-2 h-4 w-4" />
          Stop & Judge
        </Button>

        <ExportMenu onExport={handleExport} />
      </div>
    </div>
  );
}
```

---

### 8. StreamingResponse Component

**Purpose**: Handle typewriter effect for streaming text

**Props**:
```typescript
interface StreamingResponseProps {
  content: string;
  isComplete: boolean;
  speed?: number;  // Characters per frame
}
```

**Hook**: `useTypewriterEffect`

```typescript
// frontend/src/hooks/useTypewriterEffect.ts

import { useState, useEffect, useRef } from 'react';

export function useTypewriterEffect(
  fullText: string,
  isComplete: boolean,
  speed: number = 5
) {
  const [displayedText, setDisplayedText] = useState('');
  const indexRef = useRef(0);

  useEffect(() => {
    if (isComplete) {
      setDisplayedText(fullText);
      return;
    }

    if (indexRef.current < fullText.length) {
      const timer = setTimeout(() => {
        indexRef.current = Math.min(indexRef.current + speed, fullText.length);
        setDisplayedText(fullText.slice(0, indexRef.current));
      }, 16); // ~60fps

      return () => clearTimeout(timer);
    }
  }, [fullText, isComplete, speed]);

  return displayedText;
}

// Usage in component
export function TypewriterText({ text, isComplete }: { text: string; isComplete: boolean }) {
  const displayed = useTypewriterEffect(text, isComplete);

  return (
    <div className="font-mono text-sm whitespace-pre-wrap">
      {displayed}
      {!isComplete && <span className="animate-pulse">▊</span>}
    </div>
  );
}
```

---

## Component Directory Structure

```
frontend/src/
├── app/
│   ├── debate/
│   │   └── page.tsx                    # Debate route
│   ├── page.tsx                        # Home/chat route
│   └── layout.tsx
│
├── components/
│   ├── debate/
│   │   ├── DebateContainer.tsx         # Root debate component
│   │   ├── DebateConfigPanel.tsx       # Configuration UI
│   │   │   ├── TopicInput.tsx
│   │   │   ├── FormatSelector.tsx
│   │   │   ├── ParticipantConfigurator.tsx
│   │   │   ├── ModelSelector.tsx
│   │   │   ├── JudgeConfigurator.tsx
│   │   │   └── AdvancedSettings.tsx
│   │   ├── DebateArena.tsx             # Main debate view
│   │   │   ├── DebateHeader.tsx
│   │   │   ├── StateIndicator.tsx
│   │   │   ├── RoundProgress.tsx
│   │   │   └── ParticipantGrid.tsx
│   │   ├── ParticipantPanel.tsx        # Individual debater
│   │   │   ├── ParticipantHeader.tsx
│   │   │   ├── StreamingResponse.tsx
│   │   │   ├── TypewriterText.tsx
│   │   │   ├── StreamingIndicator.tsx
│   │   │   └── ParticipantMetrics.tsx
│   │   ├── JudgePanel.tsx              # Judge evaluation
│   │   │   ├── JudgeHeader.tsx
│   │   │   ├── StreamingVerdict.tsx
│   │   │   └── ScoreCards.tsx
│   │   ├── RoundTimeline.tsx           # Historical rounds
│   │   │   └── RoundCard.tsx
│   │   ├── CostTracker.tsx             # Cost monitoring
│   │   │   ├── TotalCostDisplay.tsx
│   │   │   ├── ModelBreakdown.tsx
│   │   │   ├── CostWarningModal.tsx
│   │   │   └── LimitProgressBar.tsx
│   │   ├── DebateControls.tsx          # Control toolbar
│   │   │   └── ExportMenu.tsx
│   │   ├── DebateResults.tsx           # Final results view
│   │   └── ErrorDisplay.tsx            # Error handling
│   │
│   ├── chat/                           # Existing chat components
│   │   └── ...
│   │
│   └── ui/                             # shadcn components
│       └── ...
│
├── machines/
│   ├── debate-machine.ts               # XState machine
│   └── debate-machine.test.ts
│
├── hooks/
│   ├── useDebateMachine.ts             # Machine hook wrapper
│   ├── useDebateSSE.ts                 # SSE connection hook
│   ├── useTypewriterEffect.ts          # Streaming text effect
│   └── useCostWarning.ts               # Cost warning modal
│
├── stores/
│   ├── debate-store.ts                 # Zustand debate UI state
│   └── chat-store.ts                   # Existing chat store
│
├── lib/
│   ├── api/
│   │   ├── debate-api.ts               # Debate API client
│   │   └── chat-api.ts                 # Existing chat API
│   ├── streaming/
│   │   ├── debate-sse.ts               # SSE handler
│   │   └── sse-client.ts               # Existing SSE
│   └── utils/
│       ├── token-counter.ts            # Client-side token estimation
│       └── cost-calculator.ts          # Cost calculation helpers
│
└── types/
    ├── debate.ts                       # Debate types
    └── chat.ts                         # Existing chat types
```

---

## State Management Strategy

### XState (Debate Flow State)

Handles state machine logic:
- Debate lifecycle states
- State transitions
- Event routing
- Guard conditions

```typescript
// machines/debate-machine.ts
export const debateMachine = createMachine({ /* ... */ });
```

### Zustand (UI State)

Handles UI-specific state:
- Stream buffers (for batching updates)
- UI visibility toggles
- Optimistic updates
- Client-side caching

```typescript
// stores/debate-store.ts

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface DebateUIState {
  // Stream buffers
  streamBuffers: Map<string, string>;
  updateStreamBuffer: (participantId: string, chunk: string) => void;
  flushStreamBuffer: (participantId: string) => string;

  // UI toggles
  costTrackerExpanded: boolean;
  toggleCostTracker: () => void;

  // Optimistic state
  pendingRounds: DebateRound[];
  addPendingRound: (round: DebateRound) => void;
  clearPendingRounds: () => void;
}

export const useDebateUIStore = create<DebateUIState>()(
  devtools((set, get) => ({
    streamBuffers: new Map(),
    costTrackerExpanded: false,
    pendingRounds: [],

    updateStreamBuffer: (participantId, chunk) =>
      set((state) => {
        const newBuffers = new Map(state.streamBuffers);
        const current = newBuffers.get(participantId) || '';
        newBuffers.set(participantId, current + chunk);
        return { streamBuffers: newBuffers };
      }),

    flushStreamBuffer: (participantId) => {
      const buffer = get().streamBuffers.get(participantId) || '';
      set((state) => {
        const newBuffers = new Map(state.streamBuffers);
        newBuffers.delete(participantId);
        return { streamBuffers: newBuffers };
      });
      return buffer;
    },

    toggleCostTracker: () =>
      set((state) => ({
        costTrackerExpanded: !state.costTrackerExpanded
      })),

    addPendingRound: (round) =>
      set((state) => ({
        pendingRounds: [...state.pendingRounds, round]
      })),

    clearPendingRounds: () =>
      set({ pendingRounds: [] })
  }))
);
```

---

## Component Communication Patterns

### Pattern 1: XState → Component (State-based rendering)

```typescript
const [state, send] = useMachine(debateMachine);

// Render based on state
{state.matches('debating') && <DebateArena />}
{state.matches('completed') && <DebateResults />}
```

### Pattern 2: SSE → XState (Event routing)

```typescript
useEffect(() => {
  const eventSource = useDebateSSE(debateId);

  eventSource.addEventListener('participant', (e) => {
    const data = JSON.parse(e.data);
    send({ type: 'STREAM_CHUNK', participantId: data.participantId, chunk: data.chunk });
  });

  return () => eventSource.close();
}, [debateId, send]);
```

### Pattern 3: Component → XState (User actions)

```typescript
<Button onClick={() => send({ type: 'PAUSE' })}>
  Pause Debate
</Button>
```

### Pattern 4: Zustand ↔ Component (UI state)

```typescript
const { streamBuffers, updateStreamBuffer } = useDebateUIStore();

// Batch stream updates
useEffect(() => {
  const interval = setInterval(() => {
    const buffer = streamBuffers.get(participantId);
    if (buffer) {
      setDisplayedContent(buffer);
    }
  }, 100); // Batch every 100ms

  return () => clearInterval(interval);
}, [participantId, streamBuffers]);
```

---

## Responsive Design Breakpoints

```css
/* Mobile: < 768px */
- Single column participant panels
- Stacked layout
- Floating cost tracker collapsed by default

/* Tablet: 768px - 1024px */
- 2-column participant grid
- Side-by-side debaters

/* Desktop: > 1024px */
- 3-4 column grid for 3-4 participants
- Full feature set
- Expanded cost tracker
```

---

## Accessibility Features

1. **Keyboard Navigation**:
   - Tab through controls
   - Arrow keys for round timeline
   - Escape to close modals

2. **Screen Readers**:
   - ARIA labels on all interactive elements
   - Live regions for streaming updates
   - Semantic HTML structure

3. **Visual**:
   - High contrast mode support
   - Configurable font sizes
   - Color-blind friendly palette options

4. **Reduced Motion**:
   - Disable typewriter effect
   - Instant text rendering
   - Simplified animations

---

## Performance Optimizations

1. **Virtual Scrolling**: Use `@tanstack/react-virtual` for long round lists
2. **Memoization**: Wrap expensive components in `React.memo`
3. **Lazy Loading**: Code-split debate route from chat route
4. **Stream Batching**: Buffer SSE chunks every 100ms
5. **Debounced Updates**: Throttle cost tracker updates
6. **Suspense Boundaries**: Lazy load judge panel and results

```typescript
// Lazy load heavy components
const DebateResults = lazy(() => import('@/components/debate/DebateResults'));
const JudgePanel = lazy(() => import('@/components/debate/JudgePanel'));

<Suspense fallback={<LoadingSpinner />}>
  <DebateResults />
</Suspense>
```

---

## Testing Strategy

### Component Tests (Vitest + Testing Library)

```typescript
// DebateContainer.test.tsx
describe('DebateContainer', () => {
  it('shows config panel in idle state', () => {
    render(<DebateContainer />);
    expect(screen.getByText('Configure Debate')).toBeInTheDocument();
  });

  it('transitions to arena on start', async () => {
    const { rerender } = render(<DebateContainer />);
    const startButton = screen.getByText('Start Debate');

    await userEvent.click(startButton);

    await waitFor(() => {
      expect(screen.getByText('Debate Arena')).toBeInTheDocument();
    });
  });
});
```

### Integration Tests

```typescript
// debate-flow.test.tsx
describe('Full Debate Flow', () => {
  it('completes full debate lifecycle', async () => {
    // Mock SSE
    const mockSSE = createMockSSE();

    render(<DebateContainer />);

    // Configure
    await configureDebate();

    // Start
    await userEvent.click(screen.getByText('Start Debate'));

    // Simulate SSE events
    mockSSE.emit('participant', { /* ... */ });
    mockSSE.emit('verdict', { /* ... */ });

    // Verify completion
    expect(screen.getByText('Debate Complete')).toBeInTheDocument();
  });
});
```

---

## Next Steps

1. Implement XState machine in `/machines/debate-machine.ts`
2. Create core components: `DebateContainer`, `ParticipantPanel`, `CostTracker`
3. Build SSE integration hook: `useDebateSSE`
4. Implement Zustand UI store for stream buffering
5. Add component tests for critical paths
6. Create storybook stories for visual testing
7. Implement responsive layouts with Tailwind
