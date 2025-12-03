# Context Management & Cost Tracking - Research Findings

**Research Date:** December 2, 2025
**Phase:** Phase 2 - Multi-LLM Debate Engine
**Researcher:** Research Agent

---

## Executive Summary

This document presents research on sliding window strategies for multi-participant debates, token counting approaches per provider, cost tracking implementations, and warning threshold systems. Key findings include optimal context compression algorithms, real-time cost estimation, and user-facing warning systems.

---

## 1. Sliding Window Strategies for Multi-Participant Debates

### 1.1 Context Window Management Challenges

**Problem:** Multi-participant debates quickly exceed context windows.

**Example Calculation:**
- 4 debaters × 5 rounds × 500 tokens/response = 10,000 tokens (just responses)
- + System prompts (~500 tokens each × 4) = 2,000 tokens
- + Context/history references = 3,000-5,000 tokens
- **Total:** 15,000-17,000 tokens per round

**Context Limits by Provider:**
- Claude Sonnet 4.5: 200K tokens
- GPT-4o: 128K tokens
- Gemini 1.5 Pro: 1M tokens
- Mistral Large: 128K tokens

### 1.2 Sliding Window Algorithm

**Recommended Pattern: Hybrid Sliding Window + Summarization**

```typescript
interface SlidingWindowConfig {
  maxTotalTokens: number; // Model's context limit
  reservedOutputTokens: number; // Reserve for response generation
  windowStrategy: 'last-n-rounds' | 'exponential-decay' | 'importance-weighted';
  summarizationThreshold: number; // Token count to trigger summarization
  preserveFirstMessage: boolean; // Keep initial topic/context
}

class SlidingWindowManager {
  constructor(
    private config: SlidingWindowConfig,
    private tokenCounter: TokenCounter
  ) {}

  async prepareContext(
    systemPrompt: string,
    history: DebateMessage[],
    currentRound: number
  ): Promise<PreparedContext> {
    // 1. Calculate available tokens
    const availableTokens =
      this.config.maxTotalTokens - this.config.reservedOutputTokens;

    // 2. Count current usage
    const systemPromptTokens = await this.tokenCounter.count(systemPrompt);
    let historyTokens = 0;

    for (const msg of history) {
      msg.tokenCount = await this.tokenCounter.count(msg.content);
      historyTokens += msg.tokenCount;
    }

    const totalTokens = systemPromptTokens + historyTokens;

    // 3. Check if compression needed
    if (totalTokens <= availableTokens) {
      return {
        systemPrompt,
        history,
        hadCompression: false,
        strategy: 'none',
      };
    }

    // 4. Apply sliding window strategy
    console.log(`Context exceeds limit (${totalTokens}/${availableTokens}), applying compression`);

    const compressed = await this.applyStrategy(
      systemPrompt,
      history,
      availableTokens,
      systemPromptTokens
    );

    return {
      systemPrompt,
      history: compressed,
      hadCompression: true,
      strategy: this.config.windowStrategy,
      compressionRatio: compressed.length / history.length,
    };
  }

  private async applyStrategy(
    systemPrompt: string,
    history: DebateMessage[],
    availableTokens: number,
    systemPromptTokens: number
  ): Promise<DebateMessage[]> {
    switch (this.config.windowStrategy) {
      case 'last-n-rounds':
        return this.lastNRounds(history, availableTokens - systemPromptTokens);

      case 'exponential-decay':
        return this.exponentialDecay(history, availableTokens - systemPromptTokens);

      case 'importance-weighted':
        return this.importanceWeighted(history, availableTokens - systemPromptTokens);

      default:
        return this.lastNRounds(history, availableTokens - systemPromptTokens);
    }
  }

  // Strategy 1: Keep last N rounds
  private async lastNRounds(
    history: DebateMessage[],
    availableTokens: number
  ): Promise<DebateMessage[]> {
    const result: DebateMessage[] = [];
    let tokenCount = 0;

    // Preserve first message if configured
    if (this.config.preserveFirstMessage && history.length > 0) {
      const firstMsg = history[0];
      result.push(firstMsg);
      tokenCount += firstMsg.tokenCount || 0;
    }

    // Work backwards from most recent
    for (let i = history.length - 1; i >= 1; i--) {
      const msg = history[i];
      const msgTokens = msg.tokenCount || 0;

      if (tokenCount + msgTokens <= availableTokens) {
        result.unshift(msg);
        tokenCount += msgTokens;
      } else {
        break;
      }
    }

    console.log(`Kept ${result.length}/${history.length} messages (${tokenCount} tokens)`);
    return result;
  }

  // Strategy 2: Exponential decay (keep recent + sample older)
  private async exponentialDecay(
    history: DebateMessage[],
    availableTokens: number
  ): Promise<DebateMessage[]> {
    const result: DebateMessage[] = [];
    let tokenCount = 0;

    // Always keep first message
    if (history.length > 0) {
      result.push(history[0]);
      tokenCount += history[0].tokenCount || 0;
    }

    // Recent messages: keep all (last 30%)
    const recentThreshold = Math.floor(history.length * 0.7);
    const recentMessages = history.slice(recentThreshold);

    for (const msg of recentMessages) {
      if (tokenCount + (msg.tokenCount || 0) <= availableTokens) {
        result.push(msg);
        tokenCount += msg.tokenCount || 0;
      }
    }

    // Older messages: sample with exponential decay
    const olderMessages = history.slice(1, recentThreshold);
    const sampleRate = 0.3; // Keep 30% of older messages

    for (let i = 0; i < olderMessages.length; i++) {
      const probability = Math.exp(-i / olderMessages.length) * sampleRate;

      if (Math.random() < probability) {
        const msg = olderMessages[i];
        if (tokenCount + (msg.tokenCount || 0) <= availableTokens) {
          result.push(msg);
          tokenCount += msg.tokenCount || 0;
        }
      }
    }

    // Sort by original order
    result.sort((a, b) => (a.sequenceId || 0) - (b.sequenceId || 0));

    console.log(`Exponential decay: Kept ${result.length}/${history.length} messages`);
    return result;
  }

  // Strategy 3: Importance-weighted (prioritize key arguments)
  private async importanceWeighted(
    history: DebateMessage[],
    availableTokens: number
  ): Promise<DebateMessage[]> {
    // Score each message by importance
    const scoredMessages = history.map((msg) => ({
      message: msg,
      score: this.calculateImportance(msg, history),
    }));

    // Sort by score (descending)
    scoredMessages.sort((a, b) => b.score - a.score);

    // Keep highest-scoring messages within token budget
    const result: DebateMessage[] = [];
    let tokenCount = 0;

    for (const { message } of scoredMessages) {
      if (tokenCount + (message.tokenCount || 0) <= availableTokens) {
        result.push(message);
        tokenCount += message.tokenCount || 0;
      }
    }

    // Sort by original order
    result.sort((a, b) => (a.sequenceId || 0) - (b.sequenceId || 0));

    console.log(`Importance-weighted: Kept ${result.length}/${history.length} messages`);
    return result;
  }

  private calculateImportance(msg: DebateMessage, history: DebateMessage[]): number {
    let score = 0;

    // Recent messages are more important
    const age = history.length - (msg.sequenceId || 0);
    score += Math.max(10 - age, 0); // Recent: +10, decays to 0

    // First message (topic) is critical
    if (msg.sequenceId === 0) {
      score += 50;
    }

    // Judge assessments are important
    if (msg.role === 'judge') {
      score += 20;
    }

    // Opening/closing statements are important
    if (msg.metadata?.phase === 'opening' || msg.metadata?.phase === 'closing') {
      score += 15;
    }

    // Messages with citations/evidence are valuable
    if (msg.content.includes('http') || msg.content.match(/\[\d+\]/)) {
      score += 10;
    }

    // Longer messages (more substantive) score higher
    const wordCount = msg.content.split(/\s+/).length;
    score += Math.min(wordCount / 50, 10); // Up to +10 for long messages

    return score;
  }
}

interface PreparedContext {
  systemPrompt: string;
  history: DebateMessage[];
  hadCompression: boolean;
  strategy: string;
  compressionRatio?: number;
}
```

