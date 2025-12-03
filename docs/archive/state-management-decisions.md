# Quorum State Management - Decision Matrices and Trade-offs

## Overview

This document provides detailed trade-off analysis for key architectural decisions in Quorum's state management system. Use this to understand why specific technologies and patterns were chosen.

---

## 1. State Management Library Selection

### Detailed Comparison

| Criteria | Zustand | Jotai | Redux Toolkit | XState | Valtio | Context API |
|----------|---------|-------|---------------|--------|--------|-------------|
| **Bundle Size** | 1.2kb ★★★★★ | 2.9kb ★★★★☆ | 11kb ★★☆☆☆ | 18kb ★★☆☆☆ | 3.5kb ★★★★☆ | 0kb ★★★★★ |
| **Learning Curve** | Low ★★★★★ | Medium ★★★☆☆ | High ★★☆☆☆ | High ★★☆☆☆ | Low ★★★★★ | Low ★★★★★ |
| **TypeScript Support** | Excellent ★★★★★ | Excellent ★★★★★ | Good ★★★★☆ | Excellent ★★★★★ | Good ★★★★☆ | Fair ★★★☆☆ |
| **DevTools** | Good ★★★★☆ | Good ★★★★☆ | Excellent ★★★★★ | Excellent ★★★★★ | Fair ★★★☆☆ | None ★☆☆☆☆ |
| **Boilerplate** | Minimal ★★★★★ | Minimal ★★★★★ | Medium ★★★☆☆ | Medium ★★★☆☆ | Minimal ★★★★★ | Minimal ★★★★★ |
| **Performance** | Excellent ★★★★★ | Excellent ★★★★★ | Good ★★★★☆ | Good ★★★★☆ | Excellent ★★★★★ | Poor ★★☆☆☆ |
| **Middleware** | Good ★★★★☆ | Limited ★★☆☆☆ | Excellent ★★★★★ | Good ★★★★☆ | Limited ★★☆☆☆ | None ★☆☆☆☆ |
| **Persistence** | Built-in ★★★★★ | External ★★★☆☆ | Built-in ★★★★★ | External ★★★☆☆ | External ★★★☆☆ | Manual ★★☆☆☆ |
| **Streaming Support** | Good ★★★★☆ | Excellent ★★★★★ | Good ★★★★☆ | Excellent ★★★★★ | Good ★★★★☆ | Fair ★★★☆☆ |
| **Community Size** | Large ★★★★★ | Growing ★★★☆☆ | Very Large ★★★★★ | Large ★★★★☆ | Medium ★★★☆☆ | Huge ★★★★★ |
| **Testing** | Simple ★★★★★ | Simple ★★★★★ | Complex ★★★☆☆ | Excellent ★★★★★ | Simple ★★★★★ | Complex ★★☆☆☆ |
| **Documentation** | Excellent ★★★★★ | Good ★★★★☆ | Excellent ★★★★★ | Excellent ★★★★★ | Good ★★★★☆ | Good ★★★★☆ |
| **State Machines** | Manual ★★☆☆☆ | Manual ★★☆☆☆ | Manual ★★☆☆☆ | Native ★★★★★ | Manual ★★☆☆☆ | Manual ★★☆☆☆ |

### Final Score (weighted)

1. **Zustand**: 4.5/5 - Best overall for general state
2. **XState**: 4.2/5 - Best for lifecycle management
3. **Jotai**: 4.0/5 - Excellent but overkill for this use case
4. **Redux Toolkit**: 3.7/5 - Too much boilerplate
5. **Valtio**: 3.8/5 - Good but smaller ecosystem
6. **Context API**: 2.5/5 - Poor performance, no devtools

### Recommendation Rationale

**Winner: Zustand + XState Hybrid**

**Why Zustand for global state:**
- Minimal API surface area (easy for open-source contributors)
- Excellent TypeScript inference
- No provider boilerplate
- Built-in persistence and devtools
- Small bundle size (critical for client-side app)
- Battle-tested in production

**Why XState for lifecycle:**
- Complex state transitions (7+ states)
- Guards and actions for validation
- Visualizable state charts (great for documentation)
- Built-in async orchestration
- Predictable error handling
- Testability (state machine tests are deterministic)

