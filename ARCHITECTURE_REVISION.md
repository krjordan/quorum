# Architecture Revision: Local-First, Self-Hosted Deployment

**Date:** November 29, 2025
**Reason:** Project will be open-source for users to clone and run locally with their own API keys
**Impact:** Significant simplification - no hosted service, no serverless infrastructure costs

---

## Key Change: Client-Side First for MVP

Since users will run Quorum locally with their own API keys, we don't need a backend proxy for API key security. This **drastically simplifies** the architecture.

---

## Revised Tech Stack (Local-First)

```yaml
# FRONTEND (Unchanged - Still Excellent Choice)
Framework: Next.js 15 (App Router)
UI Library: React 19
Language: TypeScript (strict mode)
State Management:
  - Zustand (UI/debate state)
  - TanStack Query (server state/caching)
Streaming: Server-Sent Events (SSE) via HTTP/2
Styling: Tailwind CSS
UI Components: shadcn/ui

# BACKEND (Simplified - Optional for MVP)
Architecture: Client-Side First (API calls direct from browser)
Optional Backend: Next.js API Routes (for advanced features)
LLM Abstraction: Vercel AI SDK (client-side) OR official provider SDKs
Storage: Local browser storage (API keys, debate history)
Rate Limiting: Client-side (respect provider limits)
Token Counting: tiktoken (client-side)

# DEPLOYMENT (Self-Hosted)
Local Development: npm run dev (Next.js dev server)
Production Build: npm run build && npm start (standalone Next.js server)
Docker: Optional containerization for easy deployment
Hosting Options:
  - Local machine (npm start)
  - Self-hosted VPS (docker-compose)
  - Personal Vercel/Netlify (user's own account)
```

---

## Architecture Comparison

### ❌ Original (Hosted Service - NOT APPLICABLE)

```
User Browser → Vercel Edge Functions → LLM APIs
              (API key security layer)
```

**Problems:**
- You pay for everyone's usage
- Requires backend infrastructure
- Rate limiting complexity
- Cost management needed

### ✅ Revised (Local-First - CORRECT FOR THIS PROJECT)

```
User Browser (local machine) → LLM APIs
    ↑
Local API Keys (env vars or browser storage)
```

**Benefits:**
- Zero hosting costs for you
- Users pay for their own API usage
- Simpler architecture (no backend needed for MVP)
- No rate limiting coordination needed
- Users control their own data

---

## Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│         User's Local Machine (http://localhost:3000)        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Next.js React App (Client-Side)             │  │
│  │                                                        │  │
│  │  ┌──────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │ Zustand  │  │  TanStack   │  │ XState Debate   │  │  │
│  │  │UI State  │  │  Query      │  │ State Machine   │  │  │
│  │  └──────────┘  └─────────────┘  └─────────────────┘  │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  LLM Client Layer (Vercel AI SDK or SDKs)        │ │  │
│  │  │  - Anthropic SDK (@anthropic-ai/sdk)             │ │  │
│  │  │  - OpenAI SDK (openai)                           │ │  │
│  │  │  - Google Generative AI SDK                      │ │  │
│  │  │  - Streaming response handlers                   │ │  │
│  │  │  - Token counting (tiktoken)                     │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  Local Storage                                    │ │  │
│  │  │  - API keys (.env.local OR browser storage)      │ │  │
│  │  │  - Debate history (IndexedDB)                    │ │  │
│  │  │  - User preferences                              │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                  Direct API Calls (HTTPS)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Anthropic │    │  OpenAI  │    │  Google  │
    │  API     │    │   API    │    │   API    │
    └──────────┘    └──────────┘    └──────────┘
```

---

## API Key Management (Local-First Approach)

### Option 1: Environment Variables (Recommended for Local Dev)

**Setup:**
```bash
# .env.local (gitignored)
NEXT_PUBLIC_ANTHROPIC_API_KEY=sk-ant-...
NEXT_PUBLIC_OPENAI_API_KEY=sk-proj-...
NEXT_PUBLIC_GOOGLE_API_KEY=...
```

**Security Note:** `NEXT_PUBLIC_` means these are exposed to the browser. This is **fine** for local development, but users should be warned not to commit `.env.local` to version control.

### Option 2: Browser Storage (Runtime Configuration)

**Setup in UI:**
```tsx
// Settings panel
<ApiKeyInput
  provider="Anthropic"
  onSave={(key) => localStorage.setItem('anthropic_key', key)}
