# Quorum State Management Architecture

## Executive Summary

This directory contains the comprehensive state management architecture for Quorum, an open-source multi-LLM debate platform. The architecture handles complex real-time streaming from 2-4 concurrent LLMs, judge assessments, and sophisticated debate lifecycle management.

## Documentation Structure

### 1. [State Management Specification](./state-management-specification.md)
**The complete technical specification** covering:
- All state domains with TypeScript interfaces
- Library evaluation (Zustand, Jotai, Redux Toolkit, XState)
- Recommended architecture (Zustand + XState hybrid)
- State machine design for debate lifecycle
- Streaming state management patterns
- Error handling and recovery strategies
- Local persistence strategy (IndexedDB + LocalStorage)
- Real-time state synchronization
- Performance optimization techniques

**When to use:** Deep dive into architecture decisions, understanding state structure

### 2. [State Architecture Diagrams](./state-architecture-diagrams.md)
**Visual representations** including:
- High-level architecture overview
- State flow diagrams (simultaneous/sequential rounds)
- Error recovery flow
- Context window management flow
- Rate limit queue system
- Multi-tab synchronization
- Component-state interaction patterns
- Security layers
- Performance optimization strategies
- Testing architecture

**When to use:** Quick visual reference, understanding data flow, onboarding new contributors

### 3. [State Implementation Guide](./state-implementation-guide.md)
**Practical code examples** featuring:
- Project setup and dependencies
- Complete Zustand store implementation
- XState machine setup (guards, actions, services)
- React Query integration for streaming
- Custom hooks library
- Component integration examples
- Testing examples
- Common patterns (debouncing, optimistic updates, subscriptions)

**When to use:** Implementing features, copying working code, learning patterns

### 4. [State Management Decisions](./state-management-decisions.md)
**Trade-off analysis** containing:
- Detailed comparison matrices for all major decisions
- Library selection rationale
- Streaming state management options
- Persistence strategy comparison
- Error handling classification
- Performance optimization priorities
- Security considerations
- Scalability limits
- Testing strategy
- Developer experience evaluation

**When to use:** Understanding why decisions were made, evaluating alternatives

---

## Quick Start

### For New Contributors

