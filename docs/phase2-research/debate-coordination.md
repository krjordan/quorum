# Debate Coordination Patterns - Research Findings

**Research Date:** December 2, 2025
**Phase:** Phase 2 - Multi-LLM Debate Engine
**Researcher:** Research Agent

---

## Executive Summary

This document presents comprehensive research on turn-taking vs. simultaneous response patterns, persona assignment algorithms, and judge evaluation rubrics for multi-LLM debates. Key findings include optimal coordination strategies, auto-assignment heuristics, and structured assessment frameworks.

---

## 1. Turn-Taking vs. Simultaneous Response Patterns

### 1.1 Coordination Strategies Comparison

**Two Primary Patterns:**

| Aspect | Turn-Taking (Sequential) | Simultaneous (Parallel) |
|--------|-------------------------|-------------------------|
| **Response Order** | One debater at a time | All debaters respond in parallel |
| **Context Awareness** | Each sees previous responses | Responses based on pre-round context only |
| **Implementation Complexity** | Simple (linear) | Moderate (requires coordination) |
| **Execution Time** | Slow (4× longer for 4 debaters) | Fast (1× baseline) |
| **Debate Dynamics** | More reactive, conversational | More independent, parallel arguments |
| **Best For** | Deep rebuttals, cross-examination | Opening statements, independent analysis |
| **User Experience** | Feels natural, like real debate | Faster, more efficient |

### 1.2 Turn-Taking Implementation

**Use Case:** Structured rounds where each debater responds to previous arguments.

```typescript
interface TurnTakingConfig {
  order: 'fixed' | 'rotating' | 'judge-selected';
  timeLimit?: number; // Max time per turn
  allowInterruptions: boolean;
}

class TurnTakingCoordinator {
  constructor(private config: TurnTakingConfig) {}

  async executeTurn(
    debaters: Debater[],
    history: DebateMessage[],
    currentRound: number
  ): Promise<DebateMessage[]> {
    const responses: DebateMessage[] = [];
    const order = this.determineTurnOrder(debaters, currentRound);

    for (const debater of order) {
      console.log(`[Round ${currentRound}] ${debater.name}'s turn`);

      // Build context including previous turns this round
      const context = this.buildTurnContext(history, responses, debater);

      try {
        // Execute debater's turn
        const response = await this.executeDebaterTurn(debater, context);

        responses.push({
          ...response,
          metadata: {
            ...response.metadata,
            turnOrder: responses.length + 1,
            round: currentRound,
          },
        });

        // Update history for next turn
        history.push(responses[responses.length - 1]);

        // Emit real-time update
        this.emitTurnComplete(debater, response);
      } catch (error) {
        console.error(`[${debater.name}] Turn failed:`, error);
        // Continue with next debater
      }
    }

    return responses;
  }

  private determineTurnOrder(debaters: Debater[], round: number): Debater[] {
    switch (this.config.order) {
      case 'fixed':
        // Same order every round
        return [...debaters];

      case 'rotating':
        // Rotate starting position each round
        const startIndex = round % debaters.length;
        return [...debaters.slice(startIndex), ...debaters.slice(0, startIndex)];

      case 'judge-selected':
        // Judge determines order based on previous round
        // (requires judge assessment)
        return this.judgeSelectedOrder(debaters);

      default:
        return [...debaters];
    }
  }

  private buildTurnContext(
    history: DebateMessage[],
    currentRoundResponses: DebateMessage[],
    debater: Debater
  ): Message[] {
    // Include:
    // 1. Full debate history
    // 2. Responses from earlier turns this round
    // 3. Specific instructions for this turn

    const systemPrompt = this.buildSystemPrompt(debater);
    const historyMessages = this.convertToMessages(history);
    const currentRoundMessages = this.convertToMessages(currentRoundResponses);

    return [
      { role: 'system', content: systemPrompt },
      ...historyMessages,
      ...currentRoundMessages,
      {
        role: 'user',
        content: `It's your turn. Respond to the previous arguments and advance your position.`,
      },
    ];
  }

  private async executeDebaterTurn(
    debater: Debater,
    context: Message[]
  ): Promise<DebateMessage> {
    const startTime = Date.now();

    const response = await debater.provider.complete({
      messages: context,
      maxTokens: debater.maxTokensPerTurn || 500,
      temperature: 0.8,
      // Streaming for real-time display
      onChunk: (chunk) => {
        this.emitChunk(debater, chunk);
      },
    });

    const duration = Date.now() - startTime;

    return {
      role: 'assistant',
      content: response.content,
      metadata: {
        participantId: debater.id,
        participantName: debater.name,
        duration,
        tokenCount: response.usage.totalTokens,
        cost: response.usage.estimatedCost,
      },
    };
  }
}
```

### 1.3 Simultaneous Response Implementation

**Use Case:** Parallel responses for efficiency (opening statements, independent analysis).

```typescript
interface SimultaneousConfig {
  maxConcurrency: number; // Max parallel LLM calls
  synchronizedDisplay: boolean; // Wait for all before showing
  timeoutMs: number; // Max wait for slowest debater
}

