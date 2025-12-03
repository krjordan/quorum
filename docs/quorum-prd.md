# Quorum - Product Requirements Document

## Overview

**Quorum** is an open-source platform that enables multiple LLMs to engage in structured debates and discussions on user-provided topics. Users can observe AI models argue different positions, with an AI judge monitoring quality, detecting diminishing returns, and determining when meaningful conclusions have been reached.

## Problem Statement

Single-LLM interactions can produce biased or one-sided responses. By pitting multiple models against each other in structured debate, users can:
- See multiple perspectives on complex topics
- Identify where models agree (potential consensus/truth)
- Identify where models diverge (areas of genuine uncertainty)
- Get higher quality reasoning through adversarial pressure

## Target Users

- AI enthusiasts and researchers exploring model behavior
- Developers evaluating different LLMs
- Educators demonstrating critical thinking and debate
- Anyone seeking multi-perspective analysis on complex topics

---

## Core Features (MVP)

### 1. Debate Configuration

**Topic Input**
- Free-text field for the debate topic or question
- Optional: Brief context or constraints the user wants to set

**Participant Selection**
- Dropdown selectors for 2+ LLM debaters (populated from configured API keys)
- Separate dropdown for Judge LLM
- Ability to add/remove debaters before starting

**Persona Assignment**
- Per-debater toggle: "Auto-assign" or "Custom"
- Auto-assign: System determines optimal stance distribution for productive debate
- Custom: User provides specific persona/position instructions

**Debate Format Selection**
- Free-form: No structure, judge decides when complete
- Structured rounds: Opening → Rebuttals (configurable count) → Closing → Verdict
- Round-limited: Hard cap on number of exchanges
- Convergence-seeking: Runs until agreement or irreconcilable positions detected

### 2. API Key Management

**Settings Panel**
- Add/remove API keys for supported providers:
  - Anthropic (Claude)
  - OpenAI (GPT-4, etc.)
  - Google (Gemini)
  - Mistral
  - Others as demand dictates
- Key validation on entry
- Local storage (with clear security disclaimers) or session-only option
- Visual indicator of which providers are currently available

### 3. Live Debate Interface

**Response Display**
- Real-time streaming of responses as they generate
- Clear visual distinction between participants (color coding, avatars, or labels)
- Participant name labels (e.g., "Claude (Pro-Colonization)")
- Timestamp or round indicators

**Simultaneous Response Handling**
- For simultaneous rounds: responses generate in parallel, revealed together (or staggered for effect)
- Clear indication of which "batch" of responses go together

**Cross-Referencing**
- LLMs can reference each other by name
- System prompts include awareness of other participants

### 4. Judge Agent

**Responsibilities**
- Monitor debate quality and relevance
- Detect diminishing returns / repetition
- Identify topic drift
- Determine when to conclude (in free-form/convergence modes)
- Provide final verdict and summary

**Judge Output**
- Per-round assessment (optional, can be hidden or shown)
- Final summary including:
  - Key points from each side
  - Areas of agreement
  - Areas of disagreement
  - Winner (if applicable) or "no clear winner"
  - Quality score or assessment

**Judge Controls**
- User can select which LLM serves as judge
- Judge operates with structured output prompts for consistency

### 5. Debate History & Export

- Save completed debates locally
- Export as Markdown or JSON
- Replay functionality (step through rounds)

---

## Stretch Goals (Post-MVP)

### User Interjection
- Ability for user to pause debate and inject a question or redirect
- LLMs acknowledge and incorporate user input before continuing

### Audience Features
- Per-round voting (which response was strongest?)
- Comments or reactions on specific points
- Shareable debate links

### Advanced Judge Features
- Fact-checking against web search
- Citation requests ("provide sources for that claim")
- Bias detection

### Branching Debates
- Fork at any point to explore tangent
- Tree view of debate branches

### Research Mode
- Enable web search for debaters
- Judge verifies claims against sources
- Source aggregation in final summary