**Why NOT others:**
- **Jotai**: Atomic approach excellent but adds complexity for this use case
- **Redux Toolkit**: Too much boilerplate scares away contributors
- **Valtio**: Proxy-based reactivity is clever but less familiar
- **Context API**: Performance issues with frequent updates

---

## 2. Streaming State Management

### Options Comparison

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **React Query** | • Built-in retry logic<br>• Request deduplication<br>• Cache management<br>• Large ecosystem | • Additional dependency<br>• Learning curve<br>• Some overhead | ★★★★★ RECOMMENDED |
| **SWR** | • Very simple API<br>• Small size<br>• Good caching | • Less feature-rich<br>• Smaller ecosystem<br>• Limited retry config | ★★★★☆ Good alternative |
| **Custom Hooks** | • Full control<br>• No dependencies<br>• Minimal overhead | • Reinventing the wheel<br>• Manual retry logic<br>• No built-in cache | ★★☆☆☆ Too much work |
| **Apollo Client** | • Excellent devtools<br>• Normalized cache<br>• Subscriptions | • GraphQL-focused<br>• Large bundle<br>• Overkill | ★★☆☆☆ Not suitable |
| **RTK Query** | • Redux integration<br>• Code generation<br>• Strong types | • Requires Redux<br>• Complex setup<br>• Large bundle | ★★★☆☆ If using Redux |

### Decision: React Query

**Reasons:**
1. **Retry Logic**: Exponential backoff out of the box (critical for streaming failures)
2. **Request Management**: Automatic deduplication prevents duplicate streams
3. **Optimistic Updates**: Built-in pattern for responsive UI
4. **DevTools**: Excellent visibility into request state
5. **Community**: Large ecosystem with SSE/WebSocket patterns
6. **Bundle Size**: Reasonable at 13kb (worth it for features)

**Implementation Pattern:**
```typescript
const { mutate } = useMutation({
  mutationFn: streamResponse,
  retry: 3,
  retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
  onSuccess: (data) => finalizeResponse(data),
  onError: (error) => handleStreamError(error),
});
```

---

## 3. Persistence Strategy

### Storage Options

| Storage Type | Capacity | Performance | Persistence | Use Case |
|--------------|----------|-------------|-------------|----------|
| **IndexedDB** | ~50MB-1GB | Fast reads | Yes | Large debates, search |
| **LocalStorage** | ~5-10MB | Very fast | Yes | User prefs, API keys |
| **SessionStorage** | ~5-10MB | Very fast | Session only | Temp API keys |
| **In-Memory** | Unlimited | Instant | No | Active debate state |
| **Cache API** | ~50MB | Fast | Yes | Response caching |

### Recommendation: Hybrid Approach

```
┌─────────────────────────────────────────────────┐
│           Persistence Strategy                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  IndexedDB:                                     │
│  ✓ Debate history (full conversations)         │
│  ✓ Search index for debates                    │
│  ✓ Large response content                      │
│  ✓ Timeline events                              │
│                                                 │
│  LocalStorage:                                  │
│  ✓ User preferences (theme, defaults)          │
│  ✓ API keys (encrypted, persistent mode)       │
│  ✓ Last active debate ID                       │
│  ✓ UI state (panel positions)                  │
│                                                 │
│  SessionStorage:                                │
│  ✓ API keys (session-only mode)                │
│  ✓ Temporary debate drafts                     │
│                                                 │
│  Zustand Store (in-memory):                     │
│  ✓ Active debate state                         │
│  ✓ Streaming responses                         │
│  ✓ UI notifications                             │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Rationale:**
- **IndexedDB** for debates: Structured queries, large capacity
- **LocalStorage** for prefs: Simple key-value, fast access
- **SessionStorage** for security: Auto-clear on close
- **Memory** for active state: Fastest access, managed by Zustand

**Migration Path:**
```typescript
// Check storage version and migrate if needed
const STORAGE_VERSION = 1;

