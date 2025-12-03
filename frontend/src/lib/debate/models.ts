/**
 * Available LLM Models for Debate
 * Phase 2 Implementation
 */

import type { LLMModel } from "@/types/debate";

export const AVAILABLE_MODELS: LLMModel[] = [
  // Anthropic Claude Models
  {
    id: "claude-3-5-sonnet-20241022",
    name: "Claude 3.5 Sonnet",
    provider: "anthropic",
    cost_per_1k_tokens: 0.003,
  },
  {
    id: "claude-3-5-haiku-20241022",
    name: "Claude 3.5 Haiku",
    provider: "anthropic",
    cost_per_1k_tokens: 0.001,
  },
  {
    id: "claude-3-opus-20240229",
    name: "Claude 3 Opus",
    provider: "anthropic",
    cost_per_1k_tokens: 0.015,
  },

  // OpenAI Models
  {
    id: "gpt-4-turbo",
    name: "GPT-4 Turbo",
    provider: "openai",
    cost_per_1k_tokens: 0.01,
  },
  {
    id: "gpt-4",
    name: "GPT-4",
    provider: "openai",
    cost_per_1k_tokens: 0.03,
  },
  {
    id: "gpt-3.5-turbo",
    name: "GPT-3.5 Turbo",
    provider: "openai",
    cost_per_1k_tokens: 0.002,
  },

  // Google Models
  {
    id: "gemini-pro",
    name: "Gemini Pro",
    provider: "google",
    cost_per_1k_tokens: 0.0005,
  },
  {
    id: "gemini-pro-vision",
    name: "Gemini Pro Vision",
    provider: "google",
    cost_per_1k_tokens: 0.002,
  },

  // Meta Models
  {
    id: "llama-3-70b",
    name: "Llama 3 70B",
    provider: "meta",
    cost_per_1k_tokens: 0.0009,
  },
  {
    id: "llama-3-8b",
    name: "Llama 3 8B",
    provider: "meta",
    cost_per_1k_tokens: 0.0002,
  },
];

// Participant colors for UI
export const PARTICIPANT_COLORS = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#10b981", // green
  "#f59e0b", // amber
  "#8b5cf6", // purple
  "#ec4899", // pink
];

// Default personas by position
export const DEFAULT_PERSONAS: Record<string, string> = {
  pro: "Advocate supporting the proposition with logical arguments and evidence",
  con: "Skeptic challenging the proposition with counterarguments and scrutiny",
  neutral: "Balanced analyst examining both perspectives objectively",
  expert: "Domain expert providing specialized knowledge and insights",
};