### Preset Templates
- Common debate formats pre-configured
- Topic suggestions / random topic generator

### Model Comparison Analytics
- Track win rates by model over many debates
- Identify which models perform better on which topic types

---

## Technical Architecture (FINALIZED)

> **Status:** ✅ Architecture Finalized (November 2025)
> **Deployment Model:** Docker Compose (local-first), cloud deployment as stretch goal
> **Research Documents:** See `TECH_STACK_CONSENSUS.md`, `FINAL_ARCHITECTURE.md`
> **Confidence Level:** Very High (9/10)

### Final Tech Stack

```yaml
# FRONTEND (UI Layer)
Framework: Next.js 15 (App Router)
UI Library: React 19 (Concurrent Features)
Language: TypeScript (strict mode)
State Management:
  - Zustand (UI/debate state)
  - TanStack Query (server state/caching)
Styling: Tailwind CSS
UI Components: shadcn/ui (recommended)
Port: 3000

# BACKEND (LLM Orchestration Layer)
Framework: FastAPI (Python 3.11+)
LLM SDK: LiteLLM (100+ providers, auto-normalization)
Streaming: SSE via FastAPI StreamingResponse
Rate Limiting: In-memory (MVP) or Redis (optional)
Token Counting: tiktoken + provider APIs
Port: 8000

# ORCHESTRATION
State Machine: XState (debate lifecycle FSM)
Context Management: Hybrid (sliding window + optional summarization)
Judge System: Structured JSON output with schema validation

# STORAGE
API Keys: Backend environment variables (.env file)
Debate History: SQLite (local file) or PostgreSQL (optional)
Export: Backend generates files, frontend downloads

# DEPLOYMENT
Development: docker-compose up (single command)
Production: Docker Compose (local) or Cloud (stretch goal)
Future Cloud Options: Vercel + Railway, Fly.io, DigitalOcean
Testing: Vitest (unit) + Playwright (E2E)
CI/CD: GitHub Actions
```

### Architecture Decision Rationale

**Frontend: Next.js 15 + React 19**
- **SSE Renaissance (2025)**: Next.js 15 has native, first-class Server-Sent Events support
- **Performance**: 40-60% faster page loads, smaller bundles (85KB vs 140KB gzipped)
- **Ecosystem**: 10:1 ratio of production LLM streaming examples vs Angular
- **Developer Experience**: Simpler implementation (~60 lines vs ~80 for multi-stream setup)
- **Open Source Appeal**: 10-20x larger contributor pool

**Backend: Python + FastAPI + LiteLLM**
- **Development Speed**: 10-20x faster than Rust (MVP in 3-5 weeks vs 8-12 weeks)
- **LLM SDK Maturity**: LiteLLM handles 80% of complexity (100+ providers, automatic streaming normalization)
- **Performance**: Backend handles heavy lifting, browser stays lightweight
- **Proven at Scale**: LiteLLM handles 2M+ requests/month in production
- **Better UX**: Backend manages multiple LLM streams efficiently vs browser overhead