async function migrateStorage() {
  const version = localStorage.getItem('storage_version');

  if (!version || parseInt(version) < STORAGE_VERSION) {
    // Perform migration
    await migrateFromV0ToV1();
    localStorage.setItem('storage_version', STORAGE_VERSION.toString());
  }
}
```

---

## 4. Error Handling Strategy

### Error Classification

| Error Type | Retryable? | Max Retries | Backoff | User Action Required |
|------------|-----------|-------------|---------|---------------------|
| **Network Error** | ✓ Yes | 3 | Exponential | Wait/Retry |
| **Rate Limit** | ✓ Yes | 5 | Long delay (60s) | Wait/Upgrade plan |
| **API Error (4xx)** | ✓ Sometimes | 2 | Linear | Check request |
| **API Error (5xx)** | ✓ Yes | 3 | Exponential | Wait/Retry |
| **Auth Error** | ✗ No | 0 | N/A | Update API key |
| **Context Overflow** | ✗ No | 0 | N/A | Summarize/End |
| **Timeout** | ✓ Yes | 2 | Linear | Wait/Retry |
| **Parse Error** | ✗ No | 0 | N/A | Report bug |

### Recovery Strategies

```typescript
const ERROR_HANDLERS = {
  'network': async (error, context) => {
    // Exponential backoff retry
    await delay(Math.min(1000 * 2 ** context.retryCount, 30000));
    return { action: 'retry' };
  },

  'rate-limit': async (error, context) => {
    // Extract retry-after header or default to 60s
    const retryAfter = error.headers?.['retry-after'] || 60;
    await delay(retryAfter * 1000);
    return { action: 'retry' };
  },

  'authentication': async (error, context) => {
    // Cannot retry, need user action
    return {
      action: 'require-user-input',
      message: 'API key invalid. Please update in settings.',
      recoveryOptions: ['update-api-key', 'remove-provider'],
    };
  },

  'context-overflow': async (error, context) => {
    // Offer summarization or end debate
    return {
      action: 'require-user-choice',
      message: 'Conversation too long for model context.',
      options: [
        { label: 'Summarize earlier messages', action: 'summarize' },
        { label: 'End debate now', action: 'end-debate' },
      ],
    };
  },
};
```

### Circuit Breaker Thresholds

| Provider | Failure Threshold | Timeout | Half-Open Attempts |
|----------|------------------|---------|-------------------|
| Anthropic | 5 failures | 60s | 1 |
| OpenAI | 5 failures | 60s | 1 |
| Google | 5 failures | 60s | 1 |
| Mistral | 5 failures | 60s | 1 |

**Circuit Breaker States:**
```
CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing) → CLOSED
     ↓                                    ↓
  5 failures                         1 success
```

---

## 5. Performance Optimization Decisions

### Re-render Optimization

| Technique | Use Case | Impact | Complexity |
|-----------|----------|--------|-----------|
| **React.memo** | Expensive components | High | Low |
| **useMemo** | Heavy computations | High | Low |
| **useCallback** | Callback props | Medium | Low |
| **Shallow selectors** | Object/array state | High | Low |
| **Virtual scrolling** | Long lists (1000+) | Very High | Medium |
| **Debouncing** | Rapid state updates | High | Low |
| **Code splitting** | Route-based | Medium | Low |
| **Web Workers** | Heavy processing | Very High | High |

### Recommended Optimizations (Priority Order)

1. **Shallow Selectors** (Immediate)
   ```typescript
   useStore(state => state.participants, shallow)
   ```
   Impact: 30-50% fewer re-renders

2. **React.memo for Cards** (Immediate)
   ```typescript
   export const ParticipantCard = React.memo(...)
   ```
   Impact: 60-80% fewer re-renders for unchanged cards

3. **Virtual Scrolling** (Phase 2)
   ```typescript
   import { useVirtualizer } from '@tanstack/react-virtual'
   ```
   Impact: 90%+ improvement for 100+ messages

4. **Debounce Streaming** (Phase 1)
   ```typescript
   useDebouncedCallback(addChunk, 50)
   ```
   Impact: 50-70% fewer state updates

5. **Code Splitting** (Phase 3)
   ```typescript
   const DebateHistory = lazy(() => import('./DebateHistory'))
   ```
   Impact: 20-30% faster initial load

### Performance Budgets

```
┌──────────────────────────────────────────┐
│         Performance Targets              │
├──────────────────────────────────────────┤
│ Initial Load: < 3s (3G connection)       │
│ Time to Interactive: < 5s                │
│ Stream Chunk Render: < 16ms (60fps)      │
│ State Update: < 100ms                    │
│ Bundle Size: < 500kb gzipped             │
│ Memory Usage: < 100MB (active debate)    │
│ Database Ops: < 50ms (IndexedDB)         │
└──────────────────────────────────────────┘
```

---

## 6. Security Considerations

### API Key Storage

| Method | Security Level | User Friction | Recommendation |
|--------|---------------|---------------|----------------|
| **Encrypted LocalStorage** | Medium | Low | ★★★★☆ RECOMMENDED for MVP |
| **SessionStorage only** | Medium-High | Medium | ★★★★☆ Option for shared PCs |
| **No persistence** | High | High | ★★☆☆☆ Too inconvenient |
| **Backend storage** | Very High | Medium | ★★★★★ Post-MVP |
| **Browser keychain** | High | Low | ★★★☆☆ Limited browser support |

### Chosen Approach: Encrypted LocalStorage

**Implementation:**
```typescript
// Encryption key derived from device fingerprint
const encryptionKey = sha256(deviceFingerprint);