### 1.3 Summarization Strategy (Fallback)

**When to use:** When sliding window alone is insufficient.

```typescript
class SummarizationManager {
  constructor(private summaryProvider: LLMProvider) {}

  async summarizeHistory(
    history: DebateMessage[],
    targetTokens: number
  ): Promise<DebateMessage> {
    // Identify messages to summarize (middle section)
    const recentCount = Math.ceil(history.length * 0.3);
    const recentMessages = history.slice(-recentCount);
    const toSummarize = history.slice(0, -recentCount);

    if (toSummarize.length === 0) {
      throw new Error('No messages to summarize');
    }

    // Create summary prompt
    const summaryPrompt = this.buildSummaryPrompt(toSummarize);

    // Generate summary
    const summaryResponse = await this.summaryProvider.complete({
      messages: [
        {
          role: 'user',
          content: summaryPrompt,
        },
      ],
      maxTokens: Math.floor(targetTokens * 0.2), // Summary takes 20% of budget
      temperature: 0.3, // Low temperature for factual summary
    });

    // Create summary message
    const summaryMessage: DebateMessage = {
      role: 'system',
      content: `[Summary of earlier debate rounds]:\n\n${summaryResponse.content}`,
      metadata: {
        isSummary: true,
        summarizedCount: toSummarize.length,
        originalTokenCount: toSummarize.reduce((sum, msg) => sum + (msg.tokenCount || 0), 0),
      },
      tokenCount: summaryResponse.usage.totalTokens,
      sequenceId: -1, // Special sequence ID for summaries
    };

    return summaryMessage;
  }

  private buildSummaryPrompt(messages: DebateMessage[]): string {
    return `Summarize the following debate exchanges concisely while preserving:
- Key arguments from each participant
- Important evidence or citations
- Points of agreement and disagreement
- Evolution of positions

Debate exchanges:

${messages
  .map((msg, i) => {
    const speaker = msg.role === 'judge' ? 'Judge' : msg.metadata?.participantName || 'Speaker';
    return `[Round ${i + 1}] ${speaker}:\n${msg.content}\n`;
  })
  .join('\n---\n\n')}

Provide a comprehensive summary in 200-300 words.`;
  }
}
```

---

## 2. Token Counting Approaches per Provider

### 2.1 Provider-Specific Token Counting

**Anthropic Claude:**
```typescript
class AnthropicTokenCounter {
  constructor(private client: Anthropic) {}

  async count(text: string, model: string): Promise<number> {
    // Use Anthropic's counting API
    const response = await this.client.messages.countTokens({
      model,
      messages: [{ role: 'user', content: text }],
    });

    return response.input_tokens;
  }

  // For batch counting (more efficient)
  async countBatch(texts: string[], model: string): Promise<number[]> {
    const counts = await Promise.all(
      texts.map((text) => this.count(text, model))
    );
    return counts;
  }
}
```

**OpenAI (tiktoken):**
```typescript
import { encoding_for_model } from 'tiktoken';

class OpenAITokenCounter {
  private encoder: any;

  constructor(model: string = 'gpt-4o') {
    try {
      this.encoder = encoding_for_model(model as any);
    } catch {
      // Fallback to gpt-4o encoding
      this.encoder = encoding_for_model('gpt-4o');
    }
  }

  count(text: string): number {
    const tokens = this.encoder.encode(text);
    return tokens.length;
  }

  countBatch(texts: string[]): number[] {
    return texts.map((text) => this.count(text));
  }

  cleanup(): void {
    if (this.encoder.free) {
      this.encoder.free();
    }
  }
}
```

**Google Gemini:**
```typescript
class GeminiTokenCounter {
  constructor(private client: GoogleGenAI) {}

  async count(text: string, model: string): Promise<number> {
    const response = await this.client.models.countTokens({
      model,
      contents: [
        {
          role: 'user',
          parts: [{ text }],
        },
      ],
    });

    return response.totalTokens || 0;
  }
}
```

