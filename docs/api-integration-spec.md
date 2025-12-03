# Quorum API Integration Specification

## Executive Summary

This specification provides a comprehensive design for a unified API abstraction layer supporting multiple LLM providers (Anthropic Claude, OpenAI GPT, Google Gemini, Mistral AI) for the Quorum debate platform. The design prioritizes streaming consistency, structured outputs for judge agents, context management, and cost tracking while supporting both client-side and optional backend architectures.

**Last Updated**: November 2025
**Author**: API Integration Specialist

---

## 1. Provider Capability Matrix

### 1.1 Feature Comparison

| Feature | Anthropic Claude | OpenAI GPT | Google Gemini | Mistral AI |
|---------|-----------------|------------|---------------|------------|
| **Official TypeScript SDK** | ✅ Yes (`@anthropic-ai/sdk`) | ✅ Yes (`openai`) | ✅ Yes (`@google/genai`) | ✅ Yes (`@mistralai/mistralai`) |
| **Streaming Protocol** | SSE (Server-Sent Events) | SSE | SSE | SSE |
| **Streaming API Pattern** | `messages.stream()` + event handlers | `create({ stream: true })` + async iterator | `generateContentStream()` + async iterator | `chatStream()` + async iterator |
| **Structured Output (JSON Schema)** | ✅ Yes (Beta: Nov 2025) | ✅ Yes (Structured Outputs) | ✅ Yes (Native support) | ✅ Yes (JSON Schema mode) |
| **JSON Mode Implementation** | `output_format` with schema | `response_format` with schema | `responseMimeType: "application/json"` | `response_format: { type: "json_schema" }` |
| **Streaming + Structured Output** | ✅ Supported | ⚠️ Limited (not with `.parse()`) | ✅ Supported | ✅ Supported |
| **Token Counting** | API call (`countTokens`) | tiktoken library (client-side) | API call (`countTokens`) | Approximate with tiktoken |
| **Max Context Window** | 200K tokens (Sonnet 4.5) | 128K tokens (GPT-4o) | 1M tokens (Gemini 1.5 Pro) | 128K tokens (Mistral Large) |
| **Rate Limits** | Tier-based (tokens/min) | Tier-based (tokens/min + requests/min) | Tokens/min + requests/min | Tokens/min + requests/min |
| **Cost Tracking** | Via `usage` in response | Via `usage` in response | Via `usageMetadata` in response | Via `usage` in response |
| **SDK Quality** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Very Good | ⭐⭐⭐⭐ Very Good |
| **Browser Support** | ⚠️ Server-side recommended | ⚠️ Server-side recommended | ✅ Yes (with API key) | ⚠️ Server-side recommended |

### 1.2 Model Recommendations for Quorum

**Debater Models (High Quality):**
- Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- GPT-4o (`gpt-4o`)
- Gemini 2.5 Flash (`gemini-2.5-flash`)
- Mistral Large (`mistral-large-latest`)

**Debater Models (Cost-Effective):**
- Claude Haiku 4.5 (when available)
- GPT-4o Mini (`gpt-4o-mini`)
- Gemini 2.5 Flash (`gemini-2.5-flash`)
- Mistral Small (`mistral-small-latest`)

**Judge Models (Structured Output Required):**
- Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- GPT-4o (`gpt-4o`)
- Gemini 2.5 Flash (`gemini-2.5-flash`)
- Mistral Large (`mistral-large-latest`)

---

## 2. Unified Interface Design

### 2.1 Core TypeScript Types

```typescript
// ============================================================================
// Core Provider Types
// ============================================================================

export type ProviderType = 'anthropic' | 'openai' | 'google' | 'mistral';

export interface ProviderConfig {
  type: ProviderType;
  apiKey: string;
  model: string;
  endpoint?: string; // Optional custom endpoint
}

// ============================================================================
// Unified Message Format
// ============================================================================

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: {
    participant?: string; // For debate context (e.g., "Claude (Pro-Space)")
    timestamp?: number;
    tokens?: number;
  };
}

export interface ConversationHistory {
  messages: Message[];
  totalTokens: number;
  estimatedCost: number;
}

// ============================================================================
// Completion Request
// ============================================================================

export interface CompletionRequest {
  messages: Message[];
  maxTokens?: number;
  temperature?: number;
  topP?: number;
  stopSequences?: string[];
  metadata?: Record<string, unknown>;
}

export interface StreamingCompletionRequest extends CompletionRequest {
  onChunk?: (chunk: StreamChunk) => void;
  onComplete?: (response: CompletionResponse) => void;
  onError?: (error: ProviderError) => void;
}

// ============================================================================
// Structured Output Request (for Judge)
// ============================================================================

export interface StructuredOutputRequest<T = unknown> extends CompletionRequest {
  schema: JSONSchema;
  schemaName?: string; // For provider-specific naming
}

export interface JSONSchema {
  type: string;
  properties?: Record<string, unknown>;
  required?: string[];
  additionalProperties?: boolean;
  [key: string]: unknown;
}

// ============================================================================
// Response Types
// ============================================================================

export interface CompletionResponse {
  id: string;
  content: string;
  model: string;
  provider: ProviderType;
  usage: TokenUsage;
  finishReason: 'stop' | 'length' | 'error';
  metadata?: Record<string, unknown>;
}

export interface StructuredOutputResponse<T = unknown> extends CompletionResponse {
  structuredData: T;
  validationErrors?: string[];
}

export interface StreamChunk {
  delta: string;
  accumulated: string;
  usage?: Partial<TokenUsage>;
  isDone: boolean;
}

// ============================================================================
// Token Usage & Cost Tracking
// ============================================================================

export interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  estimatedCost?: number; // In USD
}

export interface CostEstimate {
  provider: ProviderType;
  model: string;
  inputCost: number; // Per 1M tokens
  outputCost: number; // Per 1M tokens
}

// ============================================================================
// Error Handling
// ============================================================================

export interface ProviderError {
  provider: ProviderType;
  type: 'rate_limit' | 'context_length' | 'api_error' | 'network' | 'auth' | 'validation';
  message: string;
  statusCode?: number;
  retryable: boolean;
  retryAfter?: number; // Seconds to wait before retry
  originalError?: unknown;
}
```

### 2.2 Provider Interface

```typescript
// ============================================================================
// Base Provider Interface
// ============================================================================

export interface LLMProvider {
  readonly type: ProviderType;
  readonly config: ProviderConfig;

  // Core completion methods
  complete(request: CompletionRequest): Promise<CompletionResponse>;
  streamComplete(request: StreamingCompletionRequest): Promise<void>;

  // Structured output methods (for judge)
  structuredComplete<T = unknown>(
    request: StructuredOutputRequest<T>
  ): Promise<StructuredOutputResponse<T>>;

  streamStructuredComplete<T = unknown>(
    request: StructuredOutputRequest<T>,
    onChunk: (chunk: StreamChunk) => void
  ): Promise<StructuredOutputResponse<T>>;

  // Token and cost management
  countTokens(text: string): Promise<number>;
  estimateCost(usage: TokenUsage): number;

  // Health and validation
  validateApiKey(): Promise<boolean>;
  checkRateLimit(): Promise<RateLimitStatus>;
}

export interface RateLimitStatus {
  requestsRemaining?: number;
  tokensRemaining?: number;
  resetAt?: Date;
  limitTier?: string;
}
```

### 2.3 Unified Provider Manager

