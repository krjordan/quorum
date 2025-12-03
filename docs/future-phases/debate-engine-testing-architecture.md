# Debate Engine Architecture & Testing Strategy
## Comprehensive Research Analysis for Quorum Platform

**Author**: TESTER Agent (Quorum Hive Mind Collective)
**Date**: November 29, 2025
**Version**: 1.0

---

## Executive Summary

This document provides a comprehensive analysis of debate engine architecture patterns and testing strategies for the Quorum multi-LLM debate platform. Based on extensive research of existing state management specifications, API integration designs, and industry best practices, this analysis delivers actionable recommendations for building a robust, testable debate orchestration system.

**Key Deliverables:**
1. Finite state machine specification for debate lifecycle
2. Prompt engineering architecture with template examples
3. Context management strategy with overflow handling
4. Judge agent design with structured evaluation rubric
5. Comprehensive testing strategy with specific scenarios
6. Error handling and recovery patterns
7. Implementation roadmap and code structure recommendations

---

## Table of Contents

1. [State Machine Design](#1-state-machine-design)
2. [Prompt Engineering Architecture](#2-prompt-engineering-architecture)
3. [Context Management Strategy](#3-context-management-strategy)
4. [Judge Agent Design](#4-judge-agent-design)
5. [Testing Strategy](#5-testing-strategy)
6. [Error Handling & Recovery](#6-error-handling--recovery)
7. [Implementation Recommendations](#7-implementation-recommendations)
8. [Research Sources](#8-research-sources)

---

## 1. State Machine Design

### 1.1 Debate Lifecycle State Machine

Based on research into finite state machines for conversational AI and the existing state management specification, the debate lifecycle follows a well-defined state transition model.

#### State Diagram

```
┌──────────────┐
│ CONFIGURING  │ ← Initial state
└──────┬───────┘
       │ VALIDATE
       ▼
┌──────────────┐
│  VALIDATING  │ ← Async validation of config + API keys
└──────┬───────┘
       │ onDone
       ▼
┌──────────────┐
│    READY     │ ← Debate configured and validated
└──────┬───────┘
       │ START
       ▼
┌──────────────┐
│ INITIALIZING │ ← Auto-assign personas, init participants
└──────┬───────┘
       │ onDone
       ▼
┌────────────────────────────────────────┐
│            RUNNING                     │
│  ┌─────────────────────────────────┐  │
│  │   AWAITING_RESPONSES            │  │ ← Streaming participant responses
│  └──────┬──────────────────────────┘  │
│         │ onDone (all complete)       │
│         ▼                             │
│  ┌─────────────────────────────────┐  │
│  │        JUDGING                  │  │ ← Judge evaluates round
│  └──────┬──────────────────────────┘  │
│         │                             │
│         ├─ shouldEndDebate? YES ──────┼─► COMPLETING
│         │                             │
│         └─ shouldEndDebate? NO        │
│                ▼                      │
│  ┌─────────────────────────────────┐  │
│  │    ROUND_COMPLETE               │  │ ← Brief pause, increment round
│  └──────┬──────────────────────────┘  │
│         │ after 1s                    │
│         └─► canContinue? ─────────────┤
│                                        │
│         PAUSE ────► PAUSED             │
│         FORCE_STOP ──► COMPLETING      │
└────────────────────────────────────────┘
                │
                ▼
         ┌──────────────┐
         │  COMPLETING  │ ← Generate final verdict
         └──────┬───────┘
                │ onDone
                ▼
         ┌──────────────┐
         │  COMPLETED   │ ← Final state, save to history
         └──────────────┘

         ┌──────────────┐
         │    ERROR     │ ← Error state with recovery options
         └──────────────┘
```

#### State Definitions

**CONFIGURING**
- **Purpose**: User sets up debate parameters
- **Data**: Topic, format, mode, participant selection, judge selection
- **Transitions**: VALIDATE → validating
- **Actions**: None
- **User Actions**: Edit config, add/remove participants

**VALIDATING**
- **Purpose**: Async validation of configuration
- **Validations**:
  - Topic non-empty
  - 2-4 participants selected
  - Judge selected
  - API keys valid for selected providers
  - Models available
- **Transitions**:
  - Success → ready
  - Failure → configuring (with error messages)
- **Actions**: Call provider validation APIs

**READY**
- **Purpose**: Debate ready to start
- **Data**: Validated configuration
- **Transitions**:
  - START → initializing
  - EDIT_CONFIG → configuring
- **Actions**: None
- **User Actions**: Start debate, edit configuration

**INITIALIZING**
- **Purpose**: Prepare debate for execution
- **Operations**:
  - Auto-assign personas (if auto-mode)
  - Initialize participant state (empty response history, zero token usage)
  - Initialize judge state
  - Set currentRound = 1
  - Record startedAt timestamp
- **Transitions**:
  - Success → running
  - Failure → error
- **Actions**: `initializeDebate` service

**RUNNING** (Compound State)
- **Purpose**: Active debate execution
- **Sub-states**: AWAITING_RESPONSES, JUDGING, ROUND_COMPLETE
- **Data**: Participants, judge, responses, current round
- **Transitions**:
  - PAUSE → paused
  - FORCE_STOP → completing
- **Actions**: Stream management, state updates

**RUNNING.AWAITING_RESPONSES**
- **Purpose**: Generate participant responses
- **Mode**: Simultaneous or sequential (per config)
- **Events**:
  - RESPONSE_CHUNK → Update streaming content
  - RESPONSE_COMPLETE → Finalize response, update token usage
  - RESPONSE_ERROR → Handle participant error
- **Transitions**: All responses complete → judging
- **Actions**: `streamResponses` service

**RUNNING.JUDGING**
- **Purpose**: Judge evaluates round quality
- **Input**: All participant responses from current round
- **Output**: RoundAssessment with shouldContinue flag
- **Transitions**:
  - shouldEndDebate = true → completing
  - shouldEndDebate = false → round_complete
- **Actions**: `getJudgeAssessment` service

**RUNNING.ROUND_COMPLETE**
- **Purpose**: Brief pause before next round
- **Delay**: 1 second
- **Transitions**:
  - canContinue = true → awaiting_responses (increment round)
  - canContinue = false → completing
- **Guards**: Check for errors, context overflow, round limits

**PAUSED**
- **Purpose**: User-initiated pause
- **Data**: Preserve all state
- **Transitions**:
  - RESUME → running
  - STOP → completing
- **Actions**: None
- **User Actions**: Resume, force stop

**COMPLETING**
- **Purpose**: Generate final verdict
- **Operations**:
  - Judge generates comprehensive final verdict
  - Includes summary, key points, areas of agreement/disagreement, winner (optional)
- **Transitions**:
  - Success → completed
  - Failure → error
- **Actions**: `getFinalVerdict` service

**COMPLETED**
- **Purpose**: Debate finished successfully
- **Type**: Final state
- **Entry Actions**: Save debate to history, persist to storage
- **User Actions**: Export, replay, start new debate

**ERROR**
- **Purpose**: Handle unrecoverable errors
- **Data**: Error details, context
- **Transitions**:
  - RETRY → ready (if recoverable)
  - RESET → configuring (start over)
- **Actions**: Log error, notify user
- **User Actions**: Retry, reset, view error details

### 1.2 State Transition Guards

Guards prevent invalid state transitions and enforce business rules.

```typescript
const guards = {
  hasValidConfig: (context: DebateContext) => {
    return (
      context.config?.topic?.trim().length > 0 &&
      context.config?.participants?.length >= 2 &&
      context.config?.participants?.length <= 4 &&
      context.config?.judgeConfig != null
    );
  },

  shouldEndDebate: (context: DebateContext, event: AssessmentEvent) => {
    const assessment = event.data;
    const config = context.config;

    // Round-limited format
    if (config.format === 'round-limited') {
      return context.currentRound >= config.roundLimit!;
    }

    // Convergence-seeking format
    if (config.format === 'convergence-seeking') {
      return (
        assessment.flags.convergenceReached ||
        assessment.flags.diminishingReturns
      );
    }

    // Structured rounds format
    if (config.format === 'structured-rounds') {
      const phase = getDebatePhase(context.currentRound);
      return phase === 'closing' && !assessment.shouldContinue;
    }

    // Free-form format: judge decides
    return !assessment.shouldContinue;
  },

  canContinue: (context: DebateContext) => {
    // Check for unrecoverable errors
    const hasUnrecoverableErrors = Object.values(context.participants).some(
      (p) => p.status === 'error' && !p.errors.some(e => e.retryable)
    );

    if (hasUnrecoverableErrors) return false;

    // Check for context overflow
    const hasContextOverflow = Object.values(context.participants).some(
      (p) => p.status === 'context-exceeded'
    );

    if (hasContextOverflow) return false;

    // Check rate limiting (all participants rate-limited)
    const allRateLimited = Object.values(context.participants).every(
      (p) => p.status === 'rate-limited'
    );

    if (allRateLimited) return false;

    return true;
  },

  isAuthenticated: (context: DebateContext, providerId: string) => {
    const provider = context.providers[providerId];
    return provider?.validationStatus === 'valid';
  }
};
```

### 1.3 State Machine Implementation (XState)

```typescript
import { createMachine, assign } from 'xstate';

export const debateMachine = createMachine(
  {
    id: 'debate',
    initial: 'configuring',
    context: {
      config: null,
      currentRound: 0,
      participants: {},
      judge: null,
      errors: [],
      providers: {},
    },
    states: {
      configuring: {
        on: {
          SET_CONFIG: {
            actions: assign({
              config: (_, event) => event.config,
            }),
          },
          VALIDATE: {
            target: 'validating',
          },
        },
      },

      validating: {
        invoke: {
          src: 'validateConfiguration',
          onDone: {
            target: 'ready',
            actions: assign({ errors: [] }),
          },
          onError: {
            target: 'configuring',
            actions: assign({
              errors: (_, event) => event.data.errors,
            }),
          },
        },
      },

      ready: {
        on: {
          START: {
            target: 'initializing',
            cond: 'hasValidConfig',
          },
          EDIT_CONFIG: 'configuring',
        },
      },

      initializing: {
        invoke: {
          src: 'initializeDebate',
          onDone: {
            target: 'running',
            actions: assign({
              participants: (_, event) => event.data.participants,
              judge: (_, event) => event.data.judge,
              currentRound: 1,
              startedAt: () => Date.now(),
            }),
          },
          onError: {
            target: 'error',
            actions: assign({ errors: (_, event) => [event.data] }),
          },
        },
      },

      running: {
        initial: 'awaitingResponses',
        on: {
          PAUSE: 'paused',
          FORCE_STOP: 'completing',
        },
        states: {
          awaitingResponses: {
            invoke: {
              src: 'streamResponses',
              onDone: 'judging',
            },
            on: {
              RESPONSE_CHUNK: {
                actions: 'updateStreamingResponse',
              },
              RESPONSE_COMPLETE: {
                actions: 'finalizeResponse',
              },
              RESPONSE_ERROR: {
                actions: 'handleResponseError',
              },
            },
          },

          judging: {
            invoke: {
              src: 'getJudgeAssessment',
              onDone: [
                {
                  target: '#debate.completing',
                  cond: 'shouldEndDebate',
                  actions: 'storeAssessment',
                },
                {
                  target: 'roundComplete',
                  actions: 'storeAssessment',
                },
              ],
              onError: {
                target: 'awaitingResponses',
                actions: 'handleJudgeError',
              },
            },
          },

          roundComplete: {
            after: {
              1000: [
                {
                  target: 'awaitingResponses',
                  cond: 'canContinue',
                  actions: assign({
                    currentRound: (ctx) => ctx.currentRound + 1,
                  }),
                },
                {
                  target: '#debate.completing',
                },
              ],
            },
          },
        },
      },

      paused: {
        on: {
          RESUME: 'running',
          STOP: 'completing',
        },
      },

      completing: {
        invoke: {
          src: 'getFinalVerdict',
          onDone: {
            target: 'completed',
            actions: assign({
              judge: (ctx, event) => ({
                ...ctx.judge,
                finalVerdict: event.data,
              }),
              completedAt: () => Date.now(),
            }),
          },
          onError: {
            target: 'error',
            actions: assign({ errors: (_, event) => [event.data] }),
          },
        },
      },

      completed: {
        type: 'final',
        entry: 'saveDebateToHistory',
      },

      error: {
        on: {
          RETRY: {
            target: 'ready',
            actions: assign({ errors: [] }),
          },
          RESET: 'configuring',
        },
      },
    },
  },
  {
    guards,
    actions: {
      // Actions defined in section 1.4
    },
    services: {
      // Services defined in implementation section
    },
  }
);
```

### 1.4 Key Research Insights on FSM for Debates

Based on research into [finite state machines for conversational AI](https://meta-guide.com/dialog-systems/state-machine-dialog-systems), several insights emerged:

**Advantages for Quorum:**
- **Predictable Flow**: State machines provide clear, predictable conversation flow essential for structured debates
- **Error Recovery**: Well-defined error states enable graceful recovery from API failures
- **Visualizable**: State diagrams help contributors understand system behavior
- **Testable**: Each state transition can be unit tested independently

**Limitations to Address:**
- **Rigidity**: Pure FSMs can feel robotic; mitigate with dynamic prompt generation
- **Complexity**: Deep nesting can become unwieldy; keep state machine focused on lifecycle, not content
- **Scaling**: XState provides excellent tooling for visualizing and debugging complex state machines

**Best Practice** (from [Guiding AI Conversations through Dynamic State Transitions](https://promptengineering.org/guiding-ai-conversations-through-dynamic-state-transitions/)):
> "State machines are integral components underlying many dialog systems, enabling them to model conversational flow, interpret user intent, and manage interactions."

For Quorum, the hybrid approach works best:
- **XState** manages debate lifecycle (setup → execution → completion)
- **Dynamic prompts** handle conversational content within each state
- **Zustand** stores debate data (responses, assessments, context)

---

## 2. Prompt Engineering Architecture

### 2.1 Prompt Template System

Based on research into [multi-agent debate prompts](https://arxiv.org/html/2502.02533v1) and [LLM design patterns](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/multi-agent-debate.html), the prompt system must support:

1. **Role Assignment**: Clear persona and position definition
2. **Context Awareness**: Knowledge of other participants and debate history
3. **Format Instructions**: Response structure and length guidelines
4. **Cross-Referencing**: Ability to directly engage with other participants

#### Debater System Prompt Template

```typescript
interface DebaterPromptParams {
  topic: string;
  participantName: string;
  position: string;
  persona: string;
  otherParticipants: Array<{ name: string; position: string }>;
  format: DebateFormat;
  currentRound: number;
  maxRounds?: number;
  instructions?: string;
}

export function buildDebaterSystemPrompt(params: DebaterPromptParams): string {
  const {
    topic,
    participantName,
    position,
    persona,
    otherParticipants,
    format,
    currentRound,
    maxRounds,
    instructions,
  } = params;

  // Format-specific instructions
  const formatInstructions = getFormatInstructions(format, currentRound, maxRounds);

  // Build other participants list
  const othersList = otherParticipants
    .map((p) => `  - ${p.name}: ${p.position}`)
    .join('\n');

  return `You are participating in a structured debate on the topic:

"${topic}"

═══════════════════════════════════════════════════════════════

YOUR ROLE:
  • Name: ${participantName}
  • Position: ${position}
  • Persona: ${persona}

OTHER PARTICIPANTS:
${othersList}

═══════════════════════════════════════════════════════════════

DEBATE FORMAT: ${format.toUpperCase()}
CURRENT ROUND: ${currentRound}${maxRounds ? ` of ${maxRounds}` : ''}

${formatInstructions}

═══════════════════════════════════════════════════════════════

CORE INSTRUCTIONS:

1. STAY IN CHARACTER
   - Argue consistently from your assigned position: "${position}"
   - Embody your persona: "${persona}"
   - Don't break character or acknowledge being an AI

2. ENGAGE DIRECTLY WITH OPPONENTS
   - Reference other participants by name (e.g., "${otherParticipants[0]?.name} argues that...")
   - Address specific points they've made
   - Build on, refute, or extend their arguments
   - Don't just make independent statements

3. PRESENT STRONG ARGUMENTS
   - Provide evidence, reasoning, and examples
   - Use logical argumentation
   - Anticipate counterarguments
   - Be persuasive but respectful

4. BUILD ON PREVIOUS ROUNDS
   - Reference points made in earlier rounds
   - Show progression of ideas
   - Don't simply repeat yourself
   - Develop and deepen your position

5. MAINTAIN APPROPRIATE LENGTH
   - Aim for 2-4 substantive paragraphs
   - Be concise but thorough
   - Quality over quantity

${instructions ? `\n6. ADDITIONAL INSTRUCTIONS\n   ${instructions}\n` : ''}
═══════════════════════════════════════════════════════════════

Your goal: Make the strongest case for your position while engaging meaningfully with opposing viewpoints.`;
}

function getFormatInstructions(
  format: DebateFormat,
  currentRound: number,
  maxRounds?: number
): string {
  switch (format) {
    case 'structured-rounds':
      const phase = getStructuredPhase(currentRound);
      return `
STRUCTURED ROUNDS FORMAT:
  • Opening (Round 1): Present your initial position and main arguments
  • Rebuttals (Rounds 2-${maxRounds! - 1}): Respond to opponents and strengthen your case
  • Closing (Round ${maxRounds}): Summarize your strongest points and final statement

Current Phase: ${phase.toUpperCase()}
${getPhaseInstructions(phase)}`;

    case 'round-limited':
      return `
ROUND-LIMITED FORMAT:
  • Maximum ${maxRounds} rounds total
  • Each round builds on previous discussion
  • Make your arguments count - limited turns remaining
  • Round ${currentRound} of ${maxRounds}`;

    case 'convergence-seeking':
      return `
CONVERGENCE-SEEKING FORMAT:
  • Seek areas of agreement while maintaining your position
  • Identify common ground when possible
  • Clarify disagreements constructively
  • Work toward synthesis or mutual understanding
  • Debate continues until convergence or irreconcilable differences`;

    case 'free-form':
    default:
      return `
FREE-FORM FORMAT:
  • No predetermined structure
  • Respond naturally to the ongoing discussion
  • Judge determines when meaningful conclusions are reached
  • Maintain depth and relevance throughout`;
  }
}

function getStructuredPhase(round: number): 'opening' | 'rebuttal' | 'closing' {
  if (round === 1) return 'opening';
  // Assume closing is always the last round (determined by maxRounds)
  // For now, default to rebuttal
  return 'rebuttal';
}

function getPhaseInstructions(phase: string): string {
  switch (phase) {
    case 'opening':
      return '  → Present your core thesis and primary supporting arguments';
    case 'rebuttal':
      return '  → Address opponents\' arguments and reinforce your position';
    case 'closing':
      return '  → Deliver final summary and strongest concluding statement';
    default:
      return '';
  }
}
```

#### Example Debater Prompt (Generated)

```
You are participating in a structured debate on the topic:

"Should we prioritize Mars colonization over solving Earth's climate crisis?"

═══════════════════════════════════════════════════════════════

YOUR ROLE:
  • Name: Claude (Pro-Mars)
  • Position: Mars colonization should be the priority
  • Persona: Futurist technologist focused on long-term species survival

OTHER PARTICIPANTS:
  - GPT-4 (Pro-Earth): Climate crisis demands immediate attention
  - Gemini (Balanced): Both deserve resources but climate is urgent

═══════════════════════════════════════════════════════════════

DEBATE FORMAT: STRUCTURED-ROUNDS
CURRENT ROUND: 2 of 5

STRUCTURED ROUNDS FORMAT:
  • Opening (Round 1): Present your initial position and main arguments
  • Rebuttals (Rounds 2-4): Respond to opponents and strengthen your case
  • Closing (Round 5): Summarize your strongest points and final statement

Current Phase: REBUTTAL
  → Address opponents' arguments and reinforce your position

═══════════════════════════════════════════════════════════════

CORE INSTRUCTIONS:

1. STAY IN CHARACTER
   - Argue consistently from your assigned position: "Mars colonization should be the priority"
   - Embody your persona: "Futurist technologist focused on long-term species survival"
   - Don't break character or acknowledge being an AI

2. ENGAGE DIRECTLY WITH OPPONENTS
   - Reference other participants by name (e.g., "GPT-4 argues that...")
   - Address specific points they've made
   - Build on, refute, or extend their arguments
   - Don't just make independent statements

3. PRESENT STRONG ARGUMENTS
   - Provide evidence, reasoning, and examples
   - Use logical argumentation
   - Anticipate counterarguments
   - Be persuasive but respectful

4. BUILD ON PREVIOUS ROUNDS
   - Reference points made in earlier rounds
   - Show progression of ideas
   - Don't simply repeat yourself
   - Develop and deepen your position

5. MAINTAIN APPROPRIATE LENGTH
   - Aim for 2-4 substantive paragraphs
   - Be concise but thorough
   - Quality over quantity

═══════════════════════════════════════════════════════════════

Your goal: Make the strongest case for your position while engaging meaningfully with opposing viewpoints.
```

### 2.2 Judge System Prompt with Structured Output

Based on [LLM-as-judge research](https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method) and [structured output patterns](https://towardsdatascience.com/llm-as-a-judge-a-practical-guide/), the judge requires:

1. **Structured JSON output** (not free-form text)
2. **Clear evaluation rubric** with specific criteria
3. **Stopping criteria logic** (when to end debate)
4. **Pairwise comparison** across participants

```typescript
interface JudgePromptParams {
  topic: string;
  participants: Array<{ name: string; position: string }>;
  format: DebateFormat;
  currentRound: number;
  evaluationCriteria?: string[];
}

export function buildJudgeSystemPrompt(params: JudgePromptParams): string {
  const {
    topic,
    participants,
    format,
    currentRound,
    evaluationCriteria,
  } = params;

  const participantsList = participants
    .map((p) => `  - ${p.name}: ${p.position}`)
    .join('\n');

  const criteria = evaluationCriteria || [
    'Logical consistency and reasoning',
    'Evidence quality and relevance',
    'Direct engagement with opposing arguments',
    'Novel insights vs repetition',
    'Clarity and persuasiveness',
    'Relevance to topic',
  ];

  const criteriaList = criteria.map((c, i) => `  ${i + 1}. ${c}`).join('\n');

  return `You are an IMPARTIAL JUDGE evaluating a debate on:

"${topic}"

═══════════════════════════════════════════════════════════════

PARTICIPANTS:
${participantsList}

DEBATE FORMAT: ${format.toUpperCase()}
CURRENT ROUND: ${currentRound}

═══════════════════════════════════════════════════════════════

YOUR RESPONSIBILITIES:

1. EVALUATE ARGUMENT QUALITY
   - Assess each participant's reasoning and evidence
   - Identify strengths and weaknesses
   - Be fair and balanced in evaluation

2. DETECT DIMINISHING RETURNS
   - Identify repetitive arguments
   - Note when participants are rehashing old points
   - Recognize when discussion has plateaued

3. IDENTIFY TOPIC DRIFT
   - Ensure participants stay on topic
   - Flag tangential or irrelevant discussions
   - Assess relevance to original debate question

4. DETERMINE CONTINUATION
   - Decide if debate should continue or conclude
   - Consider: Are new insights emerging?
   - Consider: Have positions been thoroughly explored?
   - Consider: Is further discussion productive?

5. PROVIDE STRUCTURED ASSESSMENT
   - Follow the exact JSON schema provided
   - Be specific in strengths/weaknesses
   - Provide clear reasoning for decisions

═══════════════════════════════════════════════════════════════

EVALUATION CRITERIA:
${criteriaList}

═══════════════════════════════════════════════════════════════

OUTPUT FORMAT (MUST BE VALID JSON):

You must respond with a JSON object matching this exact structure:

{
  "shouldContinue": boolean,
  "qualityScore": number (0-10),
  "assessments": [
    {
      "participant": "participant name",
      "strengths": ["specific strength 1", "specific strength 2"],
      "weaknesses": ["specific weakness 1", "specific weakness 2"],
      "score": number (0-10)
    }
  ],
  "flags": {
    "repetitive": boolean,
    "drifting": boolean,
    "diminishingReturns": boolean,
    "convergenceReached": boolean
  },
  "reasoning": "Brief explanation of your assessment and decision",
  "recommendations": "What should happen next (continue with guidance, conclude, etc.)"
}

═══════════════════════════════════════════════════════════════

JUDGING GUIDELINES:

• BE OBJECTIVE: Don't favor any position or participant
• BE SPECIFIC: Cite actual arguments when noting strengths/weaknesses
• BE DECISIVE: Make clear determination on shouldContinue
• BE CONCISE: Keep reasoning focused and actionable

Your assessment will determine whether this debate continues or concludes.`;
}
```

#### Judge JSON Schema

```typescript
export const JUDGE_ASSESSMENT_SCHEMA = {
  type: 'object',
  properties: {
    shouldContinue: {
      type: 'boolean',
      description: 'Whether the debate should continue for another round',
    },
    qualityScore: {
      type: 'number',
      minimum: 0,
      maximum: 10,
      description: 'Overall quality of this round (0-10)',
    },
    assessments: {
      type: 'array',
      description: 'Individual assessments for each participant',
      items: {
        type: 'object',
        properties: {
          participant: {
            type: 'string',
            description: 'Participant name',
          },
          strengths: {
            type: 'array',
            items: { type: 'string' },
            description: 'Specific strengths in their argument',
          },
          weaknesses: {
            type: 'array',
            items: { type: 'string' },
            description: 'Specific weaknesses or areas for improvement',
          },
          score: {
            type: 'number',
            minimum: 0,
            maximum: 10,
            description: 'Score for this participant (0-10)',
          },
        },
        required: ['participant', 'strengths', 'weaknesses', 'score'],
      },
    },
    flags: {
      type: 'object',
      description: 'Detection flags for debate quality',
      properties: {
        repetitive: {
          type: 'boolean',
          description: 'Are participants repeating previous arguments?',
        },
        drifting: {
          type: 'boolean',
          description: 'Is the discussion drifting off-topic?',
        },
        diminishingReturns: {
          type: 'boolean',
          description: 'Are we seeing diminishing returns in quality?',
        },
        convergenceReached: {
          type: 'boolean',
          description: 'Have participants reached agreement or clarity?',
        },
      },
      required: ['repetitive', 'drifting', 'diminishingReturns', 'convergenceReached'],
    },
    reasoning: {
      type: 'string',
      description: 'Explanation of your assessment',
    },
    recommendations: {
      type: 'string',
      description: 'Recommended next steps for the debate',
    },
  },
  required: [
    'shouldContinue',
    'qualityScore',
    'assessments',
    'flags',
    'reasoning',
    'recommendations',
  ],
  additionalProperties: false,
} as const;

export interface JudgeAssessment {
  shouldContinue: boolean;
  qualityScore: number;
  assessments: Array<{
    participant: string;
    strengths: string[];
    weaknesses: string[];
    score: number;
  }>;
  flags: {
    repetitive: boolean;
    drifting: boolean;
    diminishingReturns: boolean;
    convergenceReached: boolean;
  };
  reasoning: string;
  recommendations: string;
}
```

### 2.3 Auto-Assignment Prompt Design

For auto-assigning optimal persona distribution:

```typescript
interface AutoAssignParams {
  topic: string;
  participantCount: number;
  desiredDiversity: 'binary' | 'spectrum' | 'multi-perspective';
}

export function buildAutoAssignPrompt(params: AutoAssignParams): string {
  const { topic, participantCount, desiredDiversity } = params;

  const diversityGuidance = {
    binary: 'two opposing positions (pro/con, for/against)',
    spectrum: 'positions distributed across a spectrum of viewpoints',
    'multi-perspective': 'diverse angles that may not be directly opposed',
  };

  return `You are an expert debate moderator tasked with assigning optimal positions for a multi-perspective debate.

TOPIC: "${topic}"

NUMBER OF PARTICIPANTS: ${participantCount}

DIVERSITY STRATEGY: ${diversityGuidance[desiredDiversity]}

═══════════════════════════════════════════════════════════════

YOUR TASK:

Generate ${participantCount} distinct positions/personas that will create a productive, engaging debate on this topic.

REQUIREMENTS:

1. PRODUCTIVE TENSION
   - Positions should create meaningful disagreement
   - Avoid positions that are too similar
   - Ensure real intellectual conflict

2. DIVERSE PERSPECTIVES
   - Don't just create binary opposition (pro vs con)
   - Consider different angles, frameworks, priorities
   - Think beyond obvious dichotomies

3. DEFENSIBLE POSITIONS
   - Each position should be intellectually credible
   - Avoid strawman positions
   - Ensure each stance can be argued substantively

4. BALANCED DIFFICULTY
   - Don't make some positions obviously weaker
   - Distribute argumentative advantage fairly

═══════════════════════════════════════════════════════════════

OUTPUT FORMAT (JSON):

{
  "positions": [
    {
      "position": "Clear statement of the position",
      "persona": "Brief persona description (profession, perspective, values)",
      "keyArguments": ["Argument 1", "Argument 2", "Argument 3"]
    }
  ],
  "reasoning": "Brief explanation of why these positions will create productive debate"
}

═══════════════════════════════════════════════════════════════

EXAMPLES:

Topic: "Universal Basic Income"
Bad (binary): "For UBI" vs "Against UBI"
Good (multi-perspective):
  - "UBI as solution to automation" (Technologist)
  - "UBI undermines work ethic" (Conservative economist)
  - "UBI insufficient without systemic change" (Democratic socialist)
  - "Conditional benefits better than UBI" (Pragmatic policy analyst)

Generate thoughtful, debate-worthy positions now.`;
}

export const AUTO_ASSIGN_SCHEMA = {
  type: 'object',
  properties: {
    positions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          position: { type: 'string' },
          persona: { type: 'string' },
          keyArguments: {
            type: 'array',
            items: { type: 'string' },
          },
        },
        required: ['position', 'persona', 'keyArguments'],
      },
    },
    reasoning: { type: 'string' },
  },
  required: ['positions', 'reasoning'],
} as const;
```

### 2.4 Prompt Engineering Best Practices

Based on [Databricks agent design patterns](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns) and [DeepLearning.AI multi-agent collaboration](https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-5-multi-agent-collaboration/):

**Key Principles:**

1. **Clear Role Definition**: Each prompt must clearly define the agent's role, constraints, and goals
2. **Context Awareness**: Agents must know about other participants and debate structure
3. **Structured Output**: Use JSON schemas for judge to ensure parseable results
4. **Minimal Instructions**: Avoid contradictory or distracting information
5. **Few-Shot Examples**: Consider adding examples for complex evaluation criteria
6. **Dynamic Injection**: Inject current debate state (round, history, other responses) into prompts

**Temperature Settings:**
- **Debaters**: 0.7-0.9 (creative, varied arguments)
- **Judge**: 0.0-0.3 (consistent, deterministic evaluation)
- **Auto-assign**: 0.8-1.0 (creative position generation)

---

## 3. Context Management Strategy

### 3.1 Challenge Overview

Long debates risk exceeding context windows, especially with:
- 2-4 participants × multiple rounds
- Full conversation history for each participant
- Context windows: 128K-200K tokens (most models)
- System prompts: 500-1000 tokens each
- Responses: 200-800 tokens each

**Example calculation** (4 participants, 10 rounds):
- System prompt: 4 × 800 = 3,200 tokens
- Responses: 4 × 10 × 400 = 16,000 tokens
- **Total**: ~19,200 tokens (acceptable)

But at 20 rounds: ~35,200 tokens (still ok)
At 50 rounds: ~83,200 tokens (approaching limits)

### 3.2 Context Management Strategies

Based on research into [context window management](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms) and [LLM context windows](https://www.kolena.com/guides/llm-context-windows-why-they-matter-and-5-solutions-for-context-limits/), three primary strategies:

#### Strategy 1: Truncation (Simplest)

**How it works:**
- Keep most recent N messages
- Discard oldest messages when limit approached
- Preserve system prompt always

**Pros:**
- Simple implementation
- No additional API calls
- Preserves exact wording

**Cons:**
- Loses early context
- May lose important setup/agreements
- Can create disjointed conversation

**Implementation:**

```typescript
class TruncationContextManager {
  constructor(
    private maxTokens: number,
    private tokenCounter: TokenCounter
  ) {}

  async buildContext(
    systemPrompt: string,
    messages: Message[],
    reserveTokens: number = 4096
  ): Promise<Message[]> {
    const availableTokens = this.maxTokens - reserveTokens;
    const systemTokens = await this.tokenCounter.count(systemPrompt);

    let remainingTokens = availableTokens - systemTokens;
    const contextMessages: Message[] = [];

    // Work backwards from most recent
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      const msgTokens = await this.tokenCounter.count(msg.content);

      if (remainingTokens - msgTokens < 0) {
        break; // Context full
      }

      contextMessages.unshift(msg);
      remainingTokens -= msgTokens;
    }

    return contextMessages;
  }
}
```

#### Strategy 2: Sliding Window (Balanced)

**How it works:**
- Keep first message (context/topic)
- Keep last N messages (recent discussion)
- Discard middle messages

**Pros:**
- Preserves debate topic/setup
- Maintains recent context
- No hallucination risk

**Cons:**
- Loses middle discussion
- Can create continuity gaps
- Participants may re-argue same points

**Implementation:**

```typescript
class SlidingWindowContextManager {
  constructor(
    private maxTokens: number,
    private tokenCounter: TokenCounter
  ) {}

  async buildContext(
    systemPrompt: string,
    messages: Message[],
    reserveTokens: number = 4096
  ): Promise<Message[]> {
    if (messages.length === 0) return [];

    const availableTokens = this.maxTokens - reserveTokens;
    const systemTokens = await this.tokenCounter.count(systemPrompt);

    // Always keep first message (topic/setup)
    const firstMsg = messages[0];
    const firstTokens = await this.tokenCounter.count(firstMsg.content);

    let remainingTokens = availableTokens - systemTokens - firstTokens;
    const recentMessages: Message[] = [];

    // Work backwards from most recent
    for (let i = messages.length - 1; i > 0; i--) {
      const msg = messages[i];
      const msgTokens = await this.tokenCounter.count(msg.content);

      if (remainingTokens - msgTokens < 0) {
        break;
      }

      recentMessages.unshift(msg);
      remainingTokens -= msgTokens;
    }

    return [firstMsg, ...recentMessages];
  }
}
```

#### Strategy 3: Summarization (Advanced)

**How it works:**
- Summarize older messages when threshold reached
- Keep recent messages verbatim
- Use separate LLM call for summarization

**Pros:**
- Preserves key points from entire debate
- Maintains continuity
- Can extend debates indefinitely

**Cons:**
- Additional API costs
- Slight hallucination risk
- Adds latency
- Complexity

**Implementation:**

```typescript
class SummarizationContextManager {
  constructor(
    private maxTokens: number,
    private tokenCounter: TokenCounter,
    private summaryProvider: LLMProvider
  ) {}

  async buildContext(
    systemPrompt: string,
    messages: Message[],
    reserveTokens: number = 4096
  ): Promise<{ messages: Message[]; hadSummarization: boolean }> {
    const availableTokens = this.maxTokens - reserveTokens;
    const systemTokens = await this.tokenCounter.count(systemPrompt);

    // Count all tokens
    let totalTokens = systemTokens;
    for (const msg of messages) {
      totalTokens += await this.tokenCounter.count(msg.content);
    }

    // Check if summarization needed (80% threshold)
    const threshold = availableTokens * 0.8;
    if (totalTokens <= threshold) {
      return { messages, hadSummarization: false };
    }

    // Determine split point: summarize older 50%, keep recent 50%
    const splitIndex = Math.floor(messages.length * 0.5);
    const toSummarize = messages.slice(0, splitIndex);
    const toKeep = messages.slice(splitIndex);

    // Generate summary
    const summary = await this.summarizeMessages(toSummarize);
    const summaryMsg: Message = {
      role: 'system',
      content: `[PREVIOUS DEBATE SUMMARY]\n\n${summary}`,
      metadata: { summarized: true },
    };

    return {
      messages: [summaryMsg, ...toKeep],
      hadSummarization: true,
    };
  }

  private async summarizeMessages(messages: Message[]): Promise<string> {
    const transcript = messages
      .map((m) => `${m.metadata?.participant || m.role}: ${m.content}`)
      .join('\n\n---\n\n');

    const summaryPrompt = `Summarize the following debate discussion concisely, preserving:
- Key arguments from each participant
- Main points of agreement/disagreement
- Important evidence or examples cited
- Overall progression of discussion

Be brief but comprehensive. Focus on substance, not style.

DISCUSSION TO SUMMARIZE:

${transcript}

SUMMARY:`;

    const response = await this.summaryProvider.complete({
      messages: [{ role: 'user', content: summaryPrompt }],
      maxTokens: Math.floor(this.maxTokens * 0.2), // Summary takes max 20%
      temperature: 0.3, // More deterministic
    });

    return response.content;
  }
}
```

### 3.3 Recommended Strategy for Quorum

**Hybrid Approach:**

1. **Default**: Sliding Window (simple, no API costs)
2. **User Option**: Enable summarization for long debates
3. **Warning System**: Alert when approaching 80% context capacity
4. **Emergency**: Auto-summarize if hitting 90% without user intervention

```typescript
class HybridContextManager {
  private slidingWindow: SlidingWindowContextManager;
  private summarization: SummarizationContextManager;

  constructor(
    private maxTokens: number,
    private tokenCounter: TokenCounter,
    private summaryProvider?: LLMProvider,
    private userPreferences?: { enableAutoSummary: boolean }
  ) {
    this.slidingWindow = new SlidingWindowContextManager(maxTokens, tokenCounter);
    if (summaryProvider) {
      this.summarization = new SummarizationContextManager(
        maxTokens,
        tokenCounter,
        summaryProvider
      );
    }
  }

  async buildContext(
    systemPrompt: string,
    messages: Message[],
    reserveTokens: number = 4096
  ): Promise<{ messages: Message[]; warning?: string }> {
    const availableTokens = this.maxTokens - reserveTokens;
    const systemTokens = await this.tokenCounter.count(systemPrompt);

    // Calculate current usage
    let totalTokens = systemTokens;
    for (const msg of messages) {
      totalTokens += await this.tokenCounter.count(msg.content);
    }

    const usage = totalTokens / availableTokens;

    // 1. Under 80%: Use all messages
    if (usage <= 0.8) {
      return { messages };
    }

    // 2. 80-90%: Warning + sliding window or summarization
    if (usage <= 0.9) {
      const warning = `Approaching context limit (${Math.round(usage * 100)}% used). ${
        this.userPreferences?.enableAutoSummary
          ? 'Summarizing older messages.'
          : 'Using sliding window. Enable summarization for better continuity.'
      }`;

      if (this.summarization && this.userPreferences?.enableAutoSummary) {
        const result = await this.summarization.buildContext(
          systemPrompt,
          messages,
          reserveTokens
        );
        return { messages: result.messages, warning };
      }

      const slidingMessages = await this.slidingWindow.buildContext(
        systemPrompt,
        messages,
        reserveTokens
      );
      return { messages: slidingMessages, warning };
    }

    // 3. Over 90%: Force summarization if available, else truncate aggressively
    if (this.summarization) {
      const result = await this.summarization.buildContext(
        systemPrompt,
        messages,
        reserveTokens
      );
      return {
        messages: result.messages,
        warning: 'Context limit exceeded. Automatically summarized older messages.',
      };
    }

    // Fallback: aggressive truncation
    const truncated = await this.slidingWindow.buildContext(
      systemPrompt,
      messages,
      reserveTokens
    );
    return {
      messages: truncated,
      warning: 'Context limit exceeded. Truncated older messages. Consider enabling summarization.',
    };
  }
}
```

### 3.4 Per-Participant vs Shared Context

**Question**: Should each participant see:
- A) All messages from all participants (shared context)
- B) Only their own messages + selected others (per-participant context)

**Recommendation**: **Shared Context** (Option A)

**Reasoning:**
- Enables direct cross-referencing ("As GPT-4 mentioned...")
- Creates true multi-party debate
- Simpler implementation
- Matches user expectations for debate format

**Implementation:**

```typescript
function buildParticipantContext(
  debate: DebateState,
  participantId: string
): Message[] {
  const allResponses = getAllResponsesChronological(debate);

  return allResponses.map((response) => {
    const participant = debate.participants[response.participantId];
    const isOwnMessage = response.participantId === participantId;

    return {
      role: isOwnMessage ? 'assistant' : 'user',
      content: isOwnMessage
        ? response.content
        : `${participant.config.displayName}: ${response.content}`,
      metadata: {
        participant: participant.config.displayName,
        round: response.roundNumber,
        timestamp: response.timestamp,
      },
    };
  });
}

function getAllResponsesChronological(debate: DebateState): Response[] {
  const allResponses: Response[] = [];

  Object.values(debate.participants).forEach((p) => {
    allResponses.push(...p.responseHistory);
  });

  return allResponses.sort((a, b) => a.timestamp - b.timestamp);
}
```

---

## 4. Judge Agent Design

### 4.1 Evaluation Rubric

Based on [LLM-as-judge best practices](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) and [Hugging Face evaluation guide](https://huggingface.co/learn/cookbook/en/llm_judge), the judge rubric should include:

**Core Evaluation Dimensions:**

| Criterion | Weight | Description | Scoring (0-10) |
|-----------|--------|-------------|----------------|
| **Logical Consistency** | 20% | Arguments follow logically, no contradictions | 0=contradictory, 10=perfectly consistent |
| **Evidence Quality** | 20% | Use of data, examples, research to support claims | 0=no evidence, 10=strong evidence throughout |
| **Engagement** | 20% | Directly addresses opponent arguments by name/point | 0=ignores others, 10=deeply engages |
| **Novelty** | 15% | New insights vs repetition of previous points | 0=pure repetition, 10=all new insights |
| **Persuasiveness** | 15% | Clarity, rhetoric, compelling delivery | 0=unclear/weak, 10=highly persuasive |
| **Relevance** | 10% | Stays on topic, addresses the debate question | 0=off-topic, 10=directly relevant |

**Stopping Criteria Detection:**

The judge must detect when to end the debate:

```typescript
interface StoppingCriteria {
  // Repetition: Arguments are being repeated
  repetitive: boolean;
  repetitionThreshold: number; // % of content that's repetitive

  // Drift: Discussion wandering off-topic
  drifting: boolean;
  relevanceScore: number; // 0-10, below 5 = drifting

  // Diminishing Returns: Quality declining or plateauing
  diminishingReturns: boolean;
  qualityTrend: 'improving' | 'stable' | 'declining';

  // Convergence: Agreement reached or positions clarified
  convergenceReached: boolean;
  agreementAreas: string[];
}
```

### 4.2 Repetition Detection Algorithm

From research on [AI repetition detection](https://medium.com/@JacksonAAaron/verbalized-sampling-the-ai-strategy-solving-repetition-bias-and-boring-chatbots-82ba5a8a8198):

**Approach 1: Semantic Similarity (Embedding-based)**

```typescript
import { cosineSimilarity, generateEmbedding } from './embeddings';

class RepetitionDetector {
  private responseEmbeddings: Map<string, number[]> = new Map();

  async detectRepetition(
    newResponse: string,
    previousResponses: string[],
    threshold: number = 0.85
  ): Promise<{ isRepetitive: boolean; similarity: number }> {
    const newEmbedding = await generateEmbedding(newResponse);

    let maxSimilarity = 0;

    for (const prevResponse of previousResponses) {
      // Check cache first
      let prevEmbedding = this.responseEmbeddings.get(prevResponse);

      if (!prevEmbedding) {
        prevEmbedding = await generateEmbedding(prevResponse);
        this.responseEmbeddings.set(prevResponse, prevEmbedding);
      }

      const similarity = cosineSimilarity(newEmbedding, prevEmbedding);
      maxSimilarity = Math.max(maxSimilarity, similarity);

      if (similarity >= threshold) {
        return { isRepetitive: true, similarity };
      }
    }

    return { isRepetitive: false, similarity: maxSimilarity };
  }

  // Alternative: N-gram overlap
  calculateNGramOverlap(
    text1: string,
    text2: string,
    n: number = 3
  ): number {
    const ngrams1 = this.extractNGrams(text1, n);
    const ngrams2 = this.extractNGrams(text2, n);

    const intersection = ngrams1.filter((ng) => ngrams2.includes(ng));
    const union = [...new Set([...ngrams1, ...ngrams2])];

    return intersection.length / union.length;
  }

  private extractNGrams(text: string, n: number): string[] {
    const words = text.toLowerCase().split(/\s+/);
    const ngrams: string[] = [];

    for (let i = 0; i <= words.length - n; i++) {
      ngrams.push(words.slice(i, i + n).join(' '));
    }

    return ngrams;
  }
}
```

**Approach 2: LLM-Based Detection (More Nuanced)**

Include in judge prompt:

```typescript
const repetitionDetectionPrompt = `
REPETITION DETECTION:

For each participant, determine if their current response contains:
- Substantially new arguments (novelty score 8-10)
- Some new points mixed with previous ones (novelty score 4-7)
- Mostly repetition with minor variation (novelty score 1-3)
- Pure repetition of prior arguments (novelty score 0)

Consider semantic similarity, not just word-for-word repetition.
`;
```

### 4.3 Diminishing Returns Detection

Based on research on [diminishing returns in LLMs](https://arxiv.org/html/2509.09677v1):

**Indicators:**
1. Quality scores trending downward over rounds
2. Novelty scores decreasing
3. Engagement scores dropping
4. Response lengths shortening (participants running out of material)

```typescript
class DiminishingReturnsDetector {
  detectDiminishingReturns(
    assessmentHistory: RoundAssessment[]
  ): boolean {
    if (assessmentHistory.length < 3) return false; // Need at least 3 rounds

    // Check quality trend
    const recentQuality = assessmentHistory.slice(-3).map(a => a.quality);
    const isDecining = this.isDecreasingTrend(recentQuality);

    // Check novelty trend
    const recentNovelty = assessmentHistory.slice(-3).map(a => a.quality.novelty);
    const noveltyDecreasing = this.isDecreasingTrend(recentNovelty);

    // Check repetition flags
    const recentRepetition = assessmentHistory.slice(-2).every(a => a.flags.repetitive);

    return (isDecining && noveltyDecreasing) || recentRepetition;
  }

  private isDecreasingTrend(values: number[]): boolean {
    if (values.length < 2) return false;

    let decreaseCount = 0;
    for (let i = 1; i < values.length; i++) {
      if (values[i] < values[i - 1]) decreaseCount++;
    }

    return decreaseCount >= values.length - 1; // All or most decreasing
  }
}
```

### 4.4 Final Verdict Schema

```typescript
export const FINAL_VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    summary: {
      type: 'string',
      description: 'Comprehensive summary of the entire debate',
    },
    keyPoints: {
      type: 'array',
      description: 'Key arguments from each participant',
      items: {
        type: 'object',
        properties: {
          participant: { type: 'string' },
          mainArguments: {
            type: 'array',
            items: { type: 'string' },
          },
        },
        required: ['participant', 'mainArguments'],
      },
    },
    areasOfAgreement: {
      type: 'array',
      items: { type: 'string' },
      description: 'Points where participants agreed or found common ground',
    },
    areasOfDisagreement: {
      type: 'array',
      items: { type: 'string' },
      description: 'Irreconcilable differences or persistent disagreements',
    },
    winner: {
      type: 'object',
      nullable: true,
      description: 'Winner determination (if applicable)',
      properties: {
        participant: { type: 'string' },
        reasoning: { type: 'string' },
      },
    },
    qualityScore: {
      type: 'number',
      minimum: 0,
      maximum: 100,
      description: 'Overall debate quality (0-100)',
    },
    insights: {
      type: 'array',
      items: { type: 'string' },
      description: 'Novel insights or surprising points emerged from debate',
    },
  },
  required: [
    'summary',
    'keyPoints',
    'areasOfAgreement',
    'areasOfDisagreement',
    'qualityScore',
    'insights',
  ],
} as const;
```

---

## 5. Testing Strategy

### 5.1 Testing Pyramid for Quorum

Based on [LLM testing strategies](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies) and [multi-agent evaluation](https://orq.ai/blog/multi-agent-llm-eval-system):

```
                  ┌─────────────────┐
                  │  E2E Tests      │  ← Real API calls, expensive
                  │  (5-10 tests)   │
                  └─────────────────┘
                         ▲
                         │
                  ┌─────────────────┐
                  │ Integration     │  ← Mocked providers
                  │ Tests           │
                  │ (30-50 tests)   │
                  └─────────────────┘
                         ▲
                         │
          ┌────────────────────────────┐
          │   Unit Tests               │  ← State machine, prompts
          │   (100+ tests)             │
          └────────────────────────────┘
```

### 5.2 Unit Tests: State Machine

Test each state transition in isolation.

```typescript
// __tests__/debateMachine.test.ts
import { interpret } from 'xstate';
import { debateMachine } from '../machines/debateMachine';

describe('Debate State Machine', () => {
  describe('CONFIGURING → VALIDATING → READY', () => {
    it('should transition to ready when config is valid', (done) => {
      const service = interpret(debateMachine)
        .onTransition((state) => {
          if (state.matches('ready')) {
            expect(state.context.errors).toHaveLength(0);
            done();
          }
        })
        .start();

      service.send({
        type: 'SET_CONFIG',
        config: {
          topic: 'Test topic',
          format: 'free-form',
          mode: 'sequential',
          participants: [
            { id: 'p1', providerId: 'anthropic', modelId: 'claude-3' },
            { id: 'p2', providerId: 'openai', modelId: 'gpt-4' },
          ],
          judgeConfig: { providerId: 'anthropic', modelId: 'claude-3' },
        },
      });

      service.send('VALIDATE');
    });

    it('should return to configuring with errors when config is invalid', (done) => {
      const service = interpret(debateMachine)
        .onTransition((state) => {
          if (state.matches('configuring') && state.context.errors.length > 0) {
            expect(state.context.errors).toContainEqual(
              expect.objectContaining({ message: expect.stringContaining('topic') })
            );
            done();
          }
        })
        .start();

      service.send({
        type: 'SET_CONFIG',
        config: {
          topic: '', // Invalid: empty topic
          format: 'free-form',
          mode: 'sequential',
          participants: [],
        },
      });

      service.send('VALIDATE');
    });
  });

  describe('READY → INITIALIZING → RUNNING', () => {
    it('should not start without valid config', () => {
      const service = interpret(debateMachine).start();

      service.send('START');

      expect(service.state.matches('ready')).toBe(false);
      expect(service.state.matches('initializing')).toBe(false);
    });

    it('should initialize participants and start round 1', (done) => {
      const service = interpret(
        debateMachine.withContext({
          config: validConfig,
          currentRound: 0,
          participants: {},
          judge: null,
          errors: [],
        })
      )
        .onTransition((state) => {
          if (state.matches('running')) {
            expect(state.context.currentRound).toBe(1);
            expect(Object.keys(state.context.participants)).toHaveLength(2);
            expect(state.context.judge).toBeDefined();
            done();
          }
        })
        .start();

      service.send('START');
    });
  });

  describe('RUNNING.AWAITING_RESPONSES → JUDGING → ROUND_COMPLETE', () => {
    it('should transition to judging after all responses complete', (done) => {
      const service = interpret(runningStateMachine)
        .onTransition((state) => {
          if (state.matches({ running: 'judging' })) {
            done();
          }
        })
        .start();

      // Simulate response completion
      service.send({ type: 'RESPONSE_COMPLETE', participantId: 'p1' });
      service.send({ type: 'RESPONSE_COMPLETE', participantId: 'p2' });
    });

    it('should end debate when judge returns shouldContinue=false', (done) => {
      const service = interpret(runningStateMachine)
        .onTransition((state) => {
          if (state.matches('completing')) {
            done();
          }
        })
        .start();

      service.send({
        type: 'JUDGE_ASSESSMENT',
        assessment: {
          shouldContinue: false,
          qualityScore: 8,
          assessments: [],
          flags: { diminishingReturns: true },
        },
      });
    });

    it('should increment round and continue when judge returns shouldContinue=true', (done) => {
      const service = interpret(runningStateMachine)
        .onTransition((state) => {
          if (
            state.matches({ running: 'awaitingResponses' }) &&
            state.context.currentRound === 2
          ) {
            done();
          }
        })
        .start();

      service.send({
        type: 'JUDGE_ASSESSMENT',
        assessment: {
          shouldContinue: true,
          qualityScore: 7,
          assessments: [],
          flags: { repetitive: false },
        },
      });
    });
  });

  describe('Round-limited format', () => {
    it('should end debate at round limit', (done) => {
      const service = interpret(
        debateMachine.withContext({
          config: { ...validConfig, format: 'round-limited', roundLimit: 3 },
          currentRound: 3,
          participants: {},
          judge: null,
        })
      )
        .onTransition((state) => {
          if (state.matches('completing')) {
            done();
          }
        })
        .start();

      service.send({
        type: 'JUDGE_ASSESSMENT',
        assessment: { shouldContinue: true }, // Ignored due to round limit
      });
    });
  });

  describe('Error handling', () => {
    it('should transition to error state on initialization failure', (done) => {
      const service = interpret(debateMachine)
        .onTransition((state) => {
          if (state.matches('error')) {
            expect(state.context.errors.length).toBeGreaterThan(0);
            done();
          }
        })
        .start();

      // Trigger initialization with invalid providers
      service.send('START');
    });

    it('should allow retry from error state', () => {
      const service = interpret(errorStateMachine).start();

      service.send('RETRY');

      expect(service.state.matches('ready')).toBe(true);
      expect(service.state.context.errors).toHaveLength(0);
    });
  });
});
```

### 5.3 Unit Tests: Prompt Generation

```typescript
// __tests__/promptBuilder.test.ts
import { buildDebaterSystemPrompt, buildJudgeSystemPrompt } from '../prompts';

describe('Prompt Builder', () => {
  describe('Debater System Prompt', () => {
    it('should include all required elements', () => {
      const prompt = buildDebaterSystemPrompt({
        topic: 'AI Safety',
        participantName: 'Claude',
        position: 'Pro safety research',
        persona: 'AI safety researcher',
        otherParticipants: [{ name: 'GPT', position: 'Pro capabilities' }],
        format: 'free-form',
        currentRound: 1,
      });

      expect(prompt).toContain('AI Safety');
      expect(prompt).toContain('Claude');
      expect(prompt).toContain('Pro safety research');
      expect(prompt).toContain('AI safety researcher');
      expect(prompt).toContain('GPT');
      expect(prompt).toContain('Pro capabilities');
      expect(prompt).toContain('ROUND: 1');
    });

    it('should include format-specific instructions', () => {
      const structuredPrompt = buildDebaterSystemPrompt({
        topic: 'Test',
        participantName: 'Test',
        position: 'Test',
        persona: 'Test',
        otherParticipants: [],
        format: 'structured-rounds',
        currentRound: 1,
        maxRounds: 5,
      });

      expect(structuredPrompt).toContain('OPENING');
      expect(structuredPrompt).toContain('REBUTTALS');
      expect(structuredPrompt).toContain('CLOSING');
    });

    it('should handle convergence-seeking format', () => {
      const prompt = buildDebaterSystemPrompt({
        topic: 'Test',
        participantName: 'Test',
        position: 'Test',
        persona: 'Test',
        otherParticipants: [],
        format: 'convergence-seeking',
        currentRound: 1,
      });

      expect(prompt).toContain('convergence');
      expect(prompt).toContain('common ground');
    });
  });

  describe('Judge System Prompt', () => {
    it('should include structured output instructions', () => {
      const prompt = buildJudgeSystemPrompt({
        topic: 'Test topic',
        participants: [
          { name: 'Claude', position: 'Pro' },
          { name: 'GPT', position: 'Con' },
        ],
        format: 'free-form',
        currentRound: 1,
      });

      expect(prompt).toContain('JSON');
      expect(prompt).toContain('shouldContinue');
      expect(prompt).toContain('qualityScore');
      expect(prompt).toContain('assessments');
      expect(prompt).toContain('flags');
    });

    it('should list all participants', () => {
      const prompt = buildJudgeSystemPrompt({
        topic: 'Test',
        participants: [
          { name: 'Alice', position: 'A' },
          { name: 'Bob', position: 'B' },
          { name: 'Carol', position: 'C' },
        ],
        format: 'free-form',
        currentRound: 1,
      });

      expect(prompt).toContain('Alice');
      expect(prompt).toContain('Bob');
      expect(prompt).toContain('Carol');
    });
  });
});
```

### 5.4 Integration Tests: Mocked LLM Providers

Based on [mocking LLM responses](https://home.mlops.community/public/blogs/effective-practices-for-mocking-llm-responses-during-the-software-development-lifecycle):

```typescript
// __tests__/integration/debateFlow.test.ts
import { DebateOrchestrator } from '../services/debateOrchestrator';
import { MockProvider } from '../test-utils/mockProvider';

describe('Debate Flow Integration', () => {
  let mockClaude: MockProvider;
  let mockGPT: MockProvider;
  let mockJudge: MockProvider;
  let orchestrator: DebateOrchestrator;

  beforeEach(() => {
    mockClaude = new MockProvider('anthropic', {
      responses: [
        'Opening argument for position A...',
        'Rebuttal addressing position B...',
        'Closing statement reinforcing A...',
      ],
    });

    mockGPT = new MockProvider('openai', {
      responses: [
        'Opening argument for position B...',
        'Counterargument to position A...',
        'Final defense of position B...',
      ],
    });

    mockJudge = new MockProvider('anthropic', {
      structuredResponses: [
        {
          shouldContinue: true,
          qualityScore: 8,
          assessments: [
            { participant: 'Claude', score: 8, strengths: ['Clear'], weaknesses: [] },
            { participant: 'GPT', score: 8, strengths: ['Logical'], weaknesses: [] },
          ],
          flags: { repetitive: false, drifting: false, diminishingReturns: false },
        },
        {
          shouldContinue: true,
          qualityScore: 7,
          assessments: [/* ... */],
          flags: { repetitive: false, drifting: false, diminishingReturns: false },
        },
        {
          shouldContinue: false,
          qualityScore: 7,
          assessments: [/* ... */],
          flags: { repetitive: true, drifting: false, diminishingReturns: true },
        },
      ],
    });

    orchestrator = new DebateOrchestrator({
      providers: {
        'claude': mockClaude,
        'gpt': mockGPT,
        'judge': mockJudge,
      },
    });
  });

  it('should execute complete 3-round debate', async () => {
    const debate = await orchestrator.createDebate({
      topic: 'Test topic',
      format: 'structured-rounds',
      mode: 'sequential',
      participants: [
        { id: 'claude', name: 'Claude', position: 'A', persona: 'Researcher' },
        { id: 'gpt', name: 'GPT', position: 'B', persona: 'Analyst' },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.startDebate(debate.id);

    // Wait for completion
    await orchestrator.waitForCompletion(debate.id);

    const finalState = orchestrator.getDebate(debate.id);

    expect(finalState.status).toBe('completed');
    expect(finalState.currentRound).toBe(3);
    expect(finalState.participants['claude'].responseHistory).toHaveLength(3);
    expect(finalState.participants['gpt'].responseHistory).toHaveLength(3);
    expect(finalState.judge.assessments).toHaveLength(3);
    expect(finalState.judge.finalVerdict).toBeDefined();
  });

  it('should handle simultaneous mode correctly', async () => {
    const debate = await orchestrator.createDebate({
      topic: 'Test',
      format: 'free-form',
      mode: 'simultaneous', // Key difference
      participants: [
        { id: 'claude', name: 'Claude', position: 'A' },
        { id: 'gpt', name: 'GPT', position: 'B' },
      ],
      judgeConfig: { id: 'judge' },
    });

    const startTime = Date.now();
    await orchestrator.executeRound(debate.id);
    const duration = Date.now() - startTime;

    // Both responses should start near-simultaneously
    const claudeResponse = debate.participants['claude'].responseHistory[0];
    const gptResponse = debate.participants['gpt'].responseHistory[0];

    expect(Math.abs(claudeResponse.timestamp - gptResponse.timestamp)).toBeLessThan(1000);
  });

  it('should stop debate when judge detects diminishing returns', async () => {
    mockJudge.setStructuredResponses([
      { shouldContinue: true, flags: { diminishingReturns: false } },
      { shouldContinue: true, flags: { diminishingReturns: false } },
      { shouldContinue: false, flags: { diminishingReturns: true } }, // Stop here
    ]);

    const debate = await orchestrator.createDebate({
      topic: 'Test',
      format: 'free-form',
      mode: 'sequential',
      participants: [
        { id: 'claude', name: 'Claude', position: 'A' },
        { id: 'gpt', name: 'GPT', position: 'B' },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.startDebate(debate.id);
    await orchestrator.waitForCompletion(debate.id);

    expect(debate.status).toBe('completed');
    expect(debate.currentRound).toBe(3); // Stopped at round 3
    expect(debate.judge.assessments[2].flags.diminishingReturns).toBe(true);
  });
});
```

### 5.5 Integration Tests: Error Scenarios

```typescript
describe('Error Handling Integration', () => {
  it('should handle provider API failure gracefully', async () => {
    const failingProvider = new MockProvider('openai', {
      shouldFail: true,
      error: { type: 'api_error', message: 'API unavailable', retryable: true },
    });

    const orchestrator = new DebateOrchestrator({
      providers: {
        'claude': mockClaude,
        'gpt': failingProvider,
        'judge': mockJudge,
      },
    });

    const debate = await orchestrator.createDebate({
      topic: 'Test',
      format: 'free-form',
      mode: 'sequential',
      participants: [
        { id: 'claude', name: 'Claude', position: 'A' },
        { id: 'gpt', name: 'GPT', position: 'B' },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.startDebate(debate.id);
    await orchestrator.waitForCompletion(debate.id);

    expect(debate.status).toBe('error');
    expect(debate.participants['gpt'].status).toBe('error');
    expect(debate.participants['gpt'].errors.length).toBeGreaterThan(0);
  });

  it('should retry on rate limit error', async () => {
    const rateLimitedProvider = new MockProvider('openai', {
      failOnce: true,
      error: { type: 'rate_limit', retryable: true, retryAfter: 1 },
    });

    const orchestrator = new DebateOrchestrator({
      providers: {
        'claude': mockClaude,
        'gpt': rateLimitedProvider,
        'judge': mockJudge,
      },
    });

    const debate = await orchestrator.createDebate({
      topic: 'Test',
      format: 'free-form',
      mode: 'sequential',
      participants: [
        { id: 'claude', name: 'Claude', position: 'A' },
        { id: 'gpt', name: 'GPT', position: 'B' },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.startDebate(debate.id);
    await orchestrator.waitForCompletion(debate.id);

    expect(debate.status).toBe('completed'); // Should succeed after retry
    expect(debate.participants['gpt'].retryCount).toBeGreaterThan(0);
  });

  it('should detect and handle context overflow', async () => {
    // Simulate very long responses that exceed context window
    const verboseProvider = new MockProvider('openai', {
      responses: Array(50).fill('Very long response...'.repeat(100)),
    });

    const orchestrator = new DebateOrchestrator({
      providers: {
        'claude': verboseProvider,
        'gpt': verboseProvider,
        'judge': mockJudge,
      },
      contextManager: new HybridContextManager(128000, tokenCounter),
    });

    const debate = await orchestrator.createDebate({
      topic: 'Test',
      format: 'free-form',
      mode: 'sequential',
      participants: [
        { id: 'claude', name: 'Claude', position: 'A' },
        { id: 'gpt', name: 'GPT', position: 'B' },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.startDebate(debate.id);
    await orchestrator.waitForCompletion(debate.id);

    // Should either complete with summarization or stop gracefully
    expect(['completed', 'error']).toContain(debate.status);

    if (debate.status === 'completed') {
      // Check that context management was triggered
      expect(debate.metadata.contextWarnings).toBeDefined();
    }
  });
});
```

### 5.6 End-to-End Tests (Real API Calls)

```typescript
describe('E2E: Real API Integration', () => {
  // Only run if API keys are available
  const skipE2E = !process.env.ANTHROPIC_API_KEY || !process.env.OPENAI_API_KEY;

  (skipE2E ? it.skip : it)('should complete real 2-round debate', async () => {
    const orchestrator = new DebateOrchestrator({
      providers: {
        'claude': new AnthropicProvider({
          type: 'anthropic',
          apiKey: process.env.ANTHROPIC_API_KEY!,
          model: 'claude-sonnet-4-5-20250929',
        }),
        'gpt': new OpenAIProvider({
          type: 'openai',
          apiKey: process.env.OPENAI_API_KEY!,
          model: 'gpt-4o',
        }),
        'judge': new AnthropicProvider({
          type: 'anthropic',
          apiKey: process.env.ANTHROPIC_API_KEY!,
          model: 'claude-sonnet-4-5-20250929',
        }),
      },
    });

    const debate = await orchestrator.createDebate({
      topic: 'Is remote work better than office work for productivity?',
      format: 'round-limited',
      mode: 'sequential',
      roundLimit: 2, // Keep it short for testing
      participants: [
        {
          id: 'claude',
          name: 'Claude',
          position: 'Remote work is more productive',
          persona: 'Remote work advocate',
        },
        {
          id: 'gpt',
          name: 'GPT',
          position: 'Office work is more productive',
          persona: 'Traditional workplace proponent',
        },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.startDebate(debate.id);
    await orchestrator.waitForCompletion(debate.id, { timeout: 120000 }); // 2 min timeout

    expect(debate.status).toBe('completed');
    expect(debate.currentRound).toBe(2);
    expect(debate.judge.finalVerdict).toBeDefined();

    // Validate response quality
    for (const participant of Object.values(debate.participants)) {
      for (const response of participant.responseHistory) {
        expect(response.content.length).toBeGreaterThan(100); // Non-trivial responses
        expect(response.tokenCount).toBeGreaterThan(0);
      }
    }

    // Validate judge assessments
    expect(debate.judge.assessments).toHaveLength(2);
    for (const assessment of debate.judge.assessments) {
      expect(assessment.qualityScore).toBeGreaterThanOrEqual(0);
      expect(assessment.qualityScore).toBeLessThanOrEqual(10);
      expect(assessment.assessments.length).toBe(2); // Both participants assessed
    }

    // Log for manual inspection
    console.log('=== E2E Test Results ===');
    console.log('Total cost:', debate.totalCost);
    console.log('Final verdict:', debate.judge.finalVerdict.summary);
  }, 180000); // 3 min test timeout
});
```

### 5.7 Prompt Effectiveness Testing

```typescript
describe('Prompt Effectiveness', () => {
  it('should generate cross-referencing responses', async () => {
    const orchestrator = new DebateOrchestrator({
      providers: { 'claude': mockClaude, 'gpt': mockGPT, 'judge': mockJudge },
    });

    const debate = await orchestrator.createDebate({
      topic: 'Test cross-referencing',
      format: 'free-form',
      mode: 'sequential',
      participants: [
        { id: 'claude', name: 'Claude', position: 'A' },
        { id: 'gpt', name: 'GPT', position: 'B' },
      ],
      judgeConfig: { id: 'judge' },
    });

    await orchestrator.executeRound(debate.id); // Round 1
    await orchestrator.executeRound(debate.id); // Round 2

    // Check that Round 2 responses reference Round 1
    const claudeRound2 = debate.participants['claude'].responseHistory[1];
    const gptRound2 = debate.participants['gpt'].responseHistory[1];

    // Should mention other participant by name
    const mentionsOpponent =
      claudeRound2.content.toLowerCase().includes('gpt') ||
      gptRound2.content.toLowerCase().includes('claude');

    expect(mentionsOpponent).toBe(true);
  });

  it('should produce valid JSON from judge', async () => {
    const realJudgeProvider = new AnthropicProvider({
      type: 'anthropic',
      apiKey: process.env.ANTHROPIC_API_KEY!,
      model: 'claude-sonnet-4-5-20250929',
    });

    const assessment = await realJudgeProvider.structuredComplete({
      messages: [
        {
          role: 'system',
          content: buildJudgeSystemPrompt({
            topic: 'Test',
            participants: [
              { name: 'A', position: 'Pro' },
              { name: 'B', position: 'Con' },
            ],
            format: 'free-form',
            currentRound: 1,
          }),
        },
        {
          role: 'user',
          content: 'A: Test argument.\n\nB: Counter argument.',
        },
      ],
      schema: JUDGE_ASSESSMENT_SCHEMA,
      maxTokens: 2000,
    });

    // Validate schema compliance
    expect(assessment.structuredData).toHaveProperty('shouldContinue');
    expect(assessment.structuredData).toHaveProperty('qualityScore');
    expect(assessment.structuredData).toHaveProperty('assessments');
    expect(assessment.structuredData.assessments).toHaveLength(2);
    expect(assessment.validationErrors).toBeUndefined();
  });
});
```

### 5.8 Test Coverage Targets

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| State Machine | 95%+ | Critical |
| Prompt Builders | 90%+ | High |
| Context Manager | 85%+ | High |
| Provider Abstraction | 80%+ | Medium |
| Error Handlers | 90%+ | High |
| Judge Logic | 85%+ | High |

---

## 6. Error Handling & Recovery

### 6.1 Error Classification

Based on existing API integration spec and research:

```typescript
export enum ErrorType {
  // Retryable errors
  NETWORK = 'network',
  RATE_LIMIT = 'rate_limit',
  API_ERROR = 'api_error',
  TIMEOUT = 'timeout',

  // Non-retryable errors
  CONTEXT_OVERFLOW = 'context_overflow',
  AUTHENTICATION = 'authentication',
  VALIDATION = 'validation',
  INVALID_RESPONSE = 'invalid_response',
}

export interface DebateError {
  type: ErrorType;
  message: string;
  participantId?: string;
  round?: number;
  retryable: boolean;
  retryCount: number;
  timestamp: number;
  originalError?: unknown;
}
```

### 6.2 Recovery Strategies

```typescript
class ErrorRecoveryManager {
  private maxRetries: Record<ErrorType, number> = {
    [ErrorType.NETWORK]: 3,
    [ErrorType.RATE_LIMIT]: 5,
    [ErrorType.API_ERROR]: 2,
    [ErrorType.TIMEOUT]: 2,
    [ErrorType.CONTEXT_OVERFLOW]: 0,
    [ErrorType.AUTHENTICATION]: 0,
    [ErrorType.VALIDATION]: 0,
    [ErrorType.INVALID_RESPONSE]: 1,
  };

  async handleError(
    error: DebateError,
    context: DebateContext
  ): Promise<RecoveryAction> {
    // 1. Check if retryable
    if (!error.retryable || error.retryCount >= this.maxRetries[error.type]) {
      return this.createFailureAction(error, context);
    }

    // 2. Apply recovery strategy
    switch (error.type) {
      case ErrorType.RATE_LIMIT:
        return this.handleRateLimit(error, context);

      case ErrorType.CONTEXT_OVERFLOW:
        return this.handleContextOverflow(error, context);

      case ErrorType.NETWORK:
      case ErrorType.API_ERROR:
      case ErrorType.TIMEOUT:
        return this.handleRetryableError(error, context);

      case ErrorType.AUTHENTICATION:
        return this.handleAuthError(error, context);

      case ErrorType.INVALID_RESPONSE:
        return this.handleInvalidResponse(error, context);

      default:
        return this.createFailureAction(error, context);
    }
  }

  private handleRateLimit(
    error: DebateError,
    context: DebateContext
  ): RecoveryAction {
    const retryAfter = error.metadata?.retryAfter || 60; // seconds

    return {
      type: 'RETRY',
      delay: retryAfter * 1000,
      message: `Rate limit hit. Retrying in ${retryAfter} seconds...`,
      modifiedContext: context,
    };
  }

  private handleContextOverflow(
    error: DebateError,
    context: DebateContext
  ): RecoveryAction {
    // Offer user options
    return {
      type: 'USER_CHOICE',
      message: 'Context window exceeded. Choose recovery option:',
      options: [
        {
          label: 'Summarize and continue',
          action: 'SUMMARIZE_CONTEXT',
          description: 'Use LLM to summarize older messages and continue debate',
        },
        {
          label: 'End debate now',
          action: 'FORCE_END',
          description: 'Generate final verdict with current state',
        },
        {
          label: 'Truncate and continue',
          action: 'TRUNCATE_CONTEXT',
          description: 'Remove older messages and continue (may lose context)',
        },
      ],
    };
  }

  private handleRetryableError(
    error: DebateError,
    context: DebateContext
  ): RecoveryAction {
    const backoff = this.calculateBackoff(error.retryCount);

    return {
      type: 'RETRY',
      delay: backoff,
      message: `${error.message}. Retrying in ${backoff / 1000}s...`,
      modifiedContext: context,
    };
  }

  private handleAuthError(
    error: DebateError,
    context: DebateContext
  ): RecoveryAction {
    return {
      type: 'USER_ACTION',
      message: 'Authentication failed. Please check your API key.',
      requiredAction: 'UPDATE_API_KEY',
      providerId: error.metadata?.providerId,
    };
  }

  private handleInvalidResponse(
    error: DebateError,
    context: DebateContext
  ): RecoveryAction {
    // For judge structured output failures
    if (error.participantId === context.judge.id) {
      return {
        type: 'RETRY',
        delay: 2000,
        message: 'Judge returned invalid format. Retrying with stricter prompt...',
        modifiedContext: {
          ...context,
          judgePromptModifier: 'strict', // Add emphasis on JSON format
        },
      };
    }

    return this.createFailureAction(error, context);
  }

  private calculateBackoff(retryCount: number): number {
    const baseDelay = 1000; // 1 second
    const maxDelay = 60000; // 60 seconds
    const exponentialDelay = baseDelay * Math.pow(2, retryCount);
    const jitter = Math.random() * 1000;

    return Math.min(exponentialDelay + jitter, maxDelay);
  }

  private createFailureAction(
    error: DebateError,
    context: DebateContext
  ): RecoveryAction {
    return {
      type: 'FAIL',
      message: `Unrecoverable error: ${error.message}`,
      error,
      suggestedAction: this.getSuggestedAction(error),
    };
  }

  private getSuggestedAction(error: DebateError): string {
    switch (error.type) {
      case ErrorType.AUTHENTICATION:
        return 'Update API key in settings';
      case ErrorType.CONTEXT_OVERFLOW:
        return 'Enable context summarization or restart debate';
      case ErrorType.RATE_LIMIT:
        return 'Wait or upgrade API tier';
      case ErrorType.NETWORK:
        return 'Check internet connection';
      default:
        return 'Contact support if issue persists';
    }
  }
}

interface RecoveryAction {
  type: 'RETRY' | 'USER_CHOICE' | 'USER_ACTION' | 'FAIL';
  message: string;
  delay?: number;
  modifiedContext?: DebateContext;
  options?: Array<{
    label: string;
    action: string;
    description: string;
  }>;
  requiredAction?: string;
  error?: DebateError;
  suggestedAction?: string;
}
```

### 6.3 Graceful Degradation

```typescript
class GracefulDegradationManager {
  // If one participant fails repeatedly, continue with remaining participants
  async handleParticipantFailure(
    debateId: string,
    participantId: string
  ): Promise<void> {
    const debate = store.getState().debates[debateId];
    const participant = debate.participants[participantId];

    // Mark participant as failed
    store.setState((state) => {
      state.debates[debateId].participants[participantId].status = 'failed';
    });

    // Notify user
    store.setState((state) => {
      state.ui.notifications.push({
        id: generateId(),
        type: 'warning',
        message: `${participant.config.displayName} has failed and will not continue in the debate.`,
        dismissible: true,
      });
    });

    // Check if we can continue with remaining participants
    const activeParticipants = Object.values(debate.participants).filter(
      (p) => p.status !== 'failed'
    );

    if (activeParticipants.length < 2) {
      // Can't continue with less than 2 participants
      return this.endDebateEarly(debateId, 'Insufficient active participants');
    }

    // Continue with remaining participants
    console.log(
      `Continuing debate with ${activeParticipants.length} active participants`
    );
  }

  // If judge fails, offer alternatives
  async handleJudgeFailure(debateId: string): Promise<void> {
    const debate = store.getState().debates[debateId];

    // Offer user choices
    store.setState((state) => {
      state.ui.notifications.push({
        id: generateId(),
        type: 'error',
        message: 'Judge agent has failed. Choose how to proceed:',
        dismissible: false,
        action: {
          label: 'Choose',
          handler: () => {
            // Show modal with options
            this.showJudgeFailureModal(debateId);
          },
        },
      });
    });
  }

  private async showJudgeFailureModal(debateId: string): Promise<void> {
    const options = [
      {
        label: 'Use different judge model',
        action: async () => {
          // Let user select alternative model
          const newJudge = await selectAlternativeJudge();
          await this.swapJudge(debateId, newJudge);
        },
      },
      {
        label: 'Continue without judge',
        action: async () => {
          // Disable judge assessments, just run debate
          await this.disableJudge(debateId);
        },
      },
      {
        label: 'End debate now',
        action: async () => {
          await this.endDebateEarly(debateId, 'Judge failure');
        },
      },
    ];

    // Show modal (implementation depends on UI framework)
    showModal({
      title: 'Judge Failure',
      message: 'The judge agent has failed. How would you like to proceed?',
      options,
    });
  }
}
```

---

## 7. Implementation Recommendations

### 7.1 Code Structure

```
src/
├── machines/
│   ├── debateMachine.ts          # XState machine definition
│   ├── guards.ts                 # State transition guards
│   ├── actions.ts                # State machine actions
│   └── services.ts               # Async services (init, stream, judge)
│
├── prompts/
│   ├── debaterPrompt.ts          # Debater system prompt builder
│   ├── judgePrompt.ts            # Judge system prompt + schema
│   ├── autoAssignPrompt.ts       # Auto-assign persona prompt
│   └── templates/                # Format-specific templates
│
├── context/
│   ├── ContextManager.ts         # Base context manager
│   ├── TruncationManager.ts      # Truncation strategy
│   ├── SlidingWindowManager.ts   # Sliding window strategy
│   ├── SummarizationManager.ts   # Summarization strategy
│   └── HybridManager.ts          # Recommended hybrid approach
│
├── providers/
│   ├── base/
│   │   ├── LLMProvider.ts        # Provider interface
│   │   └── BaseStreamingProvider.ts
│   ├── AnthropicProvider.ts
│   ├── OpenAIProvider.ts
│   ├── GoogleProvider.ts
│   └── MistralProvider.ts
│
├── services/
│   ├── DebateOrchestrator.ts     # Main orchestration service
│   ├── ProviderManager.ts        # Multi-provider coordination
│   ├── RateLimitQueue.ts         # Rate limiting + queuing
│   ├── CostTracker.ts            # Token usage + cost tracking
│   ├── TokenCounter.ts           # Cross-provider token counting
│   └── ErrorRecoveryManager.ts   # Error handling + recovery
│
├── detection/
│   ├── RepetitionDetector.ts     # Repetition detection (semantic)
│   ├── DiminishingReturnsDetector.ts
│   └── TopicDriftDetector.ts
│
├── stores/
│   ├── debateStore.ts            # Zustand store (main state)
│   ├── selectors.ts              # Memoized selectors
│   └── middleware/
│       ├── persistence.ts        # LocalStorage/IndexedDB
│       └── devtools.ts           # Redux DevTools integration
│
├── hooks/
│   ├── useDebateOrchestrator.ts  # Main hook combining XState + Zustand
│   ├── useStreamResponse.ts      # React Query streaming hook
│   ├── useDebateSubscription.ts  # Real-time event subscriptions
│   └── useContextManager.ts      # Context management hook
│
├── utils/
│   ├── embeddings.ts             # For semantic similarity
│   ├── tokenUtils.ts             # Token counting utilities
│   └── validation.ts             # Config validation
│
└── __tests__/
    ├── unit/
    │   ├── machines/
    │   ├── prompts/
    │   ├── context/
    │   └── detection/
    ├── integration/
    │   ├── debateFlow.test.ts
    │   ├── errorHandling.test.ts
    │   └── contextManagement.test.ts
    └── e2e/
        └── realAPI.test.ts
```

### 7.2 Technology Stack Summary

| Component | Technology | Justification |
|-----------|-----------|---------------|
| State Machine | XState | Visual debugging, predictable transitions, excellent TypeScript support |
| Global State | Zustand | Lightweight, minimal boilerplate, excellent DevTools |
| Server State | TanStack Query | Built-in retry, caching, streaming support |
| Token Counting | tiktoken (js) | Official OpenAI library, accurate for GPT models |
| Persistence | IndexedDB | Better for large debates, structured queries |
| Testing | Jest + Testing Library | Industry standard, excellent ecosystem |
| Type Safety | TypeScript | Essential for complex state management |

### 7.3 Implementation Phases

**Phase 1: Foundation (Week 1-2)**
- ✅ XState debate machine
- ✅ Basic prompt templates
- ✅ Zustand store setup
- ✅ Provider abstractions (existing)
- Unit tests for state machine

**Phase 2: Core Debate Flow (Week 2-3)**
- Orchestration service
- Sequential mode implementation
- Judge integration with structured output
- Context management (sliding window)
- Integration tests

**Phase 3: Advanced Features (Week 3-4)**
- Simultaneous mode
- Auto-assign personas
- Repetition detection
- Diminishing returns detection
- Context summarization (optional)

**Phase 4: Polish & Testing (Week 4-5)**
- Comprehensive error handling
- Graceful degradation
- E2E tests with real APIs
- Performance optimization
- Documentation

**Phase 5: UI Integration (Week 5-6)**
- React components for debate display
- Streaming visualization
- Error notifications
- Context warnings
- Export functionality

---

## 8. Research Sources

### Multi-Agent Systems & Debate Patterns

- [Agent system design patterns - Databricks](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)
- [Multi-Agent Design: Optimizing Agents with Better Prompts and Topologies](https://arxiv.org/html/2502.02533v1)
- [Multi-Agent Debate - AutoGen](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/multi-agent-debate.html)
- [Agentic Design Patterns Part 5, Multi-Agent Collaboration - DeepLearning.AI](https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-5-multi-agent-collaboration/)
- [Multi-agent debate with state pattern from scratch - Yixin Tian](https://www.yixtian.com/blog/10-multi-agent-debate-w-state-pattern)
- [Patterns for Democratic Multi-Agent AI: Debate-Based Consensus - Medium](https://medium.com/@edoardo.schepis/patterns-for-democratic-multi-agent-ai-debate-based-consensus-part-2-implementation-2348bf28f6a6)

### LLM-as-Judge Evaluation

- [LLM-as-a-Judge: A Practical Guide - Towards Data Science](https://towardsdatascience.com/llm-as-a-judge-a-practical-guide/)
- [Why LLM-as-a-Judge is the Best LLM Evaluation Method - Confident AI](https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method)
- [LLM-as-a-judge: complete guide - Evidently AI](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- [Using LLM-as-a-judge for automated evaluation - Hugging Face Cookbook](https://huggingface.co/learn/cookbook/en/llm_judge)
- [LLM-as-a-Judge Evaluation - Langfuse](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)

### Finite State Machines for Conversational AI

- [Guiding AI Conversations through Dynamic State Transitions](https://promptengineering.org/guiding-ai-conversations-through-dynamic-state-transitions/)
- [Dialogue Management: A Comprehensive Introduction](https://www.context-first.com/dialogue-management-introduction/)
- [Finite State Machines To The Rescue! - Haptik](https://www.haptik.ai/tech/finite-state-machines-to-the-rescue/)
- [State Machine & Dialog Systems - Meta-Guide](https://meta-guide.com/dialog-systems/state-machine-dialog-systems)

### AI Agent Orchestration

- [AI Agent Orchestration Patterns - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [What is AI Agent Orchestration? - IBM](https://www.ibm.com/think/topics/ai-agent-orchestration)
- [AI Agent Orchestration: How To Coordinate Multiple AI Agents - Botpress](https://botpress.com/blog/ai-agent-orchestration)
- [Agent Orchestration Patterns in Multi-Agent Systems - Dynamiq](https://www.getdynamiq.ai/post/agent-orchestration-patterns-in-multi-agent-systems-linear-and-adaptive-approaches-with-dynamiq)

### Testing Strategies for LLM Applications

- [Mocking External APIs in Agent Tests - Scenario](https://scenario.langwatch.ai/testing-guides/mocks/)
- [LLM Testing in 2025: Top Methods and Strategies - Confident AI](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies)
- [A Comprehensive Guide to Evaluating Multi-Agent LLM Systems - ORQ.AI](https://orq.ai/blog/multi-agent-llm-eval-system)
- [Effective Practices for Mocking LLM Responses - MLOps Community](https://home.mlops.community/public/blogs/effective-practices-for-mocking-llm-responses-during-the-software-development-lifecycle)

### Context Window Management

- [Top techniques to Manage Context Lengths in LLMs - Agenta](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms)
- [LLM Context Windows: Why They Matter and Solutions - Kolena](https://www.kolena.com/guides/llm-context-windows-why-they-matter-and-5-solutions-for-context-limits/)
- [LLM Context Windows: Basics, Examples & Prompting Best Practices - Swimm](https://swimm.io/learn/large-language-models/llm-context-windows-basics-examples-and-prompting-best-practices)
- [What is a context window? - IBM](https://www.ibm.com/think/topics/context-window)

### Repetition & Diminishing Returns Detection

- [AI Repetition Penalties: What they are and how they work - Android Police](https://www.androidpolice.com/ai-repetition-penalties-guide/)
- [Stuck in a Loop: Why AI Chatbots Keep Repeating - Medium](https://lightcapai.medium.com/stuck-in-the-loop-why-ai-chatbots-repeat-themselves-and-how-we-can-fix-it-cd93e2e784db)
- [The Illusion of Diminishing Returns: Measuring Long Horizon Execution in LLMs](https://arxiv.org/html/2509.09677v1)

---

## Appendices

### Appendix A: Example Debate State Machine Trace

```
User Action: Create debate "Should we colonize Mars?"
  → CONFIGURING

User Action: Add Claude (Pro-Mars), GPT (Pro-Earth)
  → CONFIGURING (config updated)

User Action: Click "Validate"
  → VALIDATING
    ├─ Validate topic ✓
    ├─ Validate participants (count: 2) ✓
    ├─ Validate API keys ✓
    └─ Success → READY

User Action: Click "Start Debate"
  → INITIALIZING
    ├─ Auto-assign personas
    │   ├─ Claude: "Futurist technologist, species survival focus"
    │   └─ GPT: "Environmental scientist, Earth-first priority"
    ├─ Initialize participant state
    └─ Success → RUNNING

RUNNING.AWAITING_RESPONSES (Round 1, sequential mode)
  ├─ Stream Claude response → "We must become multi-planetary..."
  ├─ RESPONSE_COMPLETE (Claude)
  ├─ Stream GPT response → "While space exploration matters..."
  └─ RESPONSE_COMPLETE (GPT) → JUDGING

RUNNING.JUDGING
  ├─ Build judge prompt with Round 1 responses
  ├─ Stream judge assessment
  └─ Result: shouldContinue=true, qualityScore=8
      → ROUND_COMPLETE

RUNNING.ROUND_COMPLETE
  └─ After 1s delay → AWAITING_RESPONSES (Round 2)

RUNNING.AWAITING_RESPONSES (Round 2)
  ├─ Stream Claude response → "GPT raises valid points, however..."
  ├─ RESPONSE_COMPLETE (Claude)
  ├─ Stream GPT response → "Claude's vision is admirable, but..."
  └─ RESPONSE_COMPLETE (GPT) → JUDGING

RUNNING.JUDGING
  ├─ Build judge prompt with Round 2 responses
  ├─ Stream judge assessment
  └─ Result: shouldContinue=false, flags.diminishingReturns=true
      → COMPLETING

COMPLETING
  ├─ Build final verdict prompt
  ├─ Stream judge final verdict
  └─ Success → COMPLETED

COMPLETED
  ├─ Save to debate history
  └─ User can export, replay, or start new debate
```

### Appendix B: Sample Judge Assessment (JSON)

```json
{
  "shouldContinue": false,
  "qualityScore": 7,
  "assessments": [
    {
      "participant": "Claude (Pro-Mars)",
      "strengths": [
        "Strong long-term thinking about species survival",
        "Acknowledged GPT's points about Earth's importance",
        "Used specific examples (asteroid risks, resource depletion)"
      ],
      "weaknesses": [
        "Did not address the cost comparison adequately",
        "Some arguments repeated from Round 1"
      ],
      "score": 7
    },
    {
      "participant": "GPT (Pro-Earth)",
      "strengths": [
        "Practical focus on immediate climate crisis",
        "Cost-benefit analysis was compelling",
        "Engaged directly with Claude's survival argument"
      ],
      "weaknesses": [
        "Could have explored dual-track approach more",
        "Slightly repetitive on funding allocation point"
      ],
      "score": 7
    }
  ],
  "flags": {
    "repetitive": true,
    "drifting": false,
    "diminishingReturns": true,
    "convergenceReached": false
  },
  "reasoning": "Both participants have made their core arguments clearly over two rounds. Round 2 responses show some repetition of Round 1 points with minor variations. While engagement quality remains good, new substantive insights are diminishing. Positions are well-articulated but irreconcilable.",
  "recommendations": "Conclude debate now. Both sides have presented strong cases. Further rounds unlikely to produce significant new insights. Recommend final verdict focusing on the fundamental trade-off between long-term species survival vs immediate planetary health."
}
```

---

**End of Document**
