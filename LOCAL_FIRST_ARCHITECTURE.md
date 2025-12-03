# Quorum: Local-First Architecture (REVISED)

**Date:** November 30, 2025
**Reason:** Project is open-source for users to clone and run locally, not a hosted service
**Impact:** Significant simplification - removes backend complexity

---

## TL;DR

Since you're **not hosting this as a service** and users will **clone and run locally with their own API keys**, the architecture is much simpler:

### What Changed:
- ❌ **Remove:** Vercel Edge Functions, backend proxy, Upstash Redis, server-side key storage
- ✅ **Keep:** Next.js + React frontend, client-side LLM calls, local storage
- ✅ **Result:** 100% client-side for MVP, zero hosting costs for you

---

## Simplified Tech Stack

```yaml
# FRONTEND (Same - Still Best Choice)
Framework: Next.js 15
UI: React 19 + TypeScript
State: Zustand + TanStack Query
Streaming: SSE (client-side)
Styling: Tailwind CSS

# LLM INTEGRATION (Client-Side)
SDKs: @anthropic-ai/sdk, openai, @google/generative-ai
Streaming: Direct API calls from browser
Token Counting: tiktoken (runs in browser)

# BACKEND
MVP: None needed!
Optional: Next.js API routes (only if CORS issues)

# STORAGE
API Keys: localStorage or .env.local
Debates: IndexedDB (browser storage)
Export: Client-side file download

# DEPLOYMENT
Local: npm run dev
Production: npm start or Docker
Zero hosting costs for you!
```

---

## Architecture Diagram

### Before (Hosted Service - Not Needed):
```
Browser → Your Backend (Edge Functions) → LLM APIs
          ↑ (you pay for server costs)
```

### After (Local-First - What You Want):
```
User's Browser (localhost:3000) → LLM APIs directly
    ↑                               ↑
User's API keys              User pays for usage
```

---

## How It Works

### 1. User Clones Your Repo
```bash
git clone https://github.com/you/quorum.git
cd quorum
npm install
```

### 2. User Adds Their API Keys

**Option A: Environment Variables (.env.local)**
```bash
# .env.local (gitignored)
NEXT_PUBLIC_ANTHROPIC_API_KEY=sk-ant-...
NEXT_PUBLIC_OPENAI_API_KEY=sk-proj-...
NEXT_PUBLIC_GOOGLE_API_KEY=...
```

**Option B: Settings UI (localStorage)**
- User enters keys in your app's settings page
- Stored in browser's localStorage
- Only on their machine

### 3. User Runs Locally
```bash
npm run dev
# Opens http://localhost:3000
```

### 4. App Makes Direct API Calls
```typescript
// Client-side code
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY,
  dangerouslyAllowBrowser: true // Required for client-side
});

const stream = await client.messages.create({
  model: 'claude-sonnet-4-5',
  messages: messages,
  stream: true
});

for await (const event of stream) {
  // Handle streaming response
}
```

---

## Why This is Better for Your Use Case

### ✅ Advantages:
1. **Zero hosting costs** - Users run on their machines
2. **Zero backend complexity** - No server code needed
3. **User pays for API usage** - Not your problem
4. **Privacy-first** - Data never leaves user's machine
5. **Faster MVP** - Remove entire backend from roadmap
6. **True open source** - Users have full control

### ⚠️ Trade-offs (Acceptable):
1. API keys in browser memory - **Fine** for local-first (same as Postman, curl, etc.)
2. No multi-user features - **Not needed** for MVP
3. No debate sharing - **Can add later** with optional backend

---

## Security Model

**Question:** "Isn't it insecure to have API keys in the browser?"

**Answer:** For local-first apps, this is the standard model:
- ✅ User's machine, user's keys
- ✅ Same security as `.env` files, Postman, curl commands
- ✅ Keys never transmitted except to official LLM APIs
- ✅ No different than running scripts with API keys locally

**Best Practices:**
- Clear warning in UI: "Keys stored locally - don't share your screen"
- `.env.local` in `.gitignore`
- Option to use session-only (not persisted)

---

## Implementation Changes

### Phase 1: Foundation (Weeks 1-2)
- [x] Next.js 15 setup
- [x] **Settings UI for API keys (localStorage)**
- [x] **Client-side Anthropic SDK integration**
- [x] Basic streaming chat
- **NO BACKEND NEEDED**