**Mistral (tiktoken approximation):**
```typescript
class MistralTokenCounter {
  private openaiCounter: OpenAITokenCounter;

  constructor() {
    // Mistral uses similar tokenization to GPT models
    this.openaiCounter = new OpenAITokenCounter('gpt-4o');
  }

  count(text: string): number {
    // Approximate with OpenAI's tokenizer
    return this.openaiCounter.count(text);
  }
}
```

### 2.2 Unified Token Counter

```typescript
class UnifiedTokenCounter {
  private counters: Map<ProviderType, any>;

  constructor(providers: Map<string, LLMProvider>) {
    this.counters = new Map();

    for (const [id, provider] of providers.entries()) {
      switch (provider.type) {
        case 'anthropic':
          this.counters.set(
            provider.type,
            new AnthropicTokenCounter(provider.client)
          );
          break;
        case 'openai':
          this.counters.set(
            provider.type,
            new OpenAITokenCounter(provider.config.model)
          );
          break;
        case 'google':
          this.counters.set(
            provider.type,
            new GeminiTokenCounter(provider.client)
          );
          break;
        case 'mistral':
          this.counters.set(provider.type, new MistralTokenCounter());
          break;
      }
    }
  }

  async count(text: string, provider: ProviderType, model?: string): Promise<number> {
    const counter = this.counters.get(provider);
    if (!counter) {
      // Fallback to approximation
      return this.approximateCount(text);
    }

    // Some counters are async (Anthropic, Gemini), others sync (OpenAI, Mistral)
    if (provider === 'anthropic' || provider === 'google') {
      return await counter.count(text, model);
    } else {
      return counter.count(text);
    }
  }

  private approximateCount(text: string): number {
    // Rough approximation: ~4 characters per token
    return Math.ceil(text.length / 4);
  }

  cleanup(): void {
    for (const counter of this.counters.values()) {
      if (counter.cleanup) {
        counter.cleanup();
      }
    }
  }
}
```

---

## 3. Cost Tracking Implementation

### 3.1 Real-Time Cost Estimation