**Docker-Based Deployment (Local-First)**
- **Zero Hosting Costs**: Users run locally with docker-compose up
- **API Key Security**: Keys in backend .env file, never exposed to browser
- **Performance**: Backend handles connection pooling, token counting, context management
- **User Control**: Users manage their own API usage and costs
- **Future-Proof**: Easy to deploy to cloud later (stretch goal), already containerized

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│         User's Local Machine (Docker Compose)                │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        Frontend Container (localhost:3000)              │ │
│  │        Next.js React App (UI Only)                      │ │
│  │                                                          │ │
│  │  ┌──────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │ Zustand  │  │  TanStack   │  │  UI Components  │   │ │
│  │  │UI State  │  │  Query      │  │  (shadcn/ui)    │   │ │
│  │  └──────────┘  └─────────────┘  └─────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                   HTTP/SSE (localhost:8000)                  │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        Backend Container (localhost:8000)               │ │
│  │        FastAPI + LiteLLM (Orchestration)                │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐│ │
│  │  │  LiteLLM Proxy Layer                                ││ │
│  │  │  - Automatic provider normalization                 ││ │
│  │  │  - Streaming SSE → Frontend                         ││ │
│  │  │  - Token counting & cost tracking                   ││ │
│  │  │  - Rate limiting & retry logic                      ││ │
│  │  │  - Context window management                        ││ │
│  │  └────────────────────────────────────────────────────┘│ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐│ │
│  │  │  Debate Engine (XState FSM)                         ││ │
│  │  │  - State management (11 states)                     ││ │
│  │  │  - Round orchestration                              ││ │
│  │  │  - Judge integration                                ││ │
│  │  └────────────────────────────────────────────────────┘│ │
│  │                                                          │ │
│  │  Storage: API keys (.env), Debates (SQLite)             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                   Direct API Calls (HTTPS)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Anthropic │    │  OpenAI  │    │  Google  │
    │ API      │    │  API     │    │  API     │
    └──────────┘    └──────────┘    └──────────┘

    User's API keys (.env) → User pays for their own usage