/>
```

**Security Note:** Keys stored in `localStorage` are only accessible on user's own machine. Still vulnerable to XSS, but acceptable for local-first app.

### Recommended Hybrid Approach

1. **First run:** User enters API keys in settings UI → stored in localStorage
2. **Developer setup:** Optionally use `.env.local` for convenience
3. **Docker deployment:** Mount `.env` file as volume

---

## LLM Client Implementation Options

### Option A: Official Provider SDKs (More Control)

**Pros:**
- Type-safe, official APIs
- Full control over requests
- Better error messages

**Cons:**
- More code to write per provider
- Manual streaming normalization

**Example (Anthropic):**
```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY,
  dangerouslyAllowBrowser: true // Required for client-side
});

const stream = await client.messages.create({
  model: 'claude-sonnet-4-5',
  messages: [...],
  stream: true
});

for await (const event of stream) {
  if (event.type === 'content_block_delta') {
    // Handle streaming chunk
  }
}
```

### Option B: Vercel AI SDK (Simpler, Unified)

**Pros:**
- Unified interface across providers
- React hooks (`useChat`, `useCompletion`)
- Streaming normalization built-in

**Cons:**
- Less control over provider-specific features
- Abstraction layer adds slight overhead

**Example:**
```typescript
import { useChat } from 'ai/react';