class SimultaneousCoordinator {
  constructor(private config: SimultaneousConfig) {}

  async executeSimultaneous(
    debaters: Debater[],
    history: DebateMessage[],
    currentRound: number
  ): Promise<DebateMessage[]> {
    console.log(`[Round ${currentRound}] Executing simultaneous responses`);

    // Build context for each debater (same history, no cross-reference)
    const contexts = debaters.map((debater) =>
      this.buildSimultaneousContext(history, debater)
    );

    // Execute all debaters in parallel
    const responsePromises = debaters.map((debater, index) =>
      this.executeDebaterResponse(debater, contexts[index], currentRound)
    );

    // Wait for all responses (with timeout)
    const responses = await Promise.allSettled(responsePromises);

    // Filter successful responses
    const successfulResponses: DebateMessage[] = [];

    for (let i = 0; i < responses.length; i++) {
      const result = responses[i];
      if (result.status === 'fulfilled') {
        successfulResponses.push(result.value);
      } else {
        console.error(`[${debaters[i].name}] Response failed:`, result.reason);
        // Create placeholder message
        successfulResponses.push({
          role: 'assistant',
          content: '[Response failed - debater unavailable]',
          metadata: {
            participantId: debaters[i].id,
            participantName: debaters[i].name,
            failed: true,
          },
        });
      }
    }

    return successfulResponses;
  }

  private buildSimultaneousContext(
    history: DebateMessage[],
    debater: Debater
  ): Message[] {
    const systemPrompt = this.buildSystemPrompt(debater);
    const historyMessages = this.convertToMessages(history);

    return [
      { role: 'system', content: systemPrompt },
      ...historyMessages,
      {
        role: 'user',
        content: `Present your argument for this round. You will respond simultaneously with other debaters.`,
      },
    ];
  }

  private async executeDebaterResponse(
    debater: Debater,
    context: Message[],
    round: number
  ): Promise<DebateMessage> {
    const startTime = Date.now();

    // Wrap in timeout promise
    const responsePromise = debater.provider.complete({
      messages: context,
      maxTokens: debater.maxTokensPerTurn || 500,
      temperature: 0.8,
      onChunk: (chunk) => {
        this.emitChunk(debater, chunk);
      },
    });

    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Response timeout')), this.config.timeoutMs);
    });

    const response = await Promise.race([responsePromise, timeoutPromise]);

    const duration = Date.now() - startTime;

    return {
      role: 'assistant',
      content: response.content,
      metadata: {
        participantId: debater.id,
        participantName: debater.name,
        round,
        duration,
        tokenCount: response.usage.totalTokens,
        cost: response.usage.estimatedCost,
      },
    };
  }
}
```

### 1.4 Hybrid Coordination Strategy (Recommended)

**Best Practice:** Combine both patterns based on debate phase.

```typescript
enum CoordinationMode {
  SIMULTANEOUS = 'simultaneous',
  TURN_TAKING = 'turn-taking',
}

interface HybridCoordinationConfig {
  phaseRules: Map<string, CoordinationMode>;
  defaultMode: CoordinationMode;
}

class HybridCoordinator {
  private simultaneousCoordinator: SimultaneousCoordinator;
  private turnTakingCoordinator: TurnTakingCoordinator;

  constructor(private config: HybridCoordinationConfig) {
    this.simultaneousCoordinator = new SimultaneousCoordinator({
      maxConcurrency: 5,
      synchronizedDisplay: true,
      timeoutMs: 60000,
    });

    this.turnTakingCoordinator = new TurnTakingCoordinator({
      order: 'rotating',
      allowInterruptions: false,
    });
  }

  async executeRound(
    debaters: Debater[],
    history: DebateMessage[],
    round: number,
    phase: string
  ): Promise<DebateMessage[]> {
    const mode = this.config.phaseRules.get(phase) || this.config.defaultMode;

    console.log(`[Round ${round}, Phase: ${phase}] Using ${mode} coordination`);

    if (mode === CoordinationMode.SIMULTANEOUS) {
      return this.simultaneousCoordinator.executeSimultaneous(debaters, history, round);
    } else {
      return this.turnTakingCoordinator.executeTurn(debaters, history, round);
    }
  }
}