```typescript
interface PricingModel {
  provider: ProviderType;
  model: string;
  inputCostPer1M: number; // USD per 1M input tokens
  outputCostPer1M: number; // USD per 1M output tokens
  lastUpdated: Date;
}

class RealTimeCostTracker {
  private pricingModels: Map<string, PricingModel>;
  private sessionCost: number = 0;
  private costHistory: CostRecord[] = [];

  constructor() {
    this.pricingModels = new Map();
    this.initializePricing();
  }

  private initializePricing(): void {
    // Pricing as of December 2025
    const models: PricingModel[] = [
      // Anthropic
      {
        provider: 'anthropic',
        model: 'claude-sonnet-4-5-20250929',
        inputCostPer1M: 3.0,
        outputCostPer1M: 15.0,
        lastUpdated: new Date('2025-11-01'),
      },
      {
        provider: 'anthropic',
        model: 'claude-3-5-haiku-20241022',
        inputCostPer1M: 0.8,
        outputCostPer1M: 4.0,
        lastUpdated: new Date('2024-10-01'),
      },

      // OpenAI
      {
        provider: 'openai',
        model: 'gpt-4o',
        inputCostPer1M: 2.5,
        outputCostPer1M: 10.0,
        lastUpdated: new Date('2024-08-01'),
      },
      {
        provider: 'openai',
        model: 'gpt-4o-mini',
        inputCostPer1M: 0.15,
        outputCostPer1M: 0.6,
        lastUpdated: new Date('2024-07-01'),
      },

      // Google
      {
        provider: 'google',
        model: 'gemini-2.5-flash',
        inputCostPer1M: 0.075,
        outputCostPer1M: 0.3,
        lastUpdated: new Date('2025-11-01'),
      },
      {
        provider: 'google',
        model: 'gemini-1.5-pro',
        inputCostPer1M: 1.25,
        outputCostPer1M: 5.0,
        lastUpdated: new Date('2024-05-01'),
      },

      // Mistral
      {
        provider: 'mistral',
        model: 'mistral-large-latest',
        inputCostPer1M: 2.0,
        outputCostPer1M: 6.0,
        lastUpdated: new Date('2024-09-01'),
      },
    ];

    for (const model of models) {
      const key = `${model.provider}:${model.model}`;
      this.pricingModels.set(key, model);
    }
  }

  trackRequest(
    provider: ProviderType,
    model: string,
    usage: TokenUsage
  ): CostRecord {
    const pricing = this.getPricing(provider, model);

    const inputCost = (usage.promptTokens / 1_000_000) * pricing.inputCostPer1M;
    const outputCost = (usage.completionTokens / 1_000_000) * pricing.outputCostPer1M;
    const totalCost = inputCost + outputCost;

    const record: CostRecord = {
      timestamp: Date.now(),
      provider,
      model,
      usage,
      inputCost,
      outputCost,
      totalCost,
    };

    this.costHistory.push(record);
    this.sessionCost += totalCost;

    return record;
  }

  estimateCost(
    provider: ProviderType,
    model: string,
    estimatedTokens: { input: number; output: number }
  ): number {
    const pricing = this.getPricing(provider, model);

    const inputCost = (estimatedTokens.input / 1_000_000) * pricing.inputCostPer1M;
    const outputCost = (estimatedTokens.output / 1_000_000) * pricing.outputCostPer1M;

    return inputCost + outputCost;
  }

  getSessionCost(): number {
    return this.sessionCost;
  }

  getCostByProvider(): Map<ProviderType, number> {
    const costs = new Map<ProviderType, number>();

    for (const record of this.costHistory) {
      const current = costs.get(record.provider) || 0;
      costs.set(record.provider, current + record.totalCost);
    }

    return costs;
  }

  getCostByDebater(debaterId: string): number {
    return this.costHistory
      .filter((r) => r.debaterId === debaterId)
      .reduce((sum, r) => sum + r.totalCost, 0);
  }

  private getPricing(provider: ProviderType, model: string): PricingModel {
    const key = `${provider}:${model}`;
    const pricing = this.pricingModels.get(key);

    if (!pricing) {
      console.warn(`No pricing for ${key}, using conservative estimate`);
      return {
        provider,
        model,
        inputCostPer1M: 5.0,
        outputCostPer1M: 15.0,
        lastUpdated: new Date(),
      };
    }

    return pricing;
  }
}

interface CostRecord {
  timestamp: number;
  provider: ProviderType;
  model: string;
  usage: TokenUsage;
  inputCost: number;
  outputCost: number;
  totalCost: number;
  debaterId?: string;
}
```

### 3.2 Cost Projection

```typescript
class CostProjector {
  constructor(private costTracker: RealTimeCostTracker) {}

  projectDebateCost(config: {
    debaters: number;
    rounds: number;
    avgTokensPerResponse: number;
    providers: Array<{ type: ProviderType; model: string }>;
  }): ProjectedCost {
    const { debaters, rounds, avgTokensPerResponse, providers } = config;

    // Calculate input tokens (grows with history)
    const avgInputTokensPerRound = (round: number) => {
      // Context grows: initial prompt + (round - 1) * debaters * avgTokens
      return 500 + (round - 1) * debaters * avgTokensPerResponse * 0.8; // 80% context retention
    };

    let totalCost = 0;
    const costBreakdown: CostBreakdownItem[] = [];

    for (let round = 1; round <= rounds; round++) {
      const inputTokens = avgInputTokensPerRound(round);

      for (const provider of providers) {
        const roundCost = this.costTracker.estimateCost(provider.type, provider.model, {
          input: inputTokens,
          output: avgTokensPerResponse,
        });

        totalCost += roundCost;

        costBreakdown.push({
          round,
          provider: provider.type,
          model: provider.model,
          inputTokens,
          outputTokens: avgTokensPerResponse,
          cost: roundCost,
        });
      }
    }

    // Add judge costs (every round or end-only)
    const judgeCost = this.estimateJudgeCost(rounds, providers[0]);
    totalCost += judgeCost;

    return {
      totalCost,
      breakdown: costBreakdown,
      judgeCost,
      perRound: totalCost / rounds,
      perDebater: totalCost / debaters,
    };
  }

  private estimateJudgeCost(
    rounds: number,
    judgeProvider: { type: ProviderType; model: string }
  ): number {
    // Judge processes full history at end
    const estimatedHistoryTokens = rounds * 4 * 500; // 4 debaters × 500 tokens
    const judgeOutputTokens = 800; // Structured assessment

    return this.costTracker.estimateCost(judgeProvider.type, judgeProvider.model, {
      input: estimatedHistoryTokens,
      output: judgeOutputTokens,
    });
  }
}

interface ProjectedCost {
  totalCost: number;
  breakdown: CostBreakdownItem[];
  judgeCost: number;
  perRound: number;
  perDebater: number;
}

interface CostBreakdownItem {
  round: number;
  provider: ProviderType;
  model: string;
  inputTokens: number;
  outputTokens: number;
  cost: number;
}
```