// Store encrypted
const encrypted = AES.encrypt(apiKey, encryptionKey);
localStorage.setItem('api_key_anthropic', encrypted);

// Retrieve and decrypt
const encrypted = localStorage.getItem('api_key_anthropic');
const decrypted = AES.decrypt(encrypted, encryptionKey);
```

**Security Measures:**
1. AES-256 encryption
2. Device-specific key (not transferable)
3. Never log or expose keys
4. Clear disclaimers in UI
5. Option for session-only mode
6. HTTPS-only API calls
7. Content Security Policy headers

**Disclaimers Shown to Users:**
```
⚠️ API Key Security Notice:
• Keys stored encrypted on your device
• Not 100% secure (browser storage limitations)
• Use session-only mode on shared computers
• Revoke keys after use in provider dashboard
• Monitor API usage for unexpected activity
```

---

## 7. Scalability Considerations

### Debate Size Limits

| Scenario | Participants | Rounds | Messages | Tokens | Storage |
|----------|-------------|--------|----------|--------|---------|
| **Small** | 2 | 3 | 6-12 | 10k | 50KB |
| **Medium** | 3 | 5 | 15-30 | 30k | 150KB |
| **Large** | 4 | 10 | 40-80 | 80k | 500KB |
| **Very Large** | 4 | 20 | 80-160 | 150k | 1MB |

### Context Window Management

| Model | Context Limit | Reserve for Prompt | Available for History |
|-------|--------------|-------------------|---------------------|
| Claude 3.5 Sonnet | 200k tokens | 5k | 195k |
| GPT-4 Turbo | 128k tokens | 5k | 123k |
| Gemini Pro | 32k tokens | 5k | 27k |
| Mistral Large | 32k tokens | 5k | 27k |

**Strategy:**
- Use 80% of available context for history
- Summarize when approaching limit
- Warn user at 70% capacity
- Auto-summarize at 80% capacity
- Block new rounds at 95% capacity

### Rate Limit Handling

| Provider | RPM Limit | TPM Limit | Strategy |
|----------|-----------|-----------|----------|
| Anthropic (Free) | 5 | 10,000 | Queue + Warn |
| Anthropic (Paid) | 50 | 100,000 | Queue |
| OpenAI (Tier 1) | 3 | 40,000 | Queue + Warn |
| OpenAI (Tier 5) | 10,000 | 10,000,000 | Rarely hit |

**Queue Configuration:**
```typescript
const queueConfig = {
  concurrency: Math.min(provider.rpm / 10, 5),
  interval: 60000, // 1 minute
  intervalCap: provider.rpm,
};
```

---

## 8. Testing Strategy

### Coverage Targets

| Layer | Coverage Target | Priority | Tools |
|-------|----------------|----------|-------|
| **Store Logic** | > 90% | Critical | Vitest |
| **State Machine** | 100% | Critical | XState Test Utils |
| **Hooks** | > 85% | High | React Testing Library |
| **Components** | > 70% | Medium | React Testing Library |
| **Services** | > 80% | High | Vitest + MSW |
| **Integration** | Critical paths | High | Playwright |
| **E2E** | Happy paths | Medium | Playwright |

### Test Pyramid

```
        ┌─────────┐
        │   E2E   │ 10% - Critical user flows
        ├─────────┤
        │ Integration│ 20% - Feature integration
        ├─────────────┤
        │  Component  │ 30% - UI components
        ├─────────────────┤
        │  Unit + Hooks   │ 40% - Logic and state
        └─────────────────┘
