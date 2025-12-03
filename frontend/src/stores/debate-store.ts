/**
 * Debate Store - Multi-LLM Debate State Management
 * Phase 2 Implementation using Zustand + Immer
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type {
  DebateConfig,
  DebateStatus,
  DebateRound,
  DebateResponse,
  JudgeVerdict,
  DebateMetrics,
  ResponseMetadata,
} from "@/types/debate";

interface DebateStore {
  // Configuration
  config: DebateConfig | null;
  status: DebateStatus;

  // Rounds
  rounds: DebateRound[];
  currentRound: number;

  // Real-time streaming
  activeStreams: Map<string, string>;
  streamingMetadata: Map<string, Partial<ResponseMetadata>>;

  // Metrics
  metrics: DebateMetrics;

  // Error state
  error?: string;

  // Actions
  setConfig: (config: DebateConfig) => void;
  startDebate: () => Promise<void>;
  pauseDebate: () => void;
  resumeDebate: () => void;
  stopDebate: () => void;

  // Streaming updates
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

const initialMetrics: DebateMetrics = {
  totalCost: 0,
  totalTokens: 0,
  totalRounds: 0,
  duration: 0,
  costByParticipant: [],
};

export const useDebateStore = create<DebateStore>()(
  devtools(
    immer((set, get) => ({
      // Initial state
      config: null,
      status: "CONFIGURING",
      rounds: [],
      currentRound: 0,
      activeStreams: new Map(),
      streamingMetadata: new Map(),
      metrics: initialMetrics,
      error: undefined,

      // Configuration
      setConfig: (config) =>
        set((state) => {
          state.config = config;
          state.status = "CONFIGURING";

          // Initialize cost breakdown for each participant
          state.metrics.costByParticipant = config.participants.map(p => ({
            participantId: p.id,
            participantName: p.model.name,
            tokens: 0,
            cost: 0,
          }));
        }),

      // Start debate
      startDebate: async () => {
        const { config } = get();
        if (!config) {
          set((state) => {
            state.error = "No configuration set";
          });
          return;
        }

        set((state) => {
          state.status = "RUNNING";
          state.currentRound = 1;
          state.error = undefined;

          // Initialize first round
          state.rounds = [{
            number: 1,
            responses: [],
            completed: false,
          }];

          // Clear streams
          state.activeStreams.clear();
          state.streamingMetadata.clear();
        });
      },

      // Pause/Resume/Stop
      pauseDebate: () =>
        set((state) => {
          if (state.status === "RUNNING") {
            state.status = "PAUSED";
          }
        }),

      resumeDebate: () =>
        set((state) => {
          if (state.status === "PAUSED") {
            state.status = "RUNNING";
          }
        }),

      stopDebate: () =>
        set((state) => {
          state.status = "COMPLETED";
          state.activeStreams.clear();
          state.streamingMetadata.clear();
        }),

      // Streaming updates
      updateStream: (participantId, text, tokens, cost) =>
        set((state) => {
          // Update streaming text
          state.activeStreams.set(participantId, text);

          // Update metadata
          const metadata = state.streamingMetadata.get(participantId) || {};
          metadata.tokens = tokens;
          metadata.cost = cost;
          state.streamingMetadata.set(participantId, metadata);

          // Update total metrics
          state.metrics.totalTokens = Array.from(state.streamingMetadata.values())
            .reduce((sum, m) => sum + (m.tokens || 0), 0);
          state.metrics.totalCost = Array.from(state.streamingMetadata.values())
            .reduce((sum, m) => sum + (m.cost || 0), 0);
        }),

      completeStream: (participantId) =>
        set((state) => {
          const text = state.activeStreams.get(participantId) || "";
          const metadata = state.streamingMetadata.get(participantId);

          if (!metadata) return;

          // Find current round
          const currentRoundData = state.rounds.find(r => r.number === state.currentRound);
          if (!currentRoundData) return;

          // Add completed response to round
          const response: DebateResponse = {
            participantId,
            roundNumber: state.currentRound,
            content: text,
            metadata: {
              participantId,
              tokens: metadata.tokens || 0,
              cost: metadata.cost || 0,
              latency: metadata.latency || 0,
              timestamp: new Date(),
            },
          };

          currentRoundData.responses.push(response);

          // Update participant cost breakdown
          const participantCost = state.metrics.costByParticipant.find(
            p => p.participantId === participantId
          );
          if (participantCost) {
            participantCost.tokens += metadata.tokens || 0;
            participantCost.cost += metadata.cost || 0;
          }

          // Remove from active streams
          state.activeStreams.delete(participantId);
          state.streamingMetadata.delete(participantId);

          // Check if round is complete (all participants responded)
          if (state.config && currentRoundData.responses.length === state.config.participants.length) {
            currentRoundData.completed = true;
          }
        }),

      // Round management
      completeRound: () =>
        set((state) => {
          const currentRoundData = state.rounds.find(r => r.number === state.currentRound);
          if (currentRoundData) {
            currentRoundData.completed = true;
            state.metrics.totalRounds = state.currentRound;
          }

          // Check if debate should continue
          const { config } = state;
          if (!config) return;

          // Check max rounds limit
          if (config.maxRounds && state.currentRound >= config.maxRounds) {
            state.status = "COMPLETED";
            return;
          }

          // Start next round
          state.currentRound += 1;
          state.rounds.push({
            number: state.currentRound,
            responses: [],
            completed: false,
          });
        }),

      addJudgeVerdict: (verdict) =>
        set((state) => {
          const round = state.rounds.find(r => r.number === verdict.roundNumber);
          if (round) {
            round.verdict = verdict;

            // Check for convergence (end debate if consensus reached)
            if (verdict.consensus && state.config?.format === "convergence") {
              state.status = "COMPLETED";
            }
          }
        }),

      // Export
      exportDebate: (format) => {
        const state = get();

        if (format === "json") {
          return JSON.stringify({
            config: state.config,
            rounds: state.rounds,
            metrics: state.metrics,
            exportedAt: new Date().toISOString(),
          }, null, 2);
        }

        // Markdown format
        let markdown = `# Debate: ${state.config?.topic || "Untitled"}\n\n`;
        markdown += `**Format:** ${state.config?.format}\n`;
        markdown += `**Participants:** ${state.config?.participants.map(p => p.model.name).join(", ")}\n`;
        markdown += `**Total Rounds:** ${state.metrics.totalRounds}\n`;
        markdown += `**Total Cost:** $${state.metrics.totalCost.toFixed(4)}\n\n`;
        markdown += `---\n\n`;

        state.rounds.forEach((round) => {
          markdown += `## Round ${round.number}\n\n`;

          round.responses.forEach((response) => {
            const participant = state.config?.participants.find(p => p.id === response.participantId);
            markdown += `### ${participant?.model.name} (${participant?.persona})\n\n`;
            markdown += `${response.content}\n\n`;
            markdown += `*Tokens: ${response.metadata.tokens}, Cost: $${response.metadata.cost.toFixed(4)}*\n\n`;
          });

          if (round.verdict) {
            markdown += `### Judge's Verdict\n\n`;
            markdown += `**Winner:** ${round.verdict.winner || "No clear winner"}\n\n`;
            markdown += `**Reasoning:** ${round.verdict.reasoning}\n\n`;
            markdown += `**Consensus:** ${round.verdict.consensus ? "Yes" : "No"}\n\n`;
          }

          markdown += `---\n\n`;
        });

        return markdown;
      },

      // Reset
      resetDebate: () =>
        set((state) => {
          state.config = null;
          state.status = "CONFIGURING";
          state.rounds = [];
          state.currentRound = 0;
          state.activeStreams.clear();
          state.streamingMetadata.clear();
          state.metrics = initialMetrics;
          state.error = undefined;
        }),
    })),
    { name: "DebateStore" }
  )
);