---

## 4. Warning Thresholds

### 4.1 Three-Tier Warning System

```typescript
enum CostWarningLevel {
  SAFE = 'safe',
  YELLOW = 'yellow',
  RED = 'red',
  CRITICAL = 'critical',
}

interface CostWarningConfig {
  yellowThreshold: number; // USD
  redThreshold: number; // USD
  criticalThreshold: number; // USD
  autoStopAtCritical: boolean;
}

class CostWarningSystem {
  private config: CostWarningConfig = {
    yellowThreshold: 0.5,
    redThreshold: 1.0,
    criticalThreshold: 2.0,
    autoStopAtCritical: true,
  };

  private lastWarningLevel: CostWarningLevel = CostWarningLevel.SAFE;
  private warnings: CostWarning[] = [];

  constructor(
    private costTracker: RealTimeCostTracker,
    config?: Partial<CostWarningConfig>
  ) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  checkCost(): CostWarning | null {
    const currentCost = this.costTracker.getSessionCost();
    const level = this.determineWarningLevel(currentCost);

    // Only emit warning if level changed
    if (level !== this.lastWarningLevel && level !== CostWarningLevel.SAFE) {
      const warning: CostWarning = {
        level,
        currentCost,
        threshold: this.getThreshold(level),
        timestamp: Date.now(),
        message: this.buildWarningMessage(level, currentCost),
        shouldStop: level === CostWarningLevel.CRITICAL && this.config.autoStopAtCritical,
      };

      this.warnings.push(warning);
      this.lastWarningLevel = level;

      return warning;
    }

    return null;
  }

  private determineWarningLevel(cost: number): CostWarningLevel {
    if (cost >= this.config.criticalThreshold) {
      return CostWarningLevel.CRITICAL;
    } else if (cost >= this.config.redThreshold) {
      return CostWarningLevel.RED;
    } else if (cost >= this.config.yellowThreshold) {
      return CostWarningLevel.YELLOW;
    } else {
      return CostWarningLevel.SAFE;
    }
  }

  private getThreshold(level: CostWarningLevel): number {
    switch (level) {
      case CostWarningLevel.YELLOW:
        return this.config.yellowThreshold;
      case CostWarningLevel.RED:
        return this.config.redThreshold;
      case CostWarningLevel.CRITICAL:
        return this.config.criticalThreshold;
      default:
        return 0;
    }
  }

  private buildWarningMessage(level: CostWarningLevel, cost: number): string {
    const formatted = cost.toFixed(2);

    switch (level) {
      case CostWarningLevel.YELLOW:
        return `⚠️ Cost Warning: Debate cost has reached $${formatted}. Consider wrapping up soon.`;

      case CostWarningLevel.RED:
        return `🔴 High Cost Alert: Debate cost is $${formatted}. Confirm to continue or stop now.`;

      case CostWarningLevel.CRITICAL:
        return `🛑 Critical Cost Limit: Debate cost has reached $${formatted}. ${
          this.config.autoStopAtCritical ? 'Debate will be stopped.' : 'Override required to continue.'
        }`;

      default:
        return '';
    }
  }

  getWarnings(): CostWarning[] {
    return this.warnings;
  }

  resetWarnings(): void {
    this.warnings = [];
    this.lastWarningLevel = CostWarningLevel.SAFE;
  }
}

interface CostWarning {
  level: CostWarningLevel;
  currentCost: number;
  threshold: number;
  timestamp: number;
  message: string;
  shouldStop: boolean;
}
```