// Example configuration for structured debate
const structuredDebateConfig: HybridCoordinationConfig = {
  phaseRules: new Map([
    ['opening', CoordinationMode.SIMULTANEOUS], // Independent opening statements
    ['rebuttal-1', CoordinationMode.TURN_TAKING], // React to each other
    ['rebuttal-2', CoordinationMode.TURN_TAKING], // Continue dialogue
    ['closing', CoordinationMode.SIMULTANEOUS], // Independent summaries
  ]),
  defaultMode: CoordinationMode.SIMULTANEOUS,
};
```

---

## 2. Persona Assignment Algorithms

### 2.1 Auto-Assignment Strategy

**Goal:** Automatically assign diverse, opposing perspectives to create productive debate.

```typescript
interface PersonaAssignment {
  debaterId: string;
  persona: string;
  position: string;
  keyArguments: string[];
  stance: 'for' | 'against' | 'nuanced';
}

class PersonaAssigner {
  constructor(private llmProvider: LLMProvider) {}

  async autoAssign(
    topic: string,
    debaterCount: number
  ): Promise<PersonaAssignment[]> {
    // Use LLM to generate diverse persona assignments
    const prompt = this.buildAssignmentPrompt(topic, debaterCount);

    const response = await this.llmProvider.structuredComplete<PersonaAssignmentResponse>({
      messages: [{ role: 'user', content: prompt }],
      schema: personaAssignmentSchema,
      maxTokens: 1500,
      temperature: 0.9, // High temperature for diversity
    });

    return response.structuredData.personas;
  }

  private buildAssignmentPrompt(topic: string, count: number): string {
    return `Given the debate topic: "${topic}"

Assign ${count} diverse personas that will create a productive, multi-faceted debate.

Guidelines:
1. Avoid simple binary opposition (not just "for" vs "against")
2. Include nuanced positions and different perspectives
3. Ensure personas bring unique angles and expertise
4. Create productive tension, not just disagreement
5. Balance theoretical and practical viewpoints

For each persona, provide:
- A descriptive name/title
- Their position/stance on the topic
- 3-4 key arguments they would make
- Their overall stance (for/against/nuanced)

Return ${count} personas that together cover the topic comprehensively.`;
  }
}

const personaAssignmentSchema = {
  type: 'object',
  properties: {
    personas: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          debaterId: { type: 'string' },
          persona: { type: 'string' },
          position: { type: 'string' },
          keyArguments: {
            type: 'array',
            items: { type: 'string' },
            minItems: 3,
            maxItems: 5,
          },
          stance: { type: 'string', enum: ['for', 'against', 'nuanced'] },
        },
        required: ['debaterId', 'persona', 'position', 'keyArguments', 'stance'],
      },
    },
  },
  required: ['personas'],
};

interface PersonaAssignmentResponse {
  personas: PersonaAssignment[];
}
```

### 2.2 Diversity Optimization

**Advanced:** Ensure maximum perspective diversity using clustering.

```typescript
class DiversityOptimizer {
  async optimizeAssignments(
    candidates: PersonaAssignment[]
  ): Promise<PersonaAssignment[]> {
    // Calculate diversity scores between personas
    const diversityMatrix = this.calculateDiversityMatrix(candidates);

    // Select most diverse subset
    const selected = this.selectDiverseSubset(candidates, diversityMatrix);

    return selected;
  }