```typescript
// ============================================================================
// Provider Manager - Central Orchestration
// ============================================================================

export class ProviderManager {
  private providers: Map<string, LLMProvider>;
  private rateLimitQueue: RequestQueue;
  private costTracker: CostTracker;

  constructor(private config: ProviderManagerConfig) {
    this.providers = new Map();
    this.rateLimitQueue = new RequestQueue(config.queueConfig);
    this.costTracker = new CostTracker();
  }

  // Provider registration
  registerProvider(id: string, config: ProviderConfig): LLMProvider {
    const provider = this.createProvider(config);
    this.providers.set(id, provider);
    return provider;
  }

  getProvider(id: string): LLMProvider | undefined {
    return this.providers.get(id);
  }

  // Intelligent request routing
  async routeRequest(
    providerId: string,
    request: CompletionRequest
  ): Promise<CompletionResponse> {
    const provider = this.getProvider(providerId);
    if (!provider) {
      throw new Error(`Provider ${providerId} not found`);
    }

    // Queue management for rate limiting
    return this.rateLimitQueue.enqueue(async () => {
      const response = await provider.complete(request);
      this.costTracker.track(provider.type, response.usage);
      return response;
    });
  }

  // Concurrent debate round support
  async executeParallelDebateRound(
    participants: Array<{ providerId: string; request: CompletionRequest }>
  ): Promise<CompletionResponse[]> {
    // Group by provider to respect rate limits
    const grouped = this.groupByProvider(participants);

    // Execute with provider-specific concurrency limits
    const results = await Promise.all(
      Array.from(grouped.entries()).map(([providerId, requests]) =>
        this.executeProviderBatch(providerId, requests)
      )
    );

    return results.flat();
  }

  private async executeProviderBatch(
    providerId: string,
    requests: CompletionRequest[]
  ): Promise<CompletionResponse[]> {
    const provider = this.getProvider(providerId);
    if (!provider) throw new Error(`Provider ${providerId} not found`);

    // Respect rate limits with staggered execution
    const concurrencyLimit = this.getConcurrencyLimit(provider.type);
    return this.rateLimitQueue.executeBatch(requests, concurrencyLimit, async (req) => {
      const response = await provider.complete(req);
      this.costTracker.track(provider.type, response.usage);
      return response;
    });
  }

  // Cost tracking and reporting
  getTotalCost(): number {
    return this.costTracker.getTotalCost();
  }

  getCostByProvider(): Map<ProviderType, number> {
    return this.costTracker.getCostByProvider();
  }

  // Utility methods
  private getConcurrencyLimit(provider: ProviderType): number {
    const limits: Record<ProviderType, number> = {
      anthropic: 5,
      openai: 5,
      google: 5,
      mistral: 3,
    };
    return limits[provider];
  }

  private groupByProvider(
    participants: Array<{ providerId: string; request: CompletionRequest }>
  ): Map<string, CompletionRequest[]> {
    const grouped = new Map<string, CompletionRequest[]>();
    for (const { providerId, request } of participants) {
      if (!grouped.has(providerId)) {
        grouped.set(providerId, []);
      }
      grouped.get(providerId)!.push(request);
    }
    return grouped;
  }

  private createProvider(config: ProviderConfig): LLMProvider {
    switch (config.type) {
      case 'anthropic':
        return new AnthropicProvider(config);
      case 'openai':
        return new OpenAIProvider(config);
      case 'google':
        return new GoogleProvider(config);
      case 'mistral':
        return new MistralProvider(config);
      default:
        throw new Error(`Unsupported provider: ${config.type}`);
    }
  }
}

export interface ProviderManagerConfig {
  queueConfig: QueueConfig;
  enableCostTracking?: boolean;
  enableRateLimitQueue?: boolean;
}

export interface QueueConfig {
  maxConcurrentRequests: number;
  retryAttempts: number;
  retryBackoffMs: number;
  timeoutMs: number;
}
```

---

## 3. Streaming Abstraction Architecture

### 3.1 Unified Streaming Interface

```typescript
// ============================================================================
// Streaming Abstraction
// ============================================================================

export interface StreamHandler {
  onStart?: () => void;
  onChunk: (chunk: StreamChunk) => void;
  onComplete: (response: CompletionResponse) => void;
  onError: (error: ProviderError) => void;
}

export abstract class BaseStreamingProvider implements LLMProvider {
  abstract readonly type: ProviderType;
  abstract readonly config: ProviderConfig;

  // Standardized streaming implementation
  async streamComplete(request: StreamingCompletionRequest): Promise<void> {
    let accumulated = '';
    let usage: TokenUsage | undefined;

    try {
      request.onChunk?.({ delta: '', accumulated: '', isDone: false });

      const stream = await this.createStream(request);

      for await (const chunk of stream) {
        const delta = this.extractDelta(chunk);
        accumulated += delta;

        const streamChunk: StreamChunk = {
          delta,
          accumulated,
          usage: this.extractUsage(chunk),
          isDone: false,
        };

        request.onChunk?.(streamChunk);
      }

      // Final chunk
      const finalChunk: StreamChunk = {
        delta: '',
        accumulated,
        isDone: true,
        usage,
      };
      request.onChunk?.(finalChunk);

      // Build complete response
      const response: CompletionResponse = {
        id: this.generateId(),
        content: accumulated,
        model: this.config.model,
        provider: this.type,
        usage: usage || { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
        finishReason: 'stop',
      };

      request.onComplete?.(response);
    } catch (error) {
      const providerError = this.handleError(error);
      request.onError?.(providerError);
      throw providerError;
    }
  }

  // Provider-specific implementations
  protected abstract createStream(request: CompletionRequest): Promise<AsyncIterable<unknown>>;
  protected abstract extractDelta(chunk: unknown): string;
  protected abstract extractUsage(chunk: unknown): Partial<TokenUsage> | undefined;
  protected abstract handleError(error: unknown): ProviderError;
  protected abstract generateId(): string;

  // Shared utilities
  protected async complete(request: CompletionRequest): Promise<CompletionResponse> {
    throw new Error('Must be implemented by provider');
  }

  protected async countTokens(text: string): Promise<number> {
    throw new Error('Must be implemented by provider');
  }

  protected estimateCost(usage: TokenUsage): number {
    throw new Error('Must be implemented by provider');
  }

  protected async validateApiKey(): Promise<boolean> {
    throw new Error('Must be implemented by provider');
  }

  protected async checkRateLimit(): Promise<RateLimitStatus> {
    throw new Error('Must be implemented by provider');
  }

  protected async structuredComplete<T>(
    request: StructuredOutputRequest<T>
  ): Promise<StructuredOutputResponse<T>> {
    throw new Error('Must be implemented by provider');
  }

  protected async streamStructuredComplete<T>(
    request: StructuredOutputRequest<T>,
    onChunk: (chunk: StreamChunk) => void
  ): Promise<StructuredOutputResponse<T>> {
    throw new Error('Must be implemented by provider');
  }
}
```

### 3.2 Provider-Specific Implementations

```typescript
// ============================================================================
// Anthropic Implementation
// ============================================================================

import Anthropic from '@anthropic-ai/sdk';

export class AnthropicProvider extends BaseStreamingProvider {
  readonly type: ProviderType = 'anthropic';
  private client: Anthropic;

  constructor(readonly config: ProviderConfig) {
    super();
    this.client = new Anthropic({
      apiKey: config.apiKey,
    });
  }

  protected async createStream(request: CompletionRequest): Promise<AsyncIterable<unknown>> {
    const stream = this.client.messages.stream({
      model: this.config.model,
      max_tokens: request.maxTokens || 4096,
      temperature: request.temperature,
      messages: request.messages.map((m) => ({
        role: m.role === 'system' ? 'user' : m.role,
        content: m.content,
      })),
    });

    return stream;
  }

  protected extractDelta(chunk: any): string {
    if (chunk.type === 'content_block_delta' && chunk.delta?.type === 'text_delta') {
      return chunk.delta.text || '';
    }
    return '';
  }

  protected extractUsage(chunk: any): Partial<TokenUsage> | undefined {
    if (chunk.message?.usage) {
      return {
        promptTokens: chunk.message.usage.input_tokens,
        completionTokens: chunk.message.usage.output_tokens,
        totalTokens: chunk.message.usage.input_tokens + chunk.message.usage.output_tokens,
      };
    }
    return undefined;
  }

  protected async structuredComplete<T>(
    request: StructuredOutputRequest<T>
  ): Promise<StructuredOutputResponse<T>> {
    // Anthropic structured output (Beta: Nov 2025)
    const response = await this.client.messages.create({
      model: this.config.model,
      max_tokens: request.maxTokens || 4096,
      messages: request.messages.map((m) => ({
        role: m.role === 'system' ? 'user' : m.role,
        content: m.content,
      })),
      // @ts-ignore - Beta feature
      output_format: {
        type: 'json_schema',
        json_schema: request.schema,
      },
      // Required beta header
      headers: {
        'anthropic-beta': 'structured-outputs-2025-11-13',
      },
    });

    const structuredData = JSON.parse(response.content[0].text);

    return {
      id: response.id,
      content: response.content[0].text,
      structuredData,
      model: response.model,
      provider: this.type,
      usage: {
        promptTokens: response.usage.input_tokens,
        completionTokens: response.usage.output_tokens,
        totalTokens: response.usage.input_tokens + response.usage.output_tokens,
      },
      finishReason: response.stop_reason === 'end_turn' ? 'stop' : 'length',
    };
  }

  protected async countTokens(text: string): Promise<number> {
    // Anthropic provides token counting API
    const response = await this.client.messages.countTokens({
      model: this.config.model,
      messages: [{ role: 'user', content: text }],
    });
    return response.input_tokens;
  }

  protected generateId(): string {
    return `anthropic_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  protected handleError(error: unknown): ProviderError {
    const err = error as any;
    return {
      provider: this.type,
      type: this.classifyError(err),
      message: err.message || 'Unknown error',
      statusCode: err.status,
      retryable: err.status === 429 || err.status >= 500,
      retryAfter: err.headers?.['retry-after'] ? parseInt(err.headers['retry-after']) : undefined,
      originalError: error,
    };
  }

  private classifyError(error: any): ProviderError['type'] {
    if (error.status === 429) return 'rate_limit';
    if (error.status === 401 || error.status === 403) return 'auth';
    if (error.message?.includes('context')) return 'context_length';
    if (error.status >= 500) return 'api_error';
    return 'network';
  }
}