const { messages, append, isLoading } = useChat({
  api: '/api/chat', // Can also be client-side with custom fetch
  body: {
    model: 'claude-sonnet-4-5',
    provider: 'anthropic'
  }
});
```

### Recommendation: Hybrid Approach

- **MVP:** Use Vercel AI SDK for speed (client-side mode with `dangerouslyAllowBrowser`)
- **Post-MVP:** Add official SDKs for advanced features
- **Abstraction:** Keep provider logic in separate modules for easy swapping

---

## Backend: Truly Optional for MVP

Since this is local-first, backend is **only needed for:**

### Not Needed for MVP:
- ❌ API key security (users have their own keys locally)
- ❌ Rate limiting coordination (users manage their own quotas)
- ❌ Multi-user support (single user per instance)

### Optional for Advanced Features:
- ⚠️ Debate persistence (can use IndexedDB client-side for MVP)
- ⚠️ Summarization (can call LLM client-side)
- ⚠️ Analytics (can be client-side only)

### When to Add Backend:
- Post-MVP: If users want to share debates (need database)
- Post-MVP: If you add collaborative features (WebSockets)
- Post-MVP: If you offer hosted version (then need the proxy architecture)

---

## Deployment Options for Users

### 1. Local Development (Simplest)

```bash
git clone https://github.com/you/quorum.git
cd quorum
npm install
cp .env.example .env.local
# Edit .env.local with API keys
npm run dev
# Open http://localhost:3000
```

### 2. Production Build (Self-Hosted)

```bash
npm run build
npm start
# Open http://localhost:3000
```

### 3. Docker (Most Portable)

```dockerfile
# Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t quorum .
docker run -p 3000:3000 --env-file .env quorum
```

### 4. User's Own Vercel/Netlify (Optional)

```bash
# User can deploy to their own account (free tier)
vercel deploy
# or
netlify deploy
```

**Cost:** Free tier sufficient for personal use

---

## Updated Concerns & Solutions

### ❓ CORS Issues?

**Problem:** Browsers block cross-origin requests by default.

**Solution:** Most LLM providers support CORS for API requests:
- ✅ Anthropic: CORS enabled for browser requests
- ✅ OpenAI: CORS enabled
- ⚠️ Google Gemini: Check CORS support (may need API route proxy)

**Fallback:** Lightweight Next.js API route proxy if needed (10 lines per provider).

### ❓ API Key Exposure?

**Problem:** Keys are in browser memory/localStorage.

**Solution:** This is **acceptable** for local-first apps:
- User's machine, user's keys
- No different from API keys in `.env` files
- Same model as: Postman, curl, terminal tools
- **Add clear warning in UI:** "Keys stored locally, don't share your machine"

### ❓ Rate Limiting?

**Problem:** User might hit provider rate limits.

**Solution:**
- Client-side exponential backoff (built into Vercel AI SDK)
- Show error messages with retry timing
- Let users manage their own quotas
- No coordination needed (single user per instance)

### ❓ Token Counting & Costs?

**Problem:** Users should know debate costs.

**Solution:**
- Client-side `tiktoken` for token counting
- Show estimated costs in UI before starting
- Real-time cost tracking during debate
- Same warning thresholds ($0.50, $1.00, $2.00)

---

## Revised Implementation Priorities

### Phase 1: Foundation (Weeks 1-2)
- [x] Next.js 15 project setup
- [x] Client-side API key management (localStorage + .env.local)
- [x] Single LLM streaming (Anthropic SDK or Vercel AI SDK)
- [x] Basic chat UI with streaming
- **Backend:** None needed

### Phase 2: Core Debate Engine (Weeks 3-4)
- [x] Multi-provider support (3+ providers)
- [x] Parallel streaming (client-side Promise.all)
- [x] XState debate state machine
- [x] Context management (client-side)
- [x] Token counting (tiktoken in browser)
- **Backend:** None needed

### Phase 3: Judge & Features (Weeks 5-6)
- [x] Judge agent (client-side LLM call)
- [x] Debate formats
- [x] Export (Markdown, JSON) - client-side file download
- **Backend:** None needed

### Phase 4: Polish & Testing (Weeks 7-8)
- [x] Error handling
- [x] Testing
- [x] Documentation
- **Backend:** None needed

### Phase 5: Deployment (Week 9)
- [x] Docker setup
- [x] README with deployment options
- [x] Open source release
- **Backend:** Optional API routes for CORS if needed

---

## When Backend Becomes Necessary

### Trigger 1: Sharing Debates
**Need:** Users want to share debate links
**Solution:** Add PostgreSQL + API routes for saving/loading debates
**Complexity:** 2-3 days

### Trigger 2: CORS Issues
**Need:** Provider doesn't support browser CORS
**Solution:** Lightweight Next.js API route proxy (10-20 lines per provider)
**Complexity:** 1 day

### Trigger 3: Hosted Version (Future)
**Need:** You decide to offer hosted version later
**Solution:** Implement original serverless proxy architecture
**Complexity:** 1-2 weeks

---

## Updated Tech Stack Summary

```yaml
# SIMPLIFIED STACK (Local-First)

FRONTEND:
  Framework: Next.js 15
  Runtime: Client-Side (no SSR needed for MVP)
  State: Zustand + TanStack Query
  LLM Clients: Vercel AI SDK (client mode) OR official SDKs
  Storage: localStorage + IndexedDB

BACKEND:
  MVP: None (100% client-side)
  Optional: Next.js API routes (if CORS issues)

DEPLOYMENT:
  Local: npm run dev
  Production: npm start or Docker
  Hosting: User's own machine/VPS
```

---

## Advantages of This Approach

✅ **Zero hosting costs for you**
✅ **Users pay for their own API usage**
✅ **Simpler architecture (no backend complexity)**
✅ **Faster MVP development (remove backend from Phase 1-4)**
✅ **True open source (users have full control)**
✅ **Privacy-first (no data leaves user's machine)**
✅ **Easy to run (git clone + npm install + add keys)**

---

## Next Steps (Updated)

1. ✅ Architecture revised for local-first deployment
2. **Update PRD to reflect client-side-first approach**
3. **Remove Vercel Edge Functions from documentation**
4. **Add Docker setup instructions**
5. **Begin Phase 1 with client-side implementation**

---

**Status:** Architecture revised and simplified for local-first, self-hosted deployment model.