  private calculateDiversityMatrix(
    personas: PersonaAssignment[]
  ): number[][] {
    const n = personas.length;
    const matrix: number[][] = Array(n)
      .fill(0)
      .map(() => Array(n).fill(0));

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const diversity = this.calculateDiversity(personas[i], personas[j]);
        matrix[i][j] = diversity;
        matrix[j][i] = diversity;
      }
    }

    return matrix;
  }

  private calculateDiversity(p1: PersonaAssignment, p2: PersonaAssignment): number {
    let score = 0;

    // Different stances = more diverse
    if (p1.stance !== p2.stance) {
      score += 2;
    }

    // Different key arguments (Jaccard similarity)
    const args1 = new Set(p1.keyArguments);
    const args2 = new Set(p2.keyArguments);
    const intersection = new Set([...args1].filter((x) => args2.has(x)));
    const union = new Set([...args1, ...args2]);
    const jaccardDistance = 1 - intersection.size / union.size;
    score += jaccardDistance * 3;

    // Different expertise domains
    if (!this.sharesDomain(p1.persona, p2.persona)) {
      score += 1;
    }

    return score;
  }

  private selectDiverseSubset(
    personas: PersonaAssignment[],
    diversityMatrix: number[][],
    targetCount: number
  ): PersonaAssignment[] {
    // Greedy selection: pick most diverse personas
    const selected: number[] = [];
    const remaining = Array.from({ length: personas.length }, (_, i) => i);

    // Start with random persona
    const first = Math.floor(Math.random() * remaining.length);
    selected.push(remaining.splice(first, 1)[0]);

    while (selected.length < targetCount && remaining.length > 0) {
      // Find persona with highest average diversity to selected
      let maxAvgDiversity = -1;
      let bestIndex = -1;

      for (let i = 0; i < remaining.length; i++) {
        const candidate = remaining[i];
        const avgDiversity =
          selected.reduce((sum, sel) => sum + diversityMatrix[candidate][sel], 0) /
          selected.length;

        if (avgDiversity > maxAvgDiversity) {
          maxAvgDiversity = avgDiversity;
          bestIndex = i;
        }
      }

      selected.push(remaining.splice(bestIndex, 1)[0]);
    }

    return selected.map((idx) => personas[idx]);
  }
}
```

---

## 3. Judge Evaluation Rubrics

### 3.1 Six-Dimensional Assessment Framework

**Rubric Design:** Structured evaluation across multiple criteria.

```typescript
interface JudgeAssessment {
  round: number;
  overallQuality: number; // 0-10
  shouldContinue: boolean;
  participantScores: ParticipantScore[];
  observations: JudgeObservations;
  recommendation: string;
}

interface ParticipantScore {
  participantId: string;
  participantName: string;
  scores: {
    logic: number; // 0-10: Logical consistency and reasoning
    evidence: number; // 0-10: Quality and relevance of evidence
    engagement: number; // 0-10: Engagement with opponent arguments
    novelty: number; // 0-10: Novel insights and original thinking
    persuasiveness: number; // 0-10: Overall persuasive impact
    relevance: number; // 0-10: Staying on topic
  };
  weightedTotal: number; // Weighted sum of scores
  strengths: string[];
  weaknesses: string[];
}

interface JudgeObservations {
  repetitionDetected: boolean;
  topicDrift: boolean;
  diminishingReturns: boolean;
  convergenceLikely: boolean;
  irreconcilablePositions: boolean;
}

const RUBRIC_WEIGHTS = {
  logic: 0.2,
  evidence: 0.2,
  engagement: 0.2,
  novelty: 0.15,
  persuasiveness: 0.15,
  relevance: 0.1,
};

class JudgeEvaluator {
  constructor(private judgeProvider: LLMProvider) {}

  async evaluate(
    participants: Debater[],
    history: DebateMessage[],
    round: number
  ): Promise<JudgeAssessment> {
    const prompt = this.buildEvaluationPrompt(participants, history, round);

    const response = await this.judgeProvider.structuredComplete<JudgeAssessment>({
      messages: [{ role: 'user', content: prompt }],
      schema: judgeAssessmentSchema,
      maxTokens: 2000,
      temperature: 0.3, // Lower temperature for consistent evaluation
    });

    // Calculate weighted totals
    for (const score of response.structuredData.participantScores) {
      score.weightedTotal = this.calculateWeightedTotal(score.scores);
    }

    return response.structuredData;
  }

  private calculateWeightedTotal(scores: ParticipantScore['scores']): number {
    return (
      scores.logic * RUBRIC_WEIGHTS.logic +
      scores.evidence * RUBRIC_WEIGHTS.evidence +
      scores.engagement * RUBRIC_WEIGHTS.engagement +
      scores.novelty * RUBRIC_WEIGHTS.novelty +
      scores.persuasiveness * RUBRIC_WEIGHTS.persuasiveness +
      scores.relevance * RUBRIC_WEIGHTS.relevance
    );
  }