// ============================================================================
// OpenAI Implementation
// ============================================================================

import OpenAI from 'openai';
import { encoding_for_model } from 'js-tiktoken';

export class OpenAIProvider extends BaseStreamingProvider {
  readonly type: ProviderType = 'openai';
  private client: OpenAI;
  private encoder: any;

  constructor(readonly config: ProviderConfig) {
    super();
    this.client = new OpenAI({
      apiKey: config.apiKey,
    });
    // Initialize tiktoken for token counting
    this.encoder = encoding_for_model('gpt-4o');
  }

  protected async createStream(request: CompletionRequest): Promise<AsyncIterable<unknown>> {
    const stream = await this.client.chat.completions.create({
      model: this.config.model,
      max_tokens: request.maxTokens,
      temperature: request.temperature,
      top_p: request.topP,
      messages: request.messages,
      stream: true,
    });

    return stream;
  }

  protected extractDelta(chunk: any): string {
    return chunk.choices?.[0]?.delta?.content || '';
  }

  protected extractUsage(chunk: any): Partial<TokenUsage> | undefined {
    if (chunk.usage) {
      return {
        promptTokens: chunk.usage.prompt_tokens,
        completionTokens: chunk.usage.completion_tokens,
        totalTokens: chunk.usage.total_tokens,
      };
    }
    return undefined;
  }

  protected async structuredComplete<T>(
    request: StructuredOutputRequest<T>
  ): Promise<StructuredOutputResponse<T>> {
    const response = await this.client.chat.completions.create({
      model: this.config.model,
      max_tokens: request.maxTokens || 4096,
      messages: request.messages,
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: request.schemaName || 'response',
          schema: request.schema,
          strict: true,
        },
      },
    });

    const structuredData = JSON.parse(response.choices[0].message.content || '{}');

    return {
      id: response.id,
      content: response.choices[0].message.content || '',
      structuredData,
      model: response.model,
      provider: this.type,
      usage: {
        promptTokens: response.usage?.prompt_tokens || 0,
        completionTokens: response.usage?.completion_tokens || 0,
        totalTokens: response.usage?.total_tokens || 0,
      },
      finishReason: response.choices[0].finish_reason === 'stop' ? 'stop' : 'length',
    };
  }

  protected async countTokens(text: string): Promise<number> {
    const tokens = this.encoder.encode(text);
    return tokens.length;
  }

  protected estimateCost(usage: TokenUsage): number {
    // GPT-4o pricing (as of 2025)
    const inputCostPer1M = 2.50;
    const outputCostPer1M = 10.00;

    const inputCost = (usage.promptTokens / 1_000_000) * inputCostPer1M;
    const outputCost = (usage.completionTokens / 1_000_000) * outputCostPer1M;

    return inputCost + outputCost;
  }

  protected generateId(): string {
    return `openai_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  protected handleError(error: unknown): ProviderError {
    const err = error as any;
    return {
      provider: this.type,
      type: this.classifyError(err),
      message: err.message || 'Unknown error',
      statusCode: err.status,
      retryable: err.status === 429 || err.status >= 500,
      retryAfter: err.headers?.['retry-after'] ? parseInt(err.headers['retry-after']) : undefined,
      originalError: error,
    };
  }

  private classifyError(error: any): ProviderError['type'] {
    if (error.status === 429) return 'rate_limit';
    if (error.status === 401 || error.status === 403) return 'auth';
    if (error.code === 'context_length_exceeded') return 'context_length';
    if (error.status >= 500) return 'api_error';
    return 'network';
  }
}

// ============================================================================
// Google Gemini Implementation
// ============================================================================

import { GoogleGenAI } from '@google/genai';

export class GoogleProvider extends BaseStreamingProvider {
  readonly type: ProviderType = 'google';
  private client: GoogleGenAI;

  constructor(readonly config: ProviderConfig) {
    super();
    this.client = new GoogleGenAI({ apiKey: config.apiKey });
  }

  protected async createStream(request: CompletionRequest): Promise<AsyncIterable<unknown>> {
    const stream = await this.client.models.generateContentStream({
      model: this.config.model,
      contents: this.convertMessages(request.messages),
      generationConfig: {
        maxOutputTokens: request.maxTokens,
        temperature: request.temperature,
        topP: request.topP,
      },
    });

    return stream;
  }

  protected extractDelta(chunk: any): string {
    return chunk.text || '';
  }

  protected extractUsage(chunk: any): Partial<TokenUsage> | undefined {
    if (chunk.usageMetadata) {
      return {
        promptTokens: chunk.usageMetadata.promptTokenCount,
        completionTokens: chunk.usageMetadata.candidatesTokenCount,
        totalTokens: chunk.usageMetadata.totalTokenCount,
      };
    }
    return undefined;
  }

  protected async structuredComplete<T>(
    request: StructuredOutputRequest<T>
  ): Promise<StructuredOutputResponse<T>> {
    const response = await this.client.models.generateContent({
      model: this.config.model,
      contents: this.convertMessages(request.messages),
      generationConfig: {
        maxOutputTokens: request.maxTokens || 4096,
        temperature: request.temperature,
        responseMimeType: 'application/json',
        responseSchema: request.schema,
      },
    });

    const text = response.candidates?.[0]?.content?.parts?.[0]?.text || '{}';
    const structuredData = JSON.parse(text);

    return {
      id: this.generateId(),
      content: text,
      structuredData,
      model: this.config.model,
      provider: this.type,
      usage: {
        promptTokens: response.usageMetadata?.promptTokenCount || 0,
        completionTokens: response.usageMetadata?.candidatesTokenCount || 0,
        totalTokens: response.usageMetadata?.totalTokenCount || 0,
      },
      finishReason: 'stop',
    };
  }

  protected async countTokens(text: string): Promise<number> {
    const response = await this.client.models.countTokens({
      model: this.config.model,
      contents: [{ role: 'user', parts: [{ text }] }],
    });
    return response.totalTokens || 0;
  }

  protected generateId(): string {
    return `google_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  protected handleError(error: unknown): ProviderError {
    const err = error as any;
    return {
      provider: this.type,
      type: this.classifyError(err),
      message: err.message || 'Unknown error',
      statusCode: err.status,
      retryable: err.status === 429 || err.status >= 500,
      originalError: error,
    };
  }

  private classifyError(error: any): ProviderError['type'] {
    if (error.status === 429) return 'rate_limit';
    if (error.status === 401 || error.status === 403) return 'auth';
    if (error.message?.includes('token')) return 'context_length';
    if (error.status >= 500) return 'api_error';
    return 'network';
  }

  private convertMessages(messages: Message[]): any[] {
    return messages.map((m) => ({
      role: m.role === 'assistant' ? 'model' : m.role,
      parts: [{ text: m.content }],
    }));
  }
}

// ============================================================================
// Mistral Implementation
// ============================================================================

import { Mistral } from '@mistralai/mistralai';

export class MistralProvider extends BaseStreamingProvider {
  readonly type: ProviderType = 'mistral';
  private client: Mistral;
  private encoder: any; // Use tiktoken for approximation

