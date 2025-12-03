/**
 * Debate Types - Multi-LLM Debate Engine
 * Phase 2 Implementation
 */

export type DebateStatus =
  | "CONFIGURING"
  | "RUNNING"
  | "PAUSED"
  | "COMPLETED"
  | "ERROR";

export type DebateFormat =
  | "free-form"
  | "structured"
  | "round-limited"
  | "convergence";

export interface LLMModel {
  id: string;
  name: string;
  provider: "anthropic" | "openai" | "google" | "meta";
  cost_per_1k_tokens: number;
}

export interface Participant {
  id: string;
  model: LLMModel;
  persona: string;
  color: string; // For UI identification
  position?: string; // For structured debates (pro/con)
}

export interface DebateConfig {
  topic: string;
  participants: Participant[];
  format: DebateFormat;
  judgeModel?: LLMModel;
  maxRounds?: number; // For round-limited format
  convergenceThreshold?: number; // For convergence format (0-1)
  autoAssignPersonas: boolean;
}

export interface ResponseMetadata {
  participantId: string;
  tokens: number;
  cost: number;
  latency: number; // milliseconds
  timestamp: Date;
}

export interface DebateResponse {
  participantId: string;
  roundNumber: number;
  content: string;
  isStreaming?: boolean;
  metadata: ResponseMetadata;
}

export interface JudgeVerdict {
  roundNumber: number;
  winner?: string; // participantId
  reasoning: string;
  consensus: boolean;
  confidence: number; // 0-1
  timestamp: Date;
}

export interface DebateRound {
  number: number;
  responses: DebateResponse[];
  verdict?: JudgeVerdict;
  completed: boolean;
}

export interface CostBreakdown {
  participantId: string;
  participantName: string;
  tokens: number;
  cost: number;
}

export interface DebateMetrics {
  totalCost: number;
  totalTokens: number;
  totalRounds: number;
  duration: number; // milliseconds
  costByParticipant: CostBreakdown[];
}

export interface DebateStoreState {
  config: DebateConfig | null;
  status: DebateStatus;
  rounds: DebateRound[];
  currentRound: number;
  activeStreams: Map<string, string>;
  metrics: DebateMetrics;
  error?: string;

  // Actions
  setConfig: (config: DebateConfig) => void;
  startDebate: () => Promise<void>;
  pauseDebate: () => void;
  resumeDebate: () => void;
  stopDebate: () => void;

  // Streaming
  updateStream: (participantId: string, text: string, tokens: number, cost: number) => void;
  completeStream: (participantId: string) => void;

  // Round management
  completeRound: () => void;
  addJudgeVerdict: (verdict: JudgeVerdict) => void;

  // Export
  exportDebate: (format: "markdown" | "json") => string;

  // Reset
  resetDebate: () => void;
}

export interface StreamingState {
  participantId: string;
  currentText: string;
  isStreaming: boolean;
  error?: Error;
}

export interface ParallelStreamConfig {
  endpoint: string;
  participantId: string;
  roundNumber: number;
  context: string; // Previous round context
}