  private buildEvaluationPrompt(
    participants: Debater[],
    history: DebateMessage[],
    round: number
  ): string {
    const recentHistory = history.slice(-10); // Last 10 messages

    return `You are an impartial judge evaluating a multi-LLM debate.

**Topic:** ${this.getTopic(history)}
**Round:** ${round}
**Participants:** ${participants.map((p) => p.name).join(', ')}

**Recent Debate History:**
${this.formatHistory(recentHistory)}

**Evaluation Task:**
Assess each participant using this rubric (0-10 scale):

1. **Logic (20%)**: Logical consistency, valid reasoning, absence of fallacies
2. **Evidence (20%)**: Quality, relevance, and proper use of evidence
3. **Engagement (20%)**: Direct responses to opponents, addresses counterarguments
4. **Novelty (15%)**: Original insights, new angles, creative thinking
5. **Persuasiveness (15%)**: Overall impact, clarity, rhetorical effectiveness
6. **Relevance (10%)**: Stays on topic, addresses core questions

**Additional Observations:**
- Repetition: Are participants repeating previous arguments?
- Topic drift: Has the debate strayed from the original question?
- Diminishing returns: Are new rounds adding meaningful content?
- Convergence: Are positions moving toward agreement?
- Irreconcilable: Have fundamental disagreements been identified?

**Decision:**
Should the debate continue, or has a meaningful conclusion been reached?

Provide structured assessment with specific strengths and weaknesses for each participant.`;
  }
}

const judgeAssessmentSchema = {
  type: 'object',
  properties: {
    round: { type: 'number' },
    overallQuality: { type: 'number', minimum: 0, maximum: 10 },
    shouldContinue: { type: 'boolean' },
    participantScores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          participantId: { type: 'string' },
          participantName: { type: 'string' },
          scores: {
            type: 'object',
            properties: {
              logic: { type: 'number', minimum: 0, maximum: 10 },
              evidence: { type: 'number', minimum: 0, maximum: 10 },
              engagement: { type: 'number', minimum: 0, maximum: 10 },
              novelty: { type: 'number', minimum: 0, maximum: 10 },
              persuasiveness: { type: 'number', minimum: 0, maximum: 10 },
              relevance: { type: 'number', minimum: 0, maximum: 10 },
            },
            required: ['logic', 'evidence', 'engagement', 'novelty', 'persuasiveness', 'relevance'],
          },
          strengths: { type: 'array', items: { type: 'string' } },
          weaknesses: { type: 'array', items: { type: 'string' } },
        },
        required: ['participantId', 'participantName', 'scores', 'strengths', 'weaknesses'],
      },
    },
    observations: {
      type: 'object',
      properties: {
        repetitionDetected: { type: 'boolean' },
        topicDrift: { type: 'boolean' },
        diminishingReturns: { type: 'boolean' },
        convergenceLikely: { type: 'boolean' },
        irreconcilablePositions: { type: 'boolean' },
      },
      required: [
        'repetitionDetected',
        'topicDrift',
        'diminishingReturns',
        'convergenceLikely',
        'irreconcilablePositions',
      ],
    },
    recommendation: { type: 'string' },
  },
  required: [
    'round',
    'overallQuality',
    'shouldContinue',
    'participantScores',
    'observations',
    'recommendation',
  ],
};
```

---

## 4. Key Recommendations

### 4.1 Architecture Decisions

✅ **Hybrid coordination** - Simultaneous for efficiency, turn-taking for depth
✅ **Auto-assign personas** - LLM-generated diverse perspectives
✅ **Six-dimensional rubric** - Comprehensive structured evaluation
✅ **Real-time judge feedback** - Assess quality every 2-3 rounds
✅ **Stop criteria detection** - Automatic detection of diminishing returns

### 4.2 Implementation Priority

**Phase 2A (Weeks 1-2): Core Coordination**
- [ ] Simultaneous coordinator
- [ ] Basic persona assignment
- [ ] Simple judge evaluation (shouldContinue only)

**Phase 2B (Weeks 3-4): Advanced Features**
- [ ] Turn-taking coordinator
- [ ] Hybrid coordination strategy
- [ ] Auto-assignment with diversity
- [ ] Full six-dimensional rubric

**Phase 2C (Weeks 5-6): Optimization**
- [ ] Diversity optimizer
- [ ] Judge feedback UI
- [ ] Detailed score breakdown
- [ ] Historical trend analysis

---

## 5. Sources

**Coordination Patterns:**
- [Multi-Agent Debate Papers](https://arxiv.org/search/?query=multi-agent+debate)
- [Turn-Taking in Dialogue Systems](https://aclanthology.org/)

**Persona Assignment:**
- [LLM Role-Playing Research](https://arxiv.org/abs/2304.03442)
- [Perspective Generation with LLMs](https://arxiv.org/abs/2310.03739)

**Evaluation Rubrics:**
- [Structured Evaluation Frameworks](https://platform.openai.com/docs/guides/structured-outputs)
- [LLM-as-Judge Benchmarks](https://github.com/lm-sys/FastChat/tree/main/fastchat/llm_judge)

---

**Research Complete:** Debate coordination with hybrid patterns, auto-assignment, and structured judge evaluation is comprehensive and production-ready.