  constructor(readonly config: ProviderConfig) {
    super();
    this.client = new Mistral({
      apiKey: config.apiKey,
    });
    this.encoder = encoding_for_model('gpt-4o'); // Approximate
  }

  protected async createStream(request: CompletionRequest): Promise<AsyncIterable<unknown>> {
    const stream = await this.client.chat.stream({
      model: this.config.model,
      max_tokens: request.maxTokens,
      temperature: request.temperature,
      top_p: request.topP,
      messages: request.messages,
    });

    return stream;
  }

  protected extractDelta(chunk: any): string {
    return chunk.choices?.[0]?.delta?.content || '';
  }

  protected extractUsage(chunk: any): Partial<TokenUsage> | undefined {
    if (chunk.usage) {
      return {
        promptTokens: chunk.usage.prompt_tokens,
        completionTokens: chunk.usage.completion_tokens,
        totalTokens: chunk.usage.total_tokens,
      };
    }
    return undefined;
  }

  protected async structuredComplete<T>(
    request: StructuredOutputRequest<T>
  ): Promise<StructuredOutputResponse<T>> {
    const response = await this.client.chat.complete({
      model: this.config.model,
      max_tokens: request.maxTokens || 4096,
      messages: request.messages,
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: request.schemaName || 'response',
          schema: request.schema,
        },
      },
    });

    const text = response.choices?.[0]?.message?.content || '{}';
    const structuredData = JSON.parse(text);

    return {
      id: response.id || this.generateId(),
      content: text,
      structuredData,
      model: response.model || this.config.model,
      provider: this.type,
      usage: {
        promptTokens: response.usage?.prompt_tokens || 0,
        completionTokens: response.usage?.completion_tokens || 0,
        totalTokens: response.usage?.total_tokens || 0,
      },
      finishReason: 'stop',
    };
  }

  protected async countTokens(text: string): Promise<number> {
    // Mistral doesn't provide token counting API, use tiktoken approximation
    const tokens = this.encoder.encode(text);
    return tokens.length;
  }

  protected generateId(): string {
    return `mistral_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  protected handleError(error: unknown): ProviderError {
    const err = error as any;
    return {
      provider: this.type,
      type: this.classifyError(err),
      message: err.message || 'Unknown error',
      statusCode: err.status,
      retryable: err.status === 429 || err.status >= 500,
      originalError: error,
    };
  }

  private classifyError(error: any): ProviderError['type'] {
    if (error.status === 429) return 'rate_limit';
    if (error.status === 401 || error.status === 403) return 'auth';
    if (error.message?.includes('context')) return 'context_length';
    if (error.status >= 500) return 'api_error';
    return 'network';
  }
}
```

---

## 4. Context Management Strategy

### 4.1 Context Window Handling

```typescript
// ============================================================================
// Context Management
// ============================================================================

export interface ContextManagerConfig {
  maxTokens: number; // Model's context limit
  reservedOutputTokens: number; // Reserve for response
  compressionStrategy: 'truncate' | 'summarize' | 'sliding_window';
  summaryProvider?: LLMProvider; // For summarization strategy
}

export class ContextManager {
  constructor(
    private config: ContextManagerConfig,
    private tokenCounter: (text: string) => Promise<number>
  ) {}

  async prepareMessages(
    messages: Message[],
    systemPrompt?: string
  ): Promise<{ messages: Message[]; hadToCompress: boolean }> {
    const availableTokens = this.config.maxTokens - this.config.reservedOutputTokens;

    // Count tokens
    let totalTokens = 0;
    if (systemPrompt) {
      totalTokens += await this.tokenCounter(systemPrompt);
    }

    for (const msg of messages) {
      msg.metadata = msg.metadata || {};
      msg.metadata.tokens = await this.tokenCounter(msg.content);
      totalTokens += msg.metadata.tokens;
    }

    // Check if compression needed
    if (totalTokens <= availableTokens) {
      return { messages, hadToCompress: false };
    }

    // Apply compression strategy
    const compressedMessages = await this.compress(messages, availableTokens, systemPrompt);

    return {
      messages: compressedMessages,
      hadToCompress: true,
    };
  }

  private async compress(
    messages: Message[],
    targetTokens: number,
    systemPrompt?: string
  ): Promise<Message[]> {
    switch (this.config.compressionStrategy) {
      case 'truncate':
        return this.truncateOldest(messages, targetTokens, systemPrompt);

      case 'sliding_window':
        return this.slidingWindow(messages, targetTokens, systemPrompt);

      case 'summarize':
        return this.summarizeHistory(messages, targetTokens, systemPrompt);

      default:
        throw new Error(`Unknown compression strategy: ${this.config.compressionStrategy}`);
    }
  }

  private async truncateOldest(
    messages: Message[],
    targetTokens: number,
    systemPrompt?: string
  ): Promise<Message[]> {
    let tokens = systemPrompt ? await this.tokenCounter(systemPrompt) : 0;
    const result: Message[] = [];

    // Work backwards from most recent
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      const msgTokens = msg.metadata?.tokens || await this.tokenCounter(msg.content);

      if (tokens + msgTokens <= targetTokens) {
        result.unshift(msg);
        tokens += msgTokens;
      } else {
        break;
      }
    }

    return result;
  }

  private async slidingWindow(
    messages: Message[],
    targetTokens: number,
    systemPrompt?: string
  ): Promise<Message[]> {
    // Keep first message (context) and last N messages
    const firstMsg = messages[0];
    const firstTokens = firstMsg.metadata?.tokens || await this.tokenCounter(firstMsg.content);

    let systemTokens = systemPrompt ? await this.tokenCounter(systemPrompt) : 0;
    let availableForRecent = targetTokens - systemTokens - firstTokens;

    const recentMessages: Message[] = [];
    let tokens = 0;

    // Work backwards
    for (let i = messages.length - 1; i > 0; i--) {
      const msg = messages[i];
      const msgTokens = msg.metadata?.tokens || await this.tokenCounter(msg.content);

      if (tokens + msgTokens <= availableForRecent) {
        recentMessages.unshift(msg);
        tokens += msgTokens;
      } else {
        break;
      }
    }

    return [firstMsg, ...recentMessages];
  }

  private async summarizeHistory(
    messages: Message[],
    targetTokens: number,
    systemPrompt?: string
  ): Promise<Message[]> {
    if (!this.config.summaryProvider) {
      throw new Error('Summary provider required for summarization strategy');
    }

    // Keep recent messages, summarize older ones
    const recentCount = Math.ceil(messages.length * 0.3); // Keep 30% recent
    const recentMessages = messages.slice(-recentCount);
    const oldMessages = messages.slice(0, -recentCount);

    if (oldMessages.length === 0) {
      return messages; // Nothing to summarize
    }

    // Create summary of old messages
    const summaryPrompt = `Summarize the following debate history in a concise manner, preserving key arguments and positions:\n\n${oldMessages
      .map((m) => `${m.role}: ${m.content}`)
      .join('\n\n')}`;

    const summaryResponse = await this.config.summaryProvider.complete({
      messages: [{ role: 'user', content: summaryPrompt }],
      maxTokens: Math.floor(targetTokens * 0.2), // Summary takes max 20% of context
    });

    const summaryMessage: Message = {
      role: 'system',
      content: `[Previous debate summary]: ${summaryResponse.content}`,
      metadata: {
        tokens: summaryResponse.usage.totalTokens,
      },
    };

    return [summaryMessage, ...recentMessages];
  }
}
```

### 4.2 Debate-Specific Context

```typescript
// ============================================================================
// Debate Context Builder
// ============================================================================

export interface DebateContext {
  topic: string;
  participants: DebateParticipant[];
  format: 'free-form' | 'structured' | 'round-limited' | 'convergence';
  currentRound: number;
  maxRounds?: number;
}

export interface DebateParticipant {
  id: string;
  name: string;
  provider: LLMProvider;
  persona: string;
  position: string;
}

export class DebateContextBuilder {
  buildDebaterSystemPrompt(context: DebateContext, participant: DebateParticipant): string {
    const otherParticipants = context.participants
      .filter((p) => p.id !== participant.id)
      .map((p) => `${p.name} (${p.position})`)
      .join(', ');

    return `You are participating in a structured debate on the topic: "${context.topic}"

YOUR ROLE:
- Name: ${participant.name}
- Position: ${participant.position}
- Persona: ${participant.persona}

OTHER PARTICIPANTS:
${otherParticipants}

DEBATE FORMAT: ${context.format}
CURRENT ROUND: ${context.currentRound}${context.maxRounds ? ` of ${context.maxRounds}` : ''}

INSTRUCTIONS:
1. Stay in character and argue from your assigned position
2. Directly engage with other participants' arguments by referencing them by name
3. Present evidence, reasoning, and counterarguments
4. Be respectful but persuasive
5. Build on previous rounds of discussion
6. Keep responses focused and substantive (aim for 2-4 paragraphs)

Your goal is to make the strongest case for your position while addressing opposing viewpoints.`;
  }

  buildJudgeSystemPrompt(context: DebateContext): string {
    return `You are an impartial judge evaluating a debate on: "${context.topic}"

PARTICIPANTS:
${context.participants.map((p) => `- ${p.name}: ${p.position}`).join('\n')}

YOUR RESPONSIBILITIES:
1. Evaluate argument quality, evidence, and reasoning
2. Detect diminishing returns or repetitive arguments
3. Identify topic drift
4. Determine when meaningful conclusions have been reached
5. Provide structured assessments

OUTPUT FORMAT:
You must respond with valid JSON matching this structure:
{
  "shouldContinue": boolean,
  "qualityScore": number (0-10),
  "assessments": [
    {
      "participant": "participant name",
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1", "weakness 2"],
      "score": number (0-10)
    }
  ],
  "reasoning": "Brief explanation of your assessment",
  "recommendations": "What should happen next or final verdict (if debate complete)"
}

EVALUATION CRITERIA:
- Logical consistency
- Evidence quality
- Engagement with opposing arguments
- Novel insights vs repetition
- Relevance to topic

Be fair, thorough, and decisive.`;
  }

  buildRoundSummary(context: DebateContext, responses: Array<{ participant: DebateParticipant; content: string }>): string {
    return `ROUND ${context.currentRound} SUMMARY:\n\n${responses
      .map((r) => `${r.participant.name} (${r.participant.position}):\n${r.content}`)
      .join('\n\n---\n\n')}`;
  }
}
```

---

## 5. Token Counting & Cost Tracking

### 5.1 Token Counting Implementation

```typescript
// ============================================================================
// Token Counter
// ============================================================================

import { encoding_for_model } from 'js-tiktoken';

export class TokenCounter {
  private encoders: Map<string, any>;

  constructor() {
    this.encoders = new Map();
  }

  async count(text: string, provider: ProviderType, model: string): Promise<number> {
    switch (provider) {
      case 'anthropic':
        return this.countAnthropic(text, model);

      case 'openai':
        return this.countOpenAI(text, model);

      case 'google':
        return this.countGoogle(text, model);

      case 'mistral':
        return this.countMistral(text, model);

      default:
        return this.approximateCount(text);
    }
  }

  private async countOpenAI(text: string, model: string): Promise<number> {
    const key = `openai_${model}`;

    if (!this.encoders.has(key)) {
      try {
        this.encoders.set(key, encoding_for_model(model as any));
      } catch {
        // Fallback to gpt-4o encoding
        this.encoders.set(key, encoding_for_model('gpt-4o'));
      }
    }

    const encoder = this.encoders.get(key);
    const tokens = encoder.encode(text);
    return tokens.length;
  }

  private async countAnthropic(text: string, model: string): Promise<number> {
    // Use API for accurate counting (requires provider instance)
    // Fallback to approximation for offline counting
    return this.approximateCount(text);
  }

  private async countGoogle(text: string, model: string): Promise<number> {
    // Use API for accurate counting (requires provider instance)
    // Fallback to approximation for offline counting
    return this.approximateCount(text);
  }

  private async countMistral(text: string, model: string): Promise<number> {
    // Mistral uses similar tokenization to GPT models
    return this.countOpenAI(text, 'gpt-4o');
  }

  private approximateCount(text: string): number {
    // Rough approximation: ~4 characters per token
    return Math.ceil(text.length / 4);
  }

  cleanup() {
    for (const encoder of this.encoders.values()) {
      if (encoder.free) {
        encoder.free();
      }
    }
    this.encoders.clear();
  }
}
```

### 5.2 Cost Tracking System

```typescript
// ============================================================================
// Cost Tracker
// ============================================================================

export interface PricingModel {
  provider: ProviderType;
  model: string;
  inputCostPer1M: number; // USD per 1M input tokens
  outputCostPer1M: number; // USD per 1M output tokens
  lastUpdated: Date;
}

export class CostTracker {
  private pricingModels: Map<string, PricingModel>;
  private usageHistory: UsageRecord[];
  private totalCost: number;

  constructor() {
    this.pricingModels = new Map();
    this.usageHistory = [];
    this.totalCost = 0;
    this.initializePricing();
  }

  private initializePricing() {
    // Pricing as of November 2025
    const models: PricingModel[] = [
      // Anthropic
      {
        provider: 'anthropic',
        model: 'claude-sonnet-4-5-20250929',
        inputCostPer1M: 3.00,
        outputCostPer1M: 15.00,
        lastUpdated: new Date('2025-11-01'),
      },
      {
        provider: 'anthropic',
        model: 'claude-3-5-haiku-20241022',
        inputCostPer1M: 0.80,
        outputCostPer1M: 4.00,
        lastUpdated: new Date('2024-10-01'),
      },

      // OpenAI
      {
        provider: 'openai',
        model: 'gpt-4o',
        inputCostPer1M: 2.50,
        outputCostPer1M: 10.00,
        lastUpdated: new Date('2024-08-01'),
      },
      {
        provider: 'openai',
        model: 'gpt-4o-mini',
        inputCostPer1M: 0.15,
        outputCostPer1M: 0.60,
        lastUpdated: new Date('2024-07-01'),
      },

      // Google
      {
        provider: 'google',
        model: 'gemini-2.5-flash',
        inputCostPer1M: 0.075,
        outputCostPer1M: 0.30,
        lastUpdated: new Date('2025-11-01'),
      },
      {
        provider: 'google',
        model: 'gemini-1.5-pro',
        inputCostPer1M: 1.25,
        outputCostPer1M: 5.00,
        lastUpdated: new Date('2024-05-01'),
      },

      // Mistral
      {
        provider: 'mistral',
        model: 'mistral-large-latest',
        inputCostPer1M: 2.00,
        outputCostPer1M: 6.00,
        lastUpdated: new Date('2024-09-01'),
      },
      {
        provider: 'mistral',
        model: 'mistral-small-latest',
        inputCostPer1M: 0.20,
        outputCostPer1M: 0.60,
        lastUpdated: new Date('2024-09-01'),
      },
    ];

    for (const model of models) {
      const key = `${model.provider}:${model.model}`;
      this.pricingModels.set(key, model);
    }
  }

  track(provider: ProviderType, model: string, usage: TokenUsage): number {
    const pricing = this.getPricing(provider, model);

    const inputCost = (usage.promptTokens / 1_000_000) * pricing.inputCostPer1M;
    const outputCost = (usage.completionTokens / 1_000_000) * pricing.outputCostPer1M;
    const cost = inputCost + outputCost;

    const record: UsageRecord = {
      timestamp: new Date(),
      provider,
      model,
      usage,
      cost,
    };

    this.usageHistory.push(record);
    this.totalCost += cost;

    return cost;
  }

  getTotalCost(): number {
    return this.totalCost;
  }

  getCostByProvider(): Map<ProviderType, number> {
    const costs = new Map<ProviderType, number>();

    for (const record of this.usageHistory) {
      const current = costs.get(record.provider) || 0;
      costs.set(record.provider, current + record.cost);
    }

    return costs;
  }

  getCostByModel(): Map<string, number> {
    const costs = new Map<string, number>();

    for (const record of this.usageHistory) {
      const key = `${record.provider}:${record.model}`;
      const current = costs.get(key) || 0;
      costs.set(key, current + record.cost);
    }

    return costs;
  }

  estimateCost(provider: ProviderType, model: string, estimatedTokens: { input: number; output: number }): number {
    const pricing = this.getPricing(provider, model);

    const inputCost = (estimatedTokens.input / 1_000_000) * pricing.inputCostPer1M;
    const outputCost = (estimatedTokens.output / 1_000_000) * pricing.outputCostPer1M;

    return inputCost + outputCost;
  }

  getUsageHistory(
    filters?: {
      provider?: ProviderType;
      model?: string;
      startDate?: Date;
      endDate?: Date;
    }
  ): UsageRecord[] {
    let records = [...this.usageHistory];

    if (filters) {
      if (filters.provider) {
        records = records.filter((r) => r.provider === filters.provider);
      }
      if (filters.model) {
        records = records.filter((r) => r.model === filters.model);
      }
      if (filters.startDate) {
        records = records.filter((r) => r.timestamp >= filters.startDate!);
      }
      if (filters.endDate) {
        records = records.filter((r) => r.timestamp <= filters.endDate!);
      }
    }

    return records;
  }

  exportReport(): CostReport {
    const byProvider = this.getCostByProvider();
    const byModel = this.getCostByModel();

    return {
      totalCost: this.totalCost,
      totalTokens: this.usageHistory.reduce((sum, r) => sum + r.usage.totalTokens, 0),
      requestCount: this.usageHistory.length,
      byProvider: Object.fromEntries(byProvider),
      byModel: Object.fromEntries(byModel),
      history: this.usageHistory,
      generatedAt: new Date(),
    };
  }

  private getPricing(provider: ProviderType, model: string): PricingModel {
    const key = `${provider}:${model}`;
    const pricing = this.pricingModels.get(key);

    if (!pricing) {
      // Fallback to conservative estimate
      console.warn(`No pricing found for ${key}, using fallback`);
      return {
        provider,
        model,
        inputCostPer1M: 5.00,
        outputCostPer1M: 15.00,
        lastUpdated: new Date(),
      };
    }

    return pricing;
  }
}

export interface UsageRecord {
  timestamp: Date;
  provider: ProviderType;
  model: string;
  usage: TokenUsage;
  cost: number;
}

export interface CostReport {
  totalCost: number;
  totalTokens: number;
  requestCount: number;
  byProvider: Record<string, number>;
  byModel: Record<string, number>;
  history: UsageRecord[];
  generatedAt: Date;
}
```

---

## 6. Rate Limiting & Queue Management

### 6.1 Request Queue Implementation

```typescript
// ============================================================================
// Request Queue with Rate Limiting
// ============================================================================

export interface QueuedRequest<T> {
  id: string;
  execute: () => Promise<T>;
  priority: number;
  retries: number;
  maxRetries: number;
  createdAt: Date;
}

export class RequestQueue {
  private queue: QueuedRequest<any>[];
  private activeRequests: number;
  private rateLimiter: RateLimiter;

  constructor(private config: QueueConfig) {
    this.queue = [];
    this.activeRequests = 0;
    this.rateLimiter = new RateLimiter({
      maxRequestsPerMinute: config.maxRequestsPerMinute || 60,
      maxTokensPerMinute: config.maxTokensPerMinute || 100_000,
    });
  }

  async enqueue<T>(execute: () => Promise<T>, priority: number = 0): Promise<T> {
    const request: QueuedRequest<T> = {
      id: this.generateId(),
      execute,
      priority,
      retries: 0,
      maxRetries: this.config.retryAttempts,
      createdAt: new Date(),
    };

    return new Promise((resolve, reject) => {
      this.queue.push(request);
      this.queue.sort((a, b) => b.priority - a.priority);
      this.processQueue().then(() => {
        this.executeRequest(request).then(resolve).catch(reject);
      });
    });
  }

  async executeBatch<T, R>(
    items: T[],
    concurrency: number,
    executor: (item: T) => Promise<R>
  ): Promise<R[]> {
    const results: R[] = [];
    const executing: Promise<void>[] = [];

    for (const item of items) {
      const promise = this.enqueue(() => executor(item)).then((result) => {
        results.push(result);
      });

      executing.push(promise);

      if (executing.length >= concurrency) {
        await Promise.race(executing);
        executing.splice(
          executing.findIndex((p) => p === promise),
          1
        );
      }
    }

    await Promise.all(executing);
    return results;
  }

  private async processQueue(): Promise<void> {
    while (this.queue.length > 0 && this.activeRequests < this.config.maxConcurrentRequests) {
      const request = this.queue.shift();
      if (request) {
        this.activeRequests++;
        // Queue processing happens asynchronously
      }
    }
  }

  private async executeRequest<T>(request: QueuedRequest<T>): Promise<T> {
    try {
      // Check rate limits
      await this.rateLimiter.waitForCapacity();

      // Execute with timeout
      const result = await this.executeWithTimeout(request.execute, this.config.timeoutMs);

      this.activeRequests--;
      this.processQueue();

      return result;
    } catch (error) {
      // Handle retries
      if (this.shouldRetry(error, request)) {
        request.retries++;
        const backoff = this.calculateBackoff(request.retries);
        await this.sleep(backoff);
        return this.executeRequest(request);
      }

      this.activeRequests--;
      this.processQueue();
      throw error;
    }
  }

  private async executeWithTimeout<T>(fn: () => Promise<T>, timeoutMs: number): Promise<T> {
    return Promise.race([
      fn(),
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
      ),
    ]);
  }

  private shouldRetry(error: unknown, request: QueuedRequest<any>): boolean {
    if (request.retries >= request.maxRetries) return false;

    const err = error as ProviderError;
    return err.retryable || false;
  }

  private calculateBackoff(retryCount: number): number {
    // Exponential backoff with jitter
    const baseDelay = this.config.retryBackoffMs;
    const exponentialDelay = baseDelay * Math.pow(2, retryCount - 1);
    const jitter = Math.random() * 1000;
    return Math.min(exponentialDelay + jitter, 60000); // Max 60s
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private generateId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getQueueSize(): number {
    return this.queue.length;
  }

  getActiveRequests(): number {
    return this.activeRequests;
  }
}

// ============================================================================
// Rate Limiter
// ============================================================================

export interface RateLimiterConfig {
  maxRequestsPerMinute: number;
  maxTokensPerMinute: number;
}

export class RateLimiter {
  private requestTimestamps: number[];
  private tokenUsage: Array<{ timestamp: number; tokens: number }>;

  constructor(private config: RateLimiterConfig) {
    this.requestTimestamps = [];
    this.tokenUsage = [];
  }

  async waitForCapacity(estimatedTokens: number = 0): Promise<void> {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Clean old entries
    this.requestTimestamps = this.requestTimestamps.filter((ts) => ts > oneMinuteAgo);
    this.tokenUsage = this.tokenUsage.filter((entry) => entry.timestamp > oneMinuteAgo);

    // Check request rate
    const requestsInLastMinute = this.requestTimestamps.length;
    if (requestsInLastMinute >= this.config.maxRequestsPerMinute) {
      const oldestRequest = this.requestTimestamps[0];
      const waitTime = oldestRequest + 60000 - now;
      if (waitTime > 0) {
        await this.sleep(waitTime);
        return this.waitForCapacity(estimatedTokens);
      }
    }

    // Check token rate
    const tokensInLastMinute = this.tokenUsage.reduce((sum, entry) => sum + entry.tokens, 0);
    if (tokensInLastMinute + estimatedTokens > this.config.maxTokensPerMinute) {
      const oldestToken = this.tokenUsage[0];
      const waitTime = oldestToken.timestamp + 60000 - now;
      if (waitTime > 0) {
        await this.sleep(waitTime);
        return this.waitForCapacity(estimatedTokens);
      }
    }

    // Record this request
    this.requestTimestamps.push(now);
    if (estimatedTokens > 0) {
      this.tokenUsage.push({ timestamp: now, tokens: estimatedTokens });
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  getStatus(): { requestsUsed: number; tokensUsed: number } {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    const requestsUsed = this.requestTimestamps.filter((ts) => ts > oneMinuteAgo).length;
    const tokensUsed = this.tokenUsage
      .filter((entry) => entry.timestamp > oneMinuteAgo)
      .reduce((sum, entry) => sum + entry.tokens, 0);

    return { requestsUsed, tokensUsed };
  }
}
```

---

## 7. Error Handling Patterns

### 7.1 Comprehensive Error Strategy

```typescript
// ============================================================================
// Error Handling
// ============================================================================

export class ErrorHandler {
  private errorLog: ErrorLogEntry[];
  private retryStrategies: Map<ProviderError['type'], RetryStrategy>;

  constructor() {
    this.errorLog = [];
    this.initializeRetryStrategies();
  }

  private initializeRetryStrategies() {
    this.retryStrategies = new Map([
      ['rate_limit', { maxRetries: 3, backoffMultiplier: 2, useRetryAfter: true }],
      ['network', { maxRetries: 3, backoffMultiplier: 1.5, useRetryAfter: false }],
      ['api_error', { maxRetries: 2, backoffMultiplier: 2, useRetryAfter: false }],
      ['context_length', { maxRetries: 0, backoffMultiplier: 0, useRetryAfter: false }],
      ['auth', { maxRetries: 0, backoffMultiplier: 0, useRetryAfter: false }],
      ['validation', { maxRetries: 0, backoffMultiplier: 0, useRetryAfter: false }],
    ]);
  }

  handle(error: ProviderError, context: ErrorContext): ErrorResponse {
    // Log error
    this.logError(error, context);

    // Get retry strategy
    const strategy = this.retryStrategies.get(error.type);

    // Build user-friendly message
    const userMessage = this.buildUserMessage(error);

    // Determine if recoverable
    const recoverable = this.isRecoverable(error);

    return {
      error,
      userMessage,
      recoverable,
      retryStrategy: strategy,
      suggestedAction: this.suggestAction(error),
    };
  }

  private buildUserMessage(error: ProviderError): string {
    switch (error.type) {
      case 'rate_limit':
        return `Rate limit exceeded for ${error.provider}. ${
          error.retryAfter
            ? `Please wait ${error.retryAfter} seconds before retrying.`
            : 'Please wait before making more requests.'
        }`;

      case 'context_length':
        return `Message history is too long for ${error.provider}. Try shortening the debate or enabling context compression.`;

      case 'api_error':
        return `${error.provider} API error: ${error.message}. This may be temporary.`;

      case 'network':
        return `Network error connecting to ${error.provider}. Please check your connection.`;

      case 'auth':
        return `Authentication failed for ${error.provider}. Please check your API key.`;

      case 'validation':
        return `Invalid request: ${error.message}`;

      default:
        return `An error occurred: ${error.message}`;
    }
  }

  private isRecoverable(error: ProviderError): boolean {
    return error.retryable && error.type !== 'auth' && error.type !== 'context_length';
  }

  private suggestAction(error: ProviderError): string {
    switch (error.type) {
      case 'rate_limit':
        return 'Reduce concurrent requests or upgrade API tier';

      case 'context_length':
        return 'Enable context compression or reduce debate length';

      case 'auth':
        return 'Verify and update API key in settings';

      case 'network':
        return 'Check internet connection and retry';

      case 'api_error':
        return 'Wait a moment and retry';

      case 'validation':
        return 'Check request parameters';

      default:
        return 'Contact support if issue persists';
    }
  }

  private logError(error: ProviderError, context: ErrorContext) {
    this.errorLog.push({
      timestamp: new Date(),
      error,
      context,
    });

    // Keep last 100 errors
    if (this.errorLog.length > 100) {
      this.errorLog.shift();
    }
  }

  getErrorLog(): ErrorLogEntry[] {
    return [...this.errorLog];
  }

  getErrorStats(): ErrorStats {
    const byType = new Map<ProviderError['type'], number>();
    const byProvider = new Map<ProviderType, number>();

    for (const entry of this.errorLog) {
      const typeCount = byType.get(entry.error.type) || 0;
      byType.set(entry.error.type, typeCount + 1);

      const providerCount = byProvider.get(entry.error.provider) || 0;
      byProvider.set(entry.error.provider, providerCount + 1);
    }

    return {
      totalErrors: this.errorLog.length,
      byType: Object.fromEntries(byType),
      byProvider: Object.fromEntries(byProvider),
    };
  }
}

export interface ErrorContext {
  operation: string;
  debateId?: string;
  round?: number;
  participantId?: string;
}

export interface RetryStrategy {
  maxRetries: number;
  backoffMultiplier: number;
  useRetryAfter: boolean;
}

export interface ErrorResponse {
  error: ProviderError;
  userMessage: string;
  recoverable: boolean;
  retryStrategy?: RetryStrategy;
  suggestedAction: string;
}

export interface ErrorLogEntry {
  timestamp: Date;
  error: ProviderError;
  context: ErrorContext;
}

export interface ErrorStats {
  totalErrors: number;
  byType: Record<string, number>;
  byProvider: Record<string, number>;
}
```

---

## 8. SDK Recommendations

### 8.1 Recommended Approach: Native SDKs

**Verdict: Use native provider SDKs directly rather than LangChain**

**Rationale:**
1. **Better Type Safety**: Official SDKs have better TypeScript support and type definitions
2. **Streaming Control**: More granular control over streaming for real-time debate UI
3. **Latest Features**: Immediate access to structured outputs and new features
4. **Smaller Bundle**: Avoid LangChain's large dependency footprint
5. **Simpler Debugging**: Direct API interaction easier to debug than abstraction layers
6. **Performance**: No additional abstraction overhead

**When LangChain Makes Sense:**
- Complex RAG (retrieval-augmented generation) pipelines
- Agent workflows with tool calling
- Vector database integration
- Cross-provider experimentation

**For Quorum's Use Case:**
- Direct streaming responses (debaters)
- Structured JSON output (judge)
- Cost tracking
- Simple request/response pattern

→ **Native SDKs are the better choice**

### 8.2 Package Dependencies

```json
{
  "dependencies": {
    "@anthropic-ai/sdk": "^0.71.0",
    "openai": "^4.73.0",
    "@google/genai": "^0.21.0",
    "@mistralai/mistralai": "^1.3.0",
    "js-tiktoken": "^1.0.15",
    "zod": "^3.24.1"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "typescript": "^5.7.2"
  }
}
```

---

## 9. Architecture Recommendations

### 9.1 Client-Side vs Backend

**For MVP: Client-Side First with Optional Backend**

#### Client-Side Architecture (Recommended for MVP)

**Pros:**
- Faster development
- No infrastructure costs
- Direct streaming to UI
- Simpler deployment

**Cons:**
- API keys exposed (with user consent)
- No central rate limiting
- No debate persistence
- Limited usage analytics

**Implementation:**
```
React App
  ↓
Provider Manager (in-browser)
  ↓
Direct API calls to: Anthropic, OpenAI, Google, Mistral
  ↓
Real-time streaming to UI components
```

#### Optional Backend Architecture (Post-MVP)

**Pros:**
- Secure API key storage
- Centralized rate limiting
- Debate persistence
- Usage analytics
- Cost controls

**Cons:**
- Infrastructure complexity
- Server costs
- Deployment overhead
- Additional latency

**Implementation:**
```
React App
  ↓ (WebSocket/SSE)
Backend Service (Node.js/Express)
  ↓
Provider Manager
  ↓
Provider APIs
```

### 9.2 Recommended Stack

**Frontend:**
- React 18+ (concurrent features for streaming)
- TypeScript
- Vite (fast builds)
- TanStack Query (request state management)
- Zustand (lightweight state management)

**Backend (Optional):**
- Node.js 20+
- Express or Fastify
- PostgreSQL (debate storage)
- Redis (rate limiting, caching)
- SSE for streaming

---

## 10. Implementation Roadmap

### Phase 1: Core Abstraction (Week 1-2)
- [ ] Implement base provider interface
- [ ] Build Anthropic provider
- [ ] Build OpenAI provider
- [ ] Implement streaming abstraction
- [ ] Create token counter
- [ ] Basic error handling

### Phase 2: Multi-Provider Support (Week 2-3)
- [ ] Build Google provider
- [ ] Build Mistral provider
- [ ] Provider manager orchestration
- [ ] Request queue implementation
- [ ] Rate limiting system

### Phase 3: Debate Features (Week 3-4)
- [ ] Context manager
- [ ] Debate context builder
- [ ] Structured output for judge
- [ ] Streaming coordination for simultaneous rounds
- [ ] Cost tracking system

### Phase 4: Polish & Testing (Week 4-5)
- [ ] Comprehensive error handling
- [ ] Unit tests for all providers
- [ ] Integration tests for debate flows
- [ ] Performance optimization
- [ ] Documentation

---

## 11. Code Examples

### 11.1 Basic Usage Example

```typescript
import { ProviderManager, AnthropicProvider, OpenAIProvider } from './llm';

// Initialize provider manager
const manager = new ProviderManager({
  queueConfig: {
    maxConcurrentRequests: 5,
    retryAttempts: 3,
    retryBackoffMs: 1000,
    timeoutMs: 60000,
  },
});

// Register providers
const claude = manager.registerProvider('claude', {
  type: 'anthropic',
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: 'claude-sonnet-4-5-20250929',
});

const gpt = manager.registerProvider('gpt', {
  type: 'openai',
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
});

// Stream a response
await claude.streamComplete({
  messages: [
    { role: 'user', content: 'Explain quantum computing in simple terms.' },
  ],
  maxTokens: 1000,
  temperature: 0.7,
  onChunk: (chunk) => {
    console.log(chunk.delta);
  },
  onComplete: (response) => {
    console.log('Done!', response.usage);
  },
  onError: (error) => {
    console.error('Error:', error.message);
  },
});
```

### 11.2 Debate Round Example

```typescript
import { ProviderManager, DebateContextBuilder } from './llm';

// Setup debate
const context = {
  topic: 'Is AI safety research more important than AI capabilities research?',
  participants: [
    {
      id: 'p1',
      name: 'Claude',
      provider: claudeProvider,
      persona: 'AI safety researcher',
      position: 'AI safety research should be prioritized',
    },
    {
      id: 'p2',
      name: 'GPT',
      provider: gptProvider,
      persona: 'AI capabilities researcher',
      position: 'AI capabilities research drives progress',
    },
  ],
  format: 'structured',
  currentRound: 1,
  maxRounds: 5,
};

const contextBuilder = new DebateContextBuilder();

// Execute parallel debate round
const responses = await manager.executeParallelDebateRound(
  context.participants.map((p) => ({
    providerId: p.id,
    request: {
      messages: [
        {
          role: 'system',
          content: contextBuilder.buildDebaterSystemPrompt(context, p),
        },
        {
          role: 'user',
          content: `Round ${context.currentRound}: Present your opening argument.`,
        },
      ],
      maxTokens: 500,
      temperature: 0.8,
    },
  }))
);

// Display responses
for (const response of responses) {
  console.log(`\n${response.metadata.participant}:`);
  console.log(response.content);
  console.log(`Cost: $${response.usage.estimatedCost?.toFixed(4)}`);
}

// Get cost report
const totalCost = manager.getTotalCost();
console.log(`\nTotal debate cost: $${totalCost.toFixed(4)}`);
```

### 11.3 Judge Evaluation Example

```typescript
// Judge evaluates the round
const judgeResponse = await judgeProvider.structuredComplete<JudgeAssessment>({
  messages: [
    {
      role: 'system',
      content: contextBuilder.buildJudgeSystemPrompt(context),
    },
    {
      role: 'user',
      content: contextBuilder.buildRoundSummary(context, responses),
    },
  ],
  schema: {
    type: 'object',
    properties: {
      shouldContinue: { type: 'boolean' },
      qualityScore: { type: 'number', minimum: 0, maximum: 10 },
      assessments: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            participant: { type: 'string' },
            strengths: { type: 'array', items: { type: 'string' } },
            weaknesses: { type: 'array', items: { type: 'string' } },
            score: { type: 'number', minimum: 0, maximum: 10 },
          },
          required: ['participant', 'strengths', 'weaknesses', 'score'],
        },
      },
      reasoning: { type: 'string' },
      recommendations: { type: 'string' },
    },
    required: ['shouldContinue', 'qualityScore', 'assessments', 'reasoning', 'recommendations'],
  },
  schemaName: 'judge_assessment',
  maxTokens: 2000,
});

interface JudgeAssessment {
  shouldContinue: boolean;
  qualityScore: number;
  assessments: Array<{
    participant: string;
    strengths: string[];
    weaknesses: string[];
    score: number;
  }>;
  reasoning: string;
  recommendations: string;
}

console.log('\nJudge Assessment:');
console.log(JSON.stringify(judgeResponse.structuredData, null, 2));

if (!judgeResponse.structuredData.shouldContinue) {
  console.log('\nDebate concluded by judge.');
}
```

---

## 12. Key Takeaways & Recommendations

### 12.1 Critical Decisions

✅ **Use Native SDKs** - Better than LangChain for Quorum's use case
✅ **Client-Side First** - Ship MVP faster, add backend post-launch
✅ **Streaming Priority** - Essential for debate UX
✅ **Structured Output** - All providers support it (use for judge)
✅ **Cost Tracking** - Critical for user transparency
✅ **Rate Limiting** - Prevent API overages and improve reliability

### 12.2 Risk Mitigation

**Context Length Issues:**
- Implement context compression (summarization)
- Show warnings when approaching limits
- Allow users to restart debates

**Rate Limiting:**
- Queue management with exponential backoff
- Provider-specific concurrency limits
- Clear user messaging

**Token Costs:**
- Real-time cost display
- Configurable cost warnings
- Model selection based on budget

**Streaming Inconsistency:**
- Unified streaming abstraction
- Provider-specific optimizations
- Graceful fallback for errors

### 12.3 Performance Targets

- **Streaming Latency**: First token < 1s
- **Parallel Round Execution**: Complete within 10s (4 participants)
- **Context Compression**: Process 100K tokens in < 30s
- **Cost Tracking**: Real-time with < 100ms overhead

---

## Sources

### Official Documentation & SDKs

**Anthropic Claude:**
- [GitHub - anthropics/anthropic-sdk-typescript](https://github.com/anthropics/anthropic-sdk-typescript)
- [Streaming Messages - Anthropic](https://docs.anthropic.com/en/docs/build-with-claude/streaming)
- [Structured outputs - Claude Docs](https://docs.claude.com/en/docs/build-with-claude/structured-outputs)
- [Anthropic Launches Structured Outputs](https://techbytes.app/posts/claude-structured-outputs-json-schema-api/)

**OpenAI:**
- [GitHub - openai/openai-node](https://github.com/openai/openai-node)
- [Introducing Structured Outputs in the API | OpenAI](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [Structured model outputs - OpenAI API](https://platform.openai.com/docs/guides/structured-outputs)

**Google Gemini:**
- [GitHub - googleapis/js-genai](https://github.com/googleapis/js-genai)
- [Structured Outputs | Gemini API](https://ai.google.dev/gemini-api/docs/structured-output)
- [Google announces support for JSON Schema](https://blog.google/technology/developers/gemini-api-structured-outputs/)

**Mistral AI:**
- [GitHub - mistralai/client-ts](https://github.com/mistralai/client-ts)
- [SDK Clients | Mistral Docs](https://docs.mistral.ai/getting-started/clients)
- [Custom Structured Output | Mistral AI](https://docs.mistral.ai/capabilities/structured-output/custom_structured_output/)

### Token Counting & Cost Tracking

- [Token Counting Explained: tiktoken, Anthropic, and Gemini (2025 Guide)](https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025)
- [llm-cost - npm](https://www.npmjs.com/package/llm-cost)
- [Model Usage & Cost Tracking for LLM applications](https://langfuse.com/docs/observability/features/token-and-cost-tracking)
- [LLM Cost Estimation Guide](https://medium.com/@alphaiterations/llm-cost-estimation-guide-from-token-usage-to-total-spend-fba348d62824)

### Rate Limiting & Queue Management

- [Rate Limits for LLM Providers](https://www.requesty.ai/blog/rate-limits-for-llm-providers-openai-anthropic-and-deepseek)
- [API Rate Limits Explained: Best Practices for 2025](https://orq.ai/blog/api-rate-limit)
- [Concurrent vs. Parallel Execution in LLM API Calls](https://medium.com/@neeldevenshah/concurrent-vs-parallel-execution-in-llm-api-calls-from-an-ai-engineers-perspective-5842e50974d4)
- [Efficient Request Queueing – Optimizing LLM Performance](https://huggingface.co/blog/tngtech/llm-performance-request-queueing)

### Framework Comparisons

- [31 Best LangChain Alternatives Developers Love](https://blog.lamatic.ai/guides/langchain-alternatives-guide/)
- [GitHub - langchain-ai/langchainjs](https://github.com/langchain-ai/langchainjs)
- [On Type Safety In LangChain TS](https://octomind.dev/blog/on-type-safety-in-langchain-ts)

---

**End of API Integration Specification**