```

### Testing Tools Decision

| Tool | Use Case | Why Chosen |
|------|----------|-----------|
| **Vitest** | Unit tests | Fast, ESM support, Vite integration |
| **React Testing Library** | Component tests | Best practices, user-centric |
| **MSW** | API mocking | Realistic mocking, network level |
| **Playwright** | E2E tests | Cross-browser, reliable, fast |
| **XState Inspect** | State machine | Visual debugging, test generation |

---

## 9. Developer Experience

### Onboarding Complexity

| Approach | Learning Curve | Setup Time | Contributor Friendly |
|----------|---------------|-----------|---------------------|
| **Zustand + XState** | Medium ★★★☆☆ | 1-2 hours | ★★★★☆ Good |
| **Redux Toolkit** | High ★★☆☆☆ | 3-4 hours | ★★★☆☆ Moderate |
| **Jotai** | Medium ★★★☆☆ | 1-2 hours | ★★★☆☆ Moderate |
| **Context API** | Low ★★★★☆ | 30 min | ★★★★★ Excellent |
| **Custom Solution** | Very High ★☆☆☆☆ | 8+ hours | ★☆☆☆☆ Poor |

### Documentation Requirements

```
Required Documentation:
├── README.md (Quick Start)
├── state-management-specification.md (Architecture)
├── state-architecture-diagrams.md (Visual guides)
├── state-implementation-guide.md (Code examples)
├── API.md (Hook/store reference)
├── CONTRIBUTING.md (How to add features)
└── TESTING.md (Test guidelines)
```

### DevTools Setup

```typescript
// Enable Redux DevTools for Zustand
import { devtools } from 'zustand/middleware';

const useStore = create(
  devtools((set) => ({
    // store logic
  }), {
    name: 'Quorum Store',
    enabled: process.env.NODE_ENV === 'development',
  })
);

// Enable XState Inspector
import { inspect } from '@xstate/inspect';

if (process.env.NODE_ENV === 'development') {
  inspect({
    iframe: false, // Open in separate window
  });
}
```

---

## 10. Migration and Maintenance

### Schema Versioning

```typescript
interface PersistedState {
  version: number;
  data: any;
  migratedAt?: number;
}

const MIGRATIONS = {
  1: (oldState: any) => {
    // V0 -> V1: Add tokenUsage to participants
    return {
      ...oldState,
      debates: Object.fromEntries(
        Object.entries(oldState.debates).map(([id, debate]) => [
          id,
          {
            ...debate,
            participants: Object.fromEntries(
              Object.entries(debate.participants).map(([pid, p]) => [
                pid,
                { ...p, tokenUsage: { ... } },
              ])
            ),
          },
        ])
      ),
    };
  },
  2: (oldState: any) => {
    // V1 -> V2: Future migration
  },
};
```

### Deprecation Strategy

```typescript
// Phase out old API
/**
 * @deprecated Use useStreamingContent instead
 * Will be removed in v2.0.0
 */
export const useCurrentResponse = (id: string) => {
  console.warn('useCurrentResponse is deprecated. Use useStreamingContent.');
  return useStreamingContent(id);
};
```

---

## Decision Summary

### Final Architecture

```
State Management: Zustand (global) + XState (lifecycle)
Streaming: React Query
Persistence: IndexedDB (debates) + LocalStorage (prefs)
Security: AES-256 encrypted storage with disclaimers
Performance: Shallow selectors + React.memo + virtual scrolling
Testing: Vitest + RTL + Playwright
DevTools: Redux DevTools + XState Inspector
```

### Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Context overflow** | High | High | Auto-summarization, user warnings |
| **Rate limiting** | Medium | High | Queue system, circuit breaker |
| **API key theft** | Low | Critical | Encryption, disclaimers, session mode |
| **State corruption** | Low | Medium | Schema versioning, validation |
| **Performance degradation** | Medium | Medium | Virtual scrolling, memoization |
| **Browser compatibility** | Low | Low | Polyfills, feature detection |

### Success Metrics

```
✓ Initial load < 3s
✓ Stream chunk render < 16ms
✓ Test coverage > 80%
✓ Bundle size < 500kb
✓ Zero critical security issues
✓ < 5% error rate in production
✓ Contributor onboarding < 2 hours
```

This architecture balances developer experience, performance, security, and maintainability for an open-source project.