```

### API Integration

**Backend LLM Orchestration (FastAPI + LiteLLM)**
- **Abstraction Layer**: LiteLLM handles all provider normalization automatically
- **Provider Support**: 100+ providers (OpenAI, Anthropic, Google, Mistral, etc.)
- **Streaming Protocol**: Backend receives from providers, streams to frontend via SSE
- **Error Handling**: Exponential backoff with jitter (1s base, 10s max, 3 retries)
- **Connection Pooling**: Backend maintains efficient connections to LLM providers

**Provider Streaming Differences (Auto-Normalized by LiteLLM)**
- **OpenAI/Mistral**: Delta chunks with `[DONE]` marker (nearly identical)
- **Anthropic**: Structured events (`message_start`, `content_block_delta`, `message_stop`)
- **Google Gemini**: Full chunks per update (less granular, some reported bugs)
- **Normalization**: LiteLLM handles all differences - frontend receives uniform SSE stream

**Context Management Strategy**
- **Default**: Sliding window (last 10 rounds + system prompts)
- **Token Tracking**: Real-time counting via provider APIs + tiktoken
- **Warning System**: Alert at 80% of context window capacity
- **Overflow Handling**:
  - Option 1: Truncate oldest rounds (preserves recent context)
  - Option 2: Summarize middle rounds (preserves arc, requires LLM call)
  - Option 3: User prompt to continue or conclude

### Debate Orchestration

**State Machine Design (XState)**
- **States**: CONFIGURING → STARTING → RUNNING → JUDGING → COMPLETED
- **Sub-states**: RUNNING → AWAITING_RESPONSES → ROUND_COMPLETE
- **Format Guards**: Round-limited, convergence-seeking, free-form, structured
- **Error States**: PARTICIPANT_FAILED → recovery or graceful degradation

**Prompt Engineering**

**Debater System Prompts:**
```typescript
{
  role: "system",
  content: `You are ${persona.name}, participating in a structured debate on: "${topic}".

Your position: ${persona.position}
Other participants: ${otherDebaters.map(d => d.name).join(", ")}

Guidelines:
- Engage directly with other participants' points
- Reference specific arguments from previous rounds
- Stay on topic and maintain civility
- Format: ${format.instructions}`
}
```

**Judge System Prompts (Structured JSON Output):**
```typescript
{
  role: "system",
  content: `You are the impartial judge for this debate on: "${topic}".

Evaluate each round using this rubric:
1. Logical Consistency (20%)
2. Evidence Quality (20%)
3. Engagement with Opponents (20%)
4. Novelty/Insight (15%)
5. Persuasiveness (15%)
6. Relevance (10%)

Return JSON:
{
  "roundAssessment": { /* scores per debater */ },
  "qualityScore": 0-10,
  "repetitionDetected": boolean,
  "topicDrift": boolean,
  "shouldConclude": boolean,
  "reasoning": "..."
}`
}
```

**Auto-Assignment Prompt:**
```typescript
{
  role: "system",
  content: `Given the topic: "${topic}" and ${debaterCount} participants,
  assign diverse, opposing perspectives that will create productive debate.

Return JSON array of personas:
[
  { "name": "Persona 1", "position": "...", "key_arguments": [...] },
  ...
]

Aim for productive tension, not just binary opposition.`
}
```

### Cost Management & Tracking

**Real-Time Cost Estimation:**
- Track input/output tokens per provider
- Calculate costs based on current pricing:
  - Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
  - GPT-4o: $2.50/MTok input, $10/MTok output
  - Gemini 1.5 Flash: $0.075/MTok input, $0.30/MTok output

**User Warning Thresholds:**
- 🟡 Yellow: $0.50 estimated (show warning)
- 🔴 Red: $1.00 estimated (confirm to continue)
- 🛑 Stop: $2.00 estimated (require explicit override)

**Example Debate Cost:**
- 5 rounds, 3 debaters, 1 judge
- ~1500 input + 1800 output tokens per round
- Total: ~16,500 tokens = **$0.08-$0.11** (depending on models)

### Security & API Key Management (Docker Deployment)

**API Key Storage:**
- **Backend Environment Variables**: API keys in `.env` file (gitignored)
- **User Setup**: Users copy `.env.example` to `.env` and add their own keys
- **Security**: Keys never exposed to frontend/browser
- **Never**: API keys in Git commits, frontend code, or localStorage

**Example .env File:**
```bash
# User's API keys (gitignored)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...
```

**Validation:**
- Backend validates API keys on startup
- Returns available providers to frontend
- Visual indicators in UI: ✅ Valid, ❌ Invalid, ⚠️ Rate limited

**Rate Limiting:**
- Backend handles rate limiting (in-memory for MVP)
- Exponential backoff on provider rate limits
- No cross-user coordination needed (single user per instance)

---

## MVP Scope Summary

**In Scope:**
- 2-4 LLM debaters
- 1 LLM judge
- 4 debate format options
- API key management (local storage)
- Live streaming responses
- Simultaneous and sequential response modes
- Auto-assign and custom personas
- Judge verdict and summary
- Basic export (Markdown)

**Out of Scope (for now):**
- User interjection
- Web search / research mode
- Branching debates
- Persistent backend / accounts
- Analytics and model comparison
- Audience voting

---

## Success Metrics

For an open-source project, success looks like:
- GitHub stars and forks
- Community contributions (PRs, issues, feature requests)
- Usage (if any telemetry is opt-in)
- Quality of debates produced (subjective, community feedback)

---

## Questions Resolved (November 2025)

### ✅ 1. Streaming Consistency
**Question:** Different providers handle streaming differently. How much effort to normalize?

**Answer:** Use Vercel AI SDK + LiteLLM for automatic normalization. Providers differ significantly:
- OpenAI/Mistral: Nearly identical (delta chunks)
- Anthropic: Sophisticated structured events
- Google Gemini: Less mature, some bugs

**Solution:** Abstraction layer handles differences transparently. Estimated effort: 2-3 days vs 2-3 weeks manual implementation.

### ✅ 2. Token Costs
**Question:** Should we show estimated/running cost? Warn users?

**Answer:** Yes, implement real-time cost tracking with three-tier warning system:
- 🟡 Yellow warning at $0.50
- 🔴 Red warning at $1.00 (confirm to continue)
- 🛑 Stop at $2.00 (require explicit override)

**Typical costs:** 5-round debate = $0.08-$0.11 (very affordable for quality insights)

### ✅ 3. Rate Limits
**Question:** Queue management needed for simultaneous calls to same provider?

**Answer:** Yes, implement Upstash Redis-based rate limiting with per-user, per-provider quotas. Queue simultaneous requests to same provider with exponential backoff (1s base, 10s max, 3 retries).

**Mitigation:** Allow users to select different providers per debater to distribute load.

### ✅ 4. Context Window Limits
**Question:** Summarize, truncate, or fail gracefully?

**Answer:** Hybrid approach with user choice:
- **Default**: Sliding window (last 10 rounds + system prompts)
- **Warning**: Alert at 80% capacity with options:
  1. Truncate oldest rounds (fast, preserves recent context)
  2. Summarize middle rounds (slow, preserves debate arc)
  3. Conclude debate (user decision)

### ✅ 5. Judge Reliability
**Question:** Recourse if judge makes bad call? "Appeal" feature?

**Answer:** For MVP: No appeal system (adds complexity). Post-MVP options:
- User override: "Continue anyway" button
- Multiple judges: Consensus voting (expensive)
- Judge audit log: Show reasoning, allow user feedback

**Mitigation for MVP:** Clear judge rubric, structured JSON output, allow debate export for manual review.

---

## Implementation Roadmap (9 Weeks to v0.1)

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Single-LLM streaming chat interface

- [ ] Next.js 15 project setup with TypeScript strict mode
- [ ] Vercel AI SDK integration (OpenAI provider first)
- [ ] Basic SSE streaming for single LLM
- [ ] Zustand state management setup
- [ ] Tailwind CSS + shadcn/ui components
- [ ] Local storage for API keys (with security disclaimers)

**Success Criteria:** Can chat with Claude/GPT with streaming responses

### Phase 2: Core Debate Engine (Weeks 3-4)
**Goal:** Multi-LLM debate with basic orchestration

- [ ] Multi-provider support (Anthropic, Google, Mistral)
- [ ] XState debate state machine implementation (11 states)
- [ ] Parallel streaming (2-4 debaters simultaneously)
- [ ] Context management (sliding window, token counting)
- [ ] Real-time cost tracking and warnings

**Success Criteria:** 2-4 LLMs can debate topic in free-form mode

### Phase 3: Judge & Features (Weeks 5-6)
**Goal:** Complete MVP with all core features

- [ ] Judge agent with structured JSON output
- [ ] Evaluation rubric (6 dimensions, weighted scoring)
- [ ] Stopping criteria detection (repetition, drift, diminishing returns)
- [ ] Debate format selection (4 formats: free-form, structured, round-limited, convergence)
- [ ] Persona assignment (auto-assign + custom)
- [ ] Export functionality (Markdown, JSON)

**Success Criteria:** Complete debates with judge verdict and summary

### Phase 4: Polish & Testing (Weeks 7-8)
**Goal:** Production-ready quality

- [ ] Comprehensive test suite (Vitest unit tests, Playwright E2E)
- [ ] Error handling and recovery flows
- [ ] Security audit (API key management, CORS, rate limiting)
- [ ] Performance optimization (bundle size, streaming latency)
- [ ] Responsive design (desktop, tablet)
- [ ] Accessibility audit (WCAG 2.1 AA compliance)
- [ ] Documentation (README, ARCHITECTURE, CONTRIBUTING)

**Success Criteria:** >80% test coverage, zero critical security issues, <100ms backend latency

### Phase 5: Deployment & Launch (Week 9)
**Goal:** Public open-source release

- [ ] Vercel deployment with environment variables
- [ ] Docker containerization (self-hosted option)
- [ ] GitHub repository setup (MIT license)
- [ ] Community guidelines (CONTRIBUTING.md, CODE_OF_CONDUCT.md)
- [ ] Demo video and screenshots
- [ ] Launch announcement (Reddit r/LocalLLaMA, Hacker News, Twitter/X)

**Success Criteria:** Successfully deployed, 100+ GitHub stars in first week

---

## Next Immediate Steps (This Week)

1. ✅ ~~Finalize tech stack decisions~~ (COMPLETE)
2. **Create initial Next.js 15 project structure**
3. **Design UI wireframes (Figma or sketches)**
4. **Set up development environment and tooling**
5. **Implement Phase 1: Single-LLM streaming (2 weeks)**

**Critical Path:** Start implementation immediately to hit 9-week MVP target.