### Phase 2: Core Engine (Weeks 3-4)
- [x] Multi-provider support (OpenAI, Google SDKs)
- [x] **Client-side parallel streaming (Promise.all)**
- [x] XState debate FSM
- [x] **Client-side token counting (tiktoken)**
- **NO BACKEND NEEDED**

### Phase 3-5: Same as before
- No changes to judge, export, testing, deployment phases
- **NO BACKEND NEEDED**

---

## Deployment Options for Users

### Option 1: Local Development (Most Common)
```bash
npm run dev
# http://localhost:3000
```

### Option 2: Production Build
```bash
npm run build
npm start
```

### Option 3: Docker
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm ci && npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t quorum .
docker run -p 3000:3000 --env-file .env quorum
```

### Option 4: Deploy to Their Own Vercel (Optional)
Users can deploy to their own Vercel account (free tier) if they want:
```bash
vercel deploy
```

---

## When Backend Becomes Necessary

### Not Needed for MVP:
- ❌ API key security (users manage their own)
- ❌ Rate limiting (single user per instance)
- ❌ Multi-user support (not in MVP)

### Optional Post-MVP:
- ⚠️ **Debate sharing** - If users want shareable links → Add PostgreSQL + API routes
- ⚠️ **CORS workaround** - If provider blocks browser → Add lightweight proxy (10 lines per provider)
- ⚠️ **Hosted version** - If you decide to offer hosting → Then implement original serverless architecture

---

## Updated File Structure

```
quorum/
├── app/                    # Next.js 15 App Router
│   ├── page.tsx            # Main debate interface
│   ├── settings/
│   │   └── page.tsx        # API key management UI
│   └── layout.tsx
├── components/
│   ├── debate/             # Debate UI components
│   ├── settings/           # Settings UI
│   └── providers/          # React context providers
├── lib/
│   ├── llm/                # LLM client abstractions
│   │   ├── anthropic.ts    # Anthropic client
│   │   ├── openai.ts       # OpenAI client
│   │   └── google.ts       # Google client
│   ├── state/              # XState machines
│   └── storage/            # localStorage/IndexedDB utils
├── .env.local              # User's API keys (gitignored)
├── .env.example            # Template for users
├── README.md               # Setup instructions
└── docker-compose.yml      # Optional Docker setup
```

---

## README.md Example

```markdown
# Quorum - Multi-LLM Debate Platform

Open-source platform for structured AI debates.

## Quick Start

1. Clone and install:
   ```bash
   git clone https://github.com/you/quorum.git
   cd quorum
   npm install
   ```

2. Add your API keys:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your keys
   ```

3. Run locally:
   ```bash
   npm run dev
   # Open http://localhost:3000
   ```

## Get API Keys

- [Anthropic (Claude)](https://console.anthropic.com/)
- [OpenAI (GPT)](https://platform.openai.com/api-keys)
- [Google (Gemini)](https://makersuite.google.com/app/apikey)

## Deployment

### Docker
```bash
docker-compose up
```

### Your own Vercel
```bash
vercel deploy
```

Your API keys, your usage, your control!
```

---

## Summary of Changes

| Aspect | Before (Hosted) | After (Local-First) |
|--------|----------------|---------------------|
| **Backend** | Vercel Edge Functions | None needed |
| **API Keys** | Server env vars | .env.local or localStorage |
| **Streaming** | Proxy via backend | Direct from browser |
| **Rate Limiting** | Redis coordination | Client-side only |
| **Costs for You** | $$$  hosting fees | $0 |
| **Costs for Users** | You pay | They pay (their own API usage) |
| **Complexity** | High (backend + frontend) | Low (frontend only) |
| **Privacy** | Data goes through your server | Stays on user's machine |
| **MVP Timeline** | 9 weeks | **7 weeks** (no backend phases) |

---

## Action Items

1. ✅ Architecture revised (this document)
2. **Remove Vercel Edge Functions from all docs**
3. **Update README with local-first setup**
4. **Create .env.example template**
5. **Implement settings UI for API keys**
6. **Use official LLM SDKs with `dangerouslyAllowBrowser: true`**
7. **Add Docker setup for easy deployment**

---

## Bottom Line

**Your original instinct was correct!** For an open-source, clone-and-run project:
- No backend needed for MVP
- Users manage their own API keys
- Everyone pays for their own usage
- Much simpler architecture
- Faster development
- Zero hosting costs

The Hive Mind's research on **Next.js + React** is still 100% valid - we just simplified the deployment model.

---

**Status:** ✅ Architecture revised for local-first deployment
**Next Step:** Update documentation and begin implementation