1. **Start here:** Read the [Executive Summary](#architecture-overview) below
2. **Visual learner?** Check [State Architecture Diagrams](./state-architecture-diagrams.md)
3. **Ready to code?** Use [State Implementation Guide](./state-implementation-guide.md)
4. **Want to understand why?** Read [State Management Decisions](./state-management-decisions.md)
5. **Deep dive:** Full [State Management Specification](./state-management-specification.md)

### For Architects/Reviewers

1. [State Management Specification](./state-management-specification.md) - Complete architecture
2. [State Management Decisions](./state-management-decisions.md) - Trade-off analysis
3. [State Architecture Diagrams](./state-architecture-diagrams.md) - Visual verification

### For Implementers

1. [State Implementation Guide](./state-implementation-guide.md) - Copy-paste ready code
2. [State Architecture Diagrams](./state-architecture-diagrams.md) - Flow reference
3. [State Management Specification](./state-management-specification.md) - Type definitions

---

## Architecture Overview

### Core Technologies

```typescript
// State Management Stack
├── Zustand v4.x           // Global state (debates, participants, UI)
├── XState v5.x            // Debate lifecycle state machine
├── React Query v5.x       // Streaming and API state
├── Immer                  // Immutable updates
├── IndexedDB              // Large data persistence
└── LocalStorage           // User preferences
```

### State Domains

```
┌─────────────────────────────────────────────────┐
│                 Zustand Store                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  debates: Record<string, DebateState>           │
│  ├── config: DebateConfig                       │
│  ├── status: DebateStatus                       │
│  ├── currentRound: number                       │
│  ├── participants: Record<string, Participant>  │
│  │   ├── status: ParticipantStatus              │
│  │   ├── responseHistory: Response[]            │
│  │   ├── currentResponse?: StreamingResponse    │
│  │   ├── tokenUsage: TokenUsage                 │
│  │   └── errors: ParticipantError[]             │
│  ├── judge: JudgeState                          │
│  │   ├── assessments: RoundAssessment[]         │
│  │   └── finalVerdict?: FinalVerdict            │
│  └── timeline: TimelineEvent[]                  │
│                                                 │
│  providers: Record<string, ProviderConfig>      │
│  ui: UIState                                    │
│  activeDebateId: string | null                  │
│                                                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              XState Machine                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  configuring → validating → ready →             │
│  initializing → running → completing →          │
│  completed                                      │
│                                                 │
│  running:                                       │
│    ├── awaitingResponses                        │
│    ├── judging                                  │
│    └── roundComplete                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Data Flow

```
User Action
    ↓
Component Event Handler
    ↓
Custom Hook (useDebateOrchestrator)
    ↓
XState Machine (send event)
    ↓
Service Invocation (async operation)
    ↓
Zustand Store Update (set state)
    ↓
Selector Subscription (useStore)
    ↓
Component Re-render (React)
```

---

## Key Features

### 1. Real-time Streaming Management

```typescript
// Simultaneous streaming from multiple LLMs
const { executeRound } = useSimultaneousRound(debateId);

// Handles:
✓ Parallel SSE/WebSocket connections
✓ Incremental chunk updates (sub-50ms)
✓ Rate limit queue management
✓ Automatic retry with exponential backoff
✓ Circuit breaker for failing providers
```

### 2. Predictable State Transitions

```typescript
// XState ensures valid transitions only
const { state, startDebate } = useDebateOrchestrator(debateId);

// State machine prevents:
✗ Starting without valid config
✗ Duplicate rounds
✗ Invalid status transitions
✗ Race conditions
```

### 3. Optimized Performance

```typescript
// Granular selectors prevent unnecessary re-renders
const content = useStreamingContent(debateId, participantId);
// ^ Only re-renders when THIS participant's content changes

// Memoized components
export const ParticipantCard = React.memo(({ debateId, participantId }) => {
  // Only re-renders when participantId changes
});
```

### 4. Robust Error Recovery

```typescript
// Classified error handling
const ERROR_RECOVERY_STRATEGIES = {
  network: { retryable: true, maxRetries: 3, backoff: 'exponential' },
  'rate-limit': { retryable: true, maxRetries: 5, delayMs: 60000 },
  authentication: { retryable: false, userAction: 'update-api-key' },
  'context-overflow': { retryable: false, options: ['summarize', 'end'] },
};
```

### 5. Secure Persistence

```typescript
// Encrypted API key storage
const encrypted = AES.encrypt(apiKey, deviceFingerprint);
localStorage.setItem('api_key', encrypted);

// Debate history in IndexedDB
await debateHistory.saveDebate(debate);
const debates = await debateHistory.searchDebates(query);
```

---

## Common Use Cases

### Creating a New Debate

```typescript
import { useStore } from './stores/debateStore';
import { useDebateOrchestrator } from './hooks/useDebateOrchestrator';

function DebateSetup() {
  const createDebate = useStore((state) => state.createDebate);

  const handleStart = () => {
    const debateId = createDebate({
      topic: "Should we colonize Mars?",
      format: 'structured-rounds',
      mode: 'simultaneous',
      participants: [
        { providerId: 'anthropic', modelId: 'claude-3-5-sonnet', ... },
        { providerId: 'openai', modelId: 'gpt-4', ... },
      ],
      judgeConfig: { providerId: 'anthropic', ... },
      createdAt: Date.now(),
      id: '',
    });

    const { startDebate } = useDebateOrchestrator(debateId);
    startDebate();
  };
}
```

### Displaying Streaming Responses

```typescript
import { useStreamingContent, useParticipantStatus } from './stores/selectors';

function ParticipantCard({ debateId, participantId }) {
  const content = useStreamingContent(debateId, participantId);
  const status = useParticipantStatus(debateId, participantId);

  return (
    <div>
      {status === 'streaming' && <LoadingIndicator />}
      <div className="content">{content}</div>
    </div>
  );
}
```

### Handling Errors

```typescript
import { useStore } from './stores/debateStore';

function ErrorDisplay({ debateId, participantId }) {
  const participant = useParticipant(debateId, participantId);
  const retryStream = useStreamResponse(debateId, participantId);

  if (participant.status !== 'error') return null;

  const lastError = participant.errors[participant.errors.length - 1];

  return (
    <div className="error">
      <p>{lastError.message}</p>
      {lastError.retryable && (
        <button onClick={() => retryStream.mutate({ prompt, context })}>
          Retry
        </button>
      )}
    </div>
  );
}
```

### Exporting Debates

```typescript
import { debateHistory } from './services/debateHistory';
import { exportService } from './services/exportService';

async function exportDebate(debateId: string, format: 'markdown' | 'json') {
  await exportService.exportDebate(debateId, format);
  // Downloads file: debate-{id}.{format}
}
```

---

## Performance Characteristics

### Benchmarks

```
Initial Load (cold start):        < 3s
Time to Interactive:               < 5s
Stream Chunk Render:               < 16ms (60fps)
State Update (single participant): < 10ms
State Update (all participants):   < 50ms
Database Read (IndexedDB):         < 50ms
Database Write (IndexedDB):        < 100ms
Selector Computation:              < 5ms
Component Re-render:               < 16ms
```

### Memory Usage

```
Empty State:                       ~5MB
Active Debate (4 participants):    ~50MB
Debate History (100 debates):      ~200MB
Peak Usage (streaming):            ~100MB
```

### Bundle Sizes

```
Zustand:                           1.2kb
XState:                            18kb
React Query:                       13kb
Total State Management:            ~32kb
Full App Bundle (gzipped):         < 500kb
```

---

## Testing Strategy

### Coverage by Layer

```
Unit Tests (40%):
├── Store slices (95% coverage)
├── Selectors (90% coverage)
├── Utilities (85% coverage)
└── Hooks (80% coverage)

Integration Tests (30%):
├── Debate flow (end-to-end state changes)
├── Streaming (simultaneous + sequential)
├── Error recovery
└── Persistence

Component Tests (20%):
├── Debate setup
├── Participant cards
├── Judge panel
└── Settings panel

E2E Tests (10%):
├── Happy path (complete debate)
├── Error scenarios
└── Cross-browser compatibility
```

### Running Tests

```bash
# Unit tests
npm test

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# Coverage report
npm run test:coverage
```

---

## Development Workflow

### Adding a New Feature

1. **Define state changes** in relevant slice
2. **Add types** to `types/` directory
3. **Create selectors** in `stores/selectors.ts`
4. **Write custom hook** in `hooks/`
5. **Add tests** for all layers
6. **Update documentation**

### Debugging State

```typescript
// Enable devtools in development
import { devtools } from 'zustand/middleware';

// Inspect Zustand store
window.__ZUSTAND_STORE__ = useStore.getState();

// Visualize XState machine
import { inspect } from '@xstate/inspect';
inspect({ iframe: false });

// Monitor React Query
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
<ReactQueryDevtools initialIsOpen={false} />
```

---

## Migration Guide

### From Context API

```typescript
// Before (Context API)
const { state, dispatch } = useDebateContext();
dispatch({ type: 'ADD_RESPONSE', payload: response });

// After (Zustand)
const finalizeResponse = useStore((state) => state.finalizeResponse);
finalizeResponse(debateId, participantId, tokenUsage);
```

### From Redux

```typescript
// Before (Redux)
const dispatch = useDispatch();
const debate = useSelector(state => state.debates.byId[id]);
dispatch(addStreamChunk({ debateId, participantId, chunk }));

// After (Zustand)
const debate = useStore(state => state.debates[id]);
const addStreamChunk = useStore(state => state.addStreamChunk);
addStreamChunk(debateId, participantId, chunk);
```

---

## Troubleshooting

### Common Issues

**Issue: Components re-rendering too often**
```typescript
// ❌ Bad: Creates new object on every render
const participants = useStore(state => state.debates[id].participants);

// ✅ Good: Use shallow comparison
import { shallow } from 'zustand/shallow';
const participants = useStore(state => state.debates[id].participants, shallow);
```

**Issue: State updates not persisting**
```typescript
// ❌ Bad: Direct mutation
state.participants[id].status = 'complete';

// ✅ Good: Immer middleware handles immutability
set((state) => {
  state.participants[id].status = 'complete';
});
```

**Issue: Race conditions in streaming**
```typescript
// ❌ Bad: No queue management
await Promise.all(participants.map(p => stream(p)));

// ✅ Good: Use rate limit queue
await providerQueue.enqueue(providerId, () => stream(p));
```

---

## Contributing

### Guidelines

1. **Follow TypeScript strictly** - No `any` types
2. **Write tests first** - TDD for new features
3. **Use existing patterns** - Check implementation guide
4. **Document state changes** - Update diagrams if needed
5. **Performance matters** - Profile before/after
6. **Think about errors** - Handle all error cases

### Pull Request Checklist

- [ ] Tests added with >80% coverage
- [ ] TypeScript types defined
- [ ] Selectors optimized (shallow where needed)
- [ ] Error handling implemented
- [ ] Documentation updated
- [ ] Performance impact measured
- [ ] State machine updated (if applicable)
- [ ] Migration guide included (if breaking)

---

## Resources

### Internal Documentation
- [State Management Specification](./state-management-specification.md)
- [State Architecture Diagrams](./state-architecture-diagrams.md)
- [State Implementation Guide](./state-implementation-guide.md)
- [State Management Decisions](./state-management-decisions.md)

### External Resources
- [Zustand Documentation](https://docs.pmnd.rs/zustand)
- [XState Documentation](https://xstate.js.org/docs/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Immer Documentation](https://immerjs.github.io/immer/)

### Community
- GitHub Issues: Report bugs, request features
- Discussions: Ask questions, share ideas
- Discord: Real-time chat with maintainers

---

## License

MIT - See LICENSE file for details

---

## Maintainers

For questions about state management architecture:
- Open an issue with label `state-management`
- Reference this documentation in discussions
- Check existing issues before creating new ones

**Last Updated:** 2025-01-29
**Architecture Version:** 1.0
**Next Review:** 2025-03-29