### 4.2 UI Integration

```typescript
// React component example
function CostMonitor({ debateId }: { debateId: string }) {
  const [currentCost, setCurrentCost] = useState(0);
  const [warning, setWarning] = useState<CostWarning | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      const cost = costTracker.getSessionCost();
      setCurrentCost(cost);

      const newWarning = warningSystem.checkCost();
      if (newWarning) {
        setWarning(newWarning);

        // Show toast notification
        if (newWarning.level === CostWarningLevel.RED) {
          toast.warning(newWarning.message, {
            duration: 10000,
            action: {
              label: 'Continue',
              onClick: () => handleContinue(),
            },
          });
        } else if (newWarning.level === CostWarningLevel.CRITICAL) {
          toast.error(newWarning.message, {
            duration: Infinity,
            action: newWarning.shouldStop
              ? undefined
              : {
                  label: 'Override',
                  onClick: () => handleOverride(),
                },
          });

          if (newWarning.shouldStop) {
            handleStopDebate();
          }
        }
      }
    }, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const getWarningColor = () => {
    if (!warning) return 'text-green-600';
    switch (warning.level) {
      case CostWarningLevel.YELLOW:
        return 'text-yellow-600';
      case CostWarningLevel.RED:
        return 'text-red-600';
      case CostWarningLevel.CRITICAL:
        return 'text-red-800';
      default:
        return 'text-green-600';
    }
  };

  return (
    <div className="cost-monitor">
      <div className="cost-display">
        <span className="cost-label">Debate Cost:</span>
        <span className={`cost-value ${getWarningColor()}`}>
          ${currentCost.toFixed(4)}
        </span>
      </div>

      {warning && (
        <div className={`cost-warning cost-warning--${warning.level}`}>
          <AlertIcon />
          <span>{warning.message}</span>
        </div>
      )}

      {/* Cost breakdown by provider */}
      <CostBreakdown costTracker={costTracker} />
    </div>
  );
}
```

---

## 5. Key Recommendations

### 5.1 Architecture Decisions

✅ **Hybrid sliding window + summarization** - Best balance of efficiency and context preservation
✅ **Provider-specific token counting** - Use native APIs for accuracy
✅ **Real-time cost tracking** - Update after every LLM call
✅ **Three-tier warning system** - Clear escalation path ($0.50 → $1.00 → $2.00)
✅ **User control over limits** - Configurable thresholds

### 5.2 Implementation Priority

**Phase 2A (Weeks 1-2): Core Context Management**
- [ ] Sliding window manager (last-n-rounds strategy)
- [ ] Unified token counter with provider support
- [ ] Basic cost tracking (per-request)
- [ ] Warning system ($0.50, $1.00 thresholds)

**Phase 2B (Weeks 3-4): Advanced Features**
- [ ] Exponential decay strategy
- [ ] Importance-weighted strategy
- [ ] Summarization fallback
- [ ] Cost projection
- [ ] $2.00 critical threshold with auto-stop

**Phase 2C (Weeks 5-6): Optimization & UI**
- [ ] Cost breakdown by provider/debater
- [ ] Real-time UI updates
- [ ] User-configurable thresholds
- [ ] Export cost reports

---

## 6. Sources

**Token Counting:**
- [Token Counting Guide 2025](https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025)
- [tiktoken Documentation](https://github.com/openai/tiktoken)
- [Anthropic Token Counting API](https://docs.anthropic.com/en/docs/token-counting)

**Cost Tracking:**
- [LLM Cost Estimation Guide](https://medium.com/@alphaiterations/llm-cost-estimation-guide-from-token-usage-to-total-spend-fba348d62824)
- [LangFuse Token & Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking)
- [Provider Pricing Pages](https://openai.com/pricing) (Anthropic, OpenAI, Google, Mistral)

**Context Management:**
- [Context Window Best Practices](https://platform.openai.com/docs/guides/optimizing-context)
- [Sliding Window Patterns for LLMs](https://arxiv.org/abs/2307.03172)

---

**Research Complete:** Context management with sliding windows and real-time cost tracking with three-tier warnings is feasible and performant for multi-LLM debates.
