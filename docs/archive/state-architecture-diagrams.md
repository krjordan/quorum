# Quorum State Architecture Diagrams

## 1. High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          React Application                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  UI Components   │  │  Custom Hooks    │  │  Services       │  │
│  ├──────────────────┤  ├──────────────────┤  ├─────────────────┤  │
│  │ - DebateSetup    │  │ - useDebate      │  │ - API Clients   │  │
│  │ - StreamView     │  │ - useStream      │  │ - Streaming     │  │
│  │ - ParticipantCard│  │ - useJudge       │  │ - Context Mgmt  │  │
│  │ - JudgePanel     │  │ - useHistory     │  │ - Export        │  │
│  │ - SettingsPanel  │  │ - useProviders   │  │ - Encryption    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬────────┘  │
│           │                     │                      │           │
│           └─────────────────────┼──────────────────────┘           │
│                                 │                                  │
├─────────────────────────────────┼──────────────────────────────────┤
│                        State Management Layer                      │
├─────────────────────────────────┼──────────────────────────────────┤
│                                 │                                  │
│  ┌──────────────────────────────▼────────────────────────────────┐ │
│  │                      Zustand Store                            │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  Slices:                                                      │ │
│  │  • Debate State        (debates, activeDebateId)             │ │
│  │  • Participant State   (streaming, responses, tokens)        │ │
│  │  • Judge State         (assessments, verdict)                │ │
│  │  • Provider State      (API keys, validation)                │ │
│  │  • UI State           (views, modals, notifications)         │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  Middleware:                                                  │ │
│  │  • Immer           (immutable updates)                       │ │
│  │  • Persist         (localStorage/IndexedDB)                  │ │
│  │  • DevTools        (debugging)                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                 │                                  │
│  ┌──────────────────────────────▼────────────────────────────────┐ │
│  │                    XState State Machine                       │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  States:                                                      │ │
│  │  configuring → validating → ready → running →                │ │
│  │  completing → completed                                       │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  Guards:     hasValidConfig, shouldEndDebate, canContinue    │ │
│  │  Actions:    updateStream, finalizeResponse, handleError     │ │
│  │  Services:   validateConfig, streamResponses, getVerdict     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                 │                                  │
│  ┌──────────────────────────────▼────────────────────────────────┐ │
│  │                       React Query                             │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  • Stream Management   (SSE/WebSocket connections)           │ │
│  │  • Retry Logic         (exponential backoff)                 │ │
│  │  • Cache Management    (response caching)                    │ │
│  │  • Optimistic Updates  (UI responsiveness)                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                       Persistence Layer                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────┐  │
│  │   IndexedDB       │  │  LocalStorage     │  │  SessionStorage│  │
│  ├───────────────────┤  ├───────────────────┤  ├───────────────┤  │
│  │ - Debate History  │  │ - User Prefs      │  │ - Session Keys │  │
│  │ - Large State     │  │ - API Keys (enc)  │  │ - Temp Data    │  │
│  │ - Search Index    │  │ - Settings        │  └───────────────┘  │
│  └───────────────────┘  └───────────────────┘                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. State Flow Diagram - Simultaneous Round

```
User Starts Round
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Debate State Machine: running.awaitingResponses             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
      ┌────────────────────────────────────────┐
      │  Trigger Parallel Stream Mutations     │
      └────────┬───────────────────────────────┘
               │
     ┌─────────┴─────────┬─────────────┬─────────────┐
     │                   │             │             │
     ▼                   ▼             ▼             ▼
┌─────────┐        ┌─────────┐   ┌─────────┐   ┌─────────┐
│Participant│       │Participant│  │Participant│  │Participant│
│    1     │        │    2     │   │    3     │   │    4     │
│(Claude)  │        │  (GPT-4) │   │ (Gemini) │   │ (Mistral)│
└────┬────┘        └────┬─────┘   └────┬─────┘   └────┬─────┘
     │                   │              │              │
     │ Stream Chunks     │              │              │
     ├──────────────────►│              │              │
     │ RESPONSE_CHUNK    │              │              │
     │                   │              │              │
     │ ┌─────────────────▼──────────────▼──────────────▼─────┐
     │ │         Zustand: addStreamChunk                     │
     │ │  Updates currentResponse.content incrementally      │
     │ └──────────────────┬──────────────────────────────────┘
     │                    │
     │                    ▼
     │         ┌──────────────────────┐
     │         │  React Re-render     │
     │         │  (streaming visible) │
     │         └──────────────────────┘
     │
     ▼ Stream Complete
┌────────────────────────────────┐
│ RESPONSE_COMPLETE              │
│ Zustand: finalizeResponse      │
│ - Move to responseHistory      │
│ - Update tokenUsage            │
│ - Set status: 'complete'       │
└────────┬───────────────────────┘
         │
         │ (All participants complete)
         │
         ▼
┌────────────────────────────────────┐
│ XState: transition to 'judging'    │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Invoke Judge Assessment Service    │
│ - Build context from all responses │
│ - Stream judge analysis            │
└────────┬───────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Store Judge Assessment             │
│ Zustand: addJudgeAssessment        │
└────────┬───────────────────────────┘
         │
         ▼
    Should Continue?
         │
    ┌────┴─────┐
   YES         NO
    │           │
    ▼           ▼
Next Round   Complete Debate
```

## 3. Error Recovery Flow

```
Error Occurs
    │
    ▼
┌──────────────────────┐
│ Classify Error Type  │
└──────┬───────────────┘
       │
       ▼
Is Retryable?
       │
   ┌───┴───┐
  YES      NO
   │        │
   ▼        ▼
┌──────┐  ┌────────────────────┐
│Retry │  │ Show User Action   │
│Logic │  │ - Update API key   │
└──┬───┘  │ - End debate       │
   │      │ - Summarize context│
   │      └────────────────────┘
   ▼
Retry Count < Max?
   │
┌──┴──┐
│YES  │NO
│     │
▼     ▼
┌─────────────┐  ┌───────────────────┐
│ Exponential │  │ Final Failure     │
│ Backoff     │  │ - Store error     │
│ - Wait      │  │ - Update UI       │
│ - Retry     │  │ - Allow recovery  │
└─────────────┘  └───────────────────┘
     │
     ▼
   Success?
     │
 ┌───┴───┐
YES     NO
 │       │
 ▼       ▼
Resume   Circuit
Debate   Breaker
         Opens
```

## 4. Context Window Management

```
Build Context for Participant
           │
           ▼
┌─────────────────────────┐
│ Calculate Token Budget  │
│ - System prompt: 500    │
│ - Reserve: 20%          │
│ - Available: 80%        │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Gather Response History     │
│ (Reverse chronological)     │
└──────────┬──────────────────┘
           │
           ▼
For each Response (newest → oldest)
           │
           ▼
┌──────────────────────────────┐
│ Token Count Current Response │
└──────────┬───────────────────┘
           │
           ▼
Budget + This > 80% Limit?
           │
      ┌────┴────┐
     YES       NO
      │         │
      ▼         ▼
  ┌──────┐   ┌──────────────┐
  │ STOP │   │ Add to Context│
  │      │   │ Update Budget │
  └──────┘   └───────┬───────┘
                     │
                     └──────┐
                            │
                            ▼
                    More responses?
                            │
                        ┌───┴───┐
                       YES     NO
                        │       │
                        └───────┴──────┐
                                       ▼
                            Context > 80%?
                                       │
                                  ┌────┴────┐
                                 YES       NO
                                  │         │
                                  ▼         ▼
                          ┌──────────┐  ┌────────┐
                          │Summarize │  │ Return │
                          │Older Msgs│  │Context │
                          └────┬─────┘  └────────┘
                               │
                               ▼
                       ┌──────────────────┐
                       │ LLM Summarization│
                       │ (Async call)     │
                       └────┬─────────────┘
                            │
                            ▼
                   ┌───────────────────┐
                   │Replace old context│
                   │with summary       │
                   └────┬──────────────┘
                        │
                        ▼
                   Return Context
```

## 5. Rate Limit Queue System

```
API Request Triggered
         │
         ▼
┌──────────────────────────┐
│ Get Provider Queue       │
│ (Create if not exists)   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Queue Configuration:             │
│ - Concurrency: 5 max             │
│ - Interval: 60s                  │
│ - Interval Cap: RPM limit        │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Enqueue Request          │
└──────────┬───────────────┘
           │
           ▼
    Queue Available?
           │
      ┌────┴────┐
     YES       NO
      │         │
      ▼         ▼
┌──────────┐  ┌──────────────────┐
│ Execute  │  │ Wait in Queue    │
│Immediately│  │ - Show position  │
└────┬─────┘  │ - Est. time      │
     │        └────┬─────────────┘
     │             │
     │             ▼
     │      Queue slot opens
     │             │
     └─────────────┘
                   │
                   ▼
            Execute Request
                   │
              ┌────┴────┐
            Success   Failure
              │          │
              ▼          ▼
         Complete   ┌─────────────┐
                    │ Retry Logic │
                    │ (See Error  │
                    │  Recovery)  │
                    └─────────────┘
```

## 6. Data Flow - User Action to UI Update

```
User Action (e.g., "Start Debate")
           │
           ▼
┌─────────────────────────┐
│ Component Event Handler │
│ onClick={() => start()} │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────────┐
│ XState: send('START')       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ State Machine Evaluation    │
│ - Check guards              │
│ - Execute transition        │
│ - Invoke services           │
└──────────┬──────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Service: initializeDebate    │
│ - Auto-assign personas       │
│ - Setup participants         │
└──────────┬───────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Zustand: updateDebate          │
│ set((state) => {               │
│   state.debates[id] = newState │
│ })                             │
└──────────┬─────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Zustand Subscriptions Notified   │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ React Components Re-render       │
│ (Only those using changed slice) │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ UI Update Visible                │
│ - Status badge changes           │
│ - Streaming indicators appear    │
│ - Participant cards update       │
└──────────────────────────────────┘
```

## 7. Multi-Tab Synchronization

```
Tab A: User adds API key
           │
           ▼
┌─────────────────────────┐
│ Zustand: addProvider    │
└──────────┬──────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Store Subscription Triggered │
└──────────┬───────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Broadcast Channel: postMessage  │
│ { type: 'provider-added',       │
│   payload: providerData }       │
└──────────┬──────────────────────┘
           │
           ▼
      Browser IPC
    (BroadcastChannel)
           │
     ┌─────┴─────┬─────────┬──────────┐
     │           │         │          │
     ▼           ▼         ▼          ▼
  Tab B       Tab C     Tab D      Tab E
     │           │         │          │
     └───────────┴─────────┴──────────┘
                   │
                   ▼
┌──────────────────────────────────┐
│ channel.onmessage handler        │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Zustand: syncProvider            │
│ (Merge without triggering new   │
│  broadcast to avoid loops)       │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ UI Updates in All Tabs           │
└──────────────────────────────────┘
```

## 8. State Persistence Flow

```
State Change in Zustand
           │
           ▼
┌──────────────────────────┐
│ Persist Middleware       │
│ (Configured partialize)  │
└──────────┬───────────────┘
           │
           ▼
  Which slices to persist?
           │
     ┌─────┴─────┬─────────┬──────────┐
     │           │         │          │
     ▼           ▼         ▼          ▼
┌────────┐  ┌──────┐  ┌──────┐  ┌────────┐
│Debates │  │Prefs │  │Keys  │  │UI State│
│        │  │      │  │(enc) │  │(partial)│
└────┬───┘  └───┬──┘  └───┬──┘  └────┬───┘
     │          │         │          │
     └──────────┴─────────┴──────────┘
                   │
                   ▼
        ┌────────────────────┐
        │ Storage Adapter    │
        └──────┬─────────────┘
               │
          ┌────┴────┐
      IndexedDB   LocalStorage
          │            │
          ▼            ▼
    ┌──────────┐  ┌─────────┐
    │ Store    │  │ Store   │
    │ Large    │  │ Small   │
    │ Debates  │  │ Prefs   │
    └──────────┘  └─────────┘

On App Load
     │
     ▼
┌──────────────────────┐
│ Restore from Storage │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│ Merge with Initial State │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Hydrate Zustand Store    │
└──────────┬───────────────┘
           │
           ▼
     App Ready
```

## 9. Component-State Interaction Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    DebateView Component                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  const debate = useActiveDebate()                           │
│  const { startRound } = useDebateOrchestrator(debate.id)    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           Participant Cards                           │ │
│  │  ┌─────────────────────────────────────────────────┐  │ │
│  │  │  ParticipantCard (Memoized)                     │  │ │
│  │  │  ┌───────────────────────────────────────────┐  │  │ │
│  │  │  │ const participant = useStore(              │  │  │ │
│  │  │  │   state => state.debates[id].participants  │  │  │ │
│  │  │  │     [participantId]                        │  │  │ │
│  │  │  │ )                                          │  │  │ │
│  │  │  │                                            │  │  │ │
│  │  │  │ const content = useStreamingContent(       │  │  │ │
│  │  │  │   debateId, participantId                  │  │  │ │
│  │  │  │ )                                          │  │  │ │
│  │  │  │                                            │  │  │ │
│  │  │  │ Re-renders ONLY when:                      │  │  │ │
│  │  │  │ - participant.status changes               │  │  │ │
│  │  │  │ - content changes (streaming)              │  │  │ │
│  │  │  │                                            │  │  │ │
│  │  │  │ NOT when:                                  │  │  │ │
│  │  │  │ - Other participants update                │  │  │ │
│  │  │  │ - Unrelated state changes                  │  │  │ │
│  │  │  └───────────────────────────────────────────┘  │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           Judge Panel                                 │ │
│  │  const assessments = useJudgeAssessments(debateId)    │ │
│  │  const verdict = useStore(                            │ │
│  │    state => state.debates[debateId].judge.finalVerdict│ │
│  │  )                                                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           Cost Tracker                                │ │
│  │  const totalCost = useTotalCost(debateId)             │ │
│  │  // Memoized calculation across all participants      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Selective Re-rendering:
- ParticipantCard only re-renders on its own updates
- Judge Panel only on assessment/verdict changes
- Cost Tracker only when token usage changes
- Parent DebateView re-renders minimally
```

## 10. Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    API Key Security                         │
└─────────────────────────────────────────────────────────────┘

User enters API key
       │
       ▼
┌──────────────────────┐
│ Encrypt with AES-256 │
│ Key: Device Fingerprint│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│ Store in:                │
│ - LocalStorage (persist) │
│ - SessionStorage (temp)  │
└──────────┬───────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Security Disclaimers Shown:     │
│ ✓ Not 100% secure               │
│ ✓ Use session-only if shared PC │
│ ✓ Revoke keys after use         │
│ ✓ Monitor API usage              │
└──────────┬──────────────────────┘
           │
           ▼
On Use
       │
       ▼
┌──────────────────────┐
│ Retrieve & Decrypt   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│ Use in memory ONLY       │
│ Never log or expose      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Send over HTTPS only     │
└──────────────────────────┘

Additional Security:
┌────────────────────────────────┐
│ CSP Headers:                   │
│ - script-src 'self'            │
│ - connect-src api endpoints    │
│ - no inline scripts            │
└────────────────────────────────┘

┌────────────────────────────────┐
│ No Analytics by Default:       │
│ - Opt-in telemetry only        │
│ - Local-first approach         │
│ - Open source transparency     │
└────────────────────────────────┘
```

## 11. Performance Optimization Strategies

```
┌─────────────────────────────────────────────────────────────┐
│                Performance Optimization                      │
└─────────────────────────────────────────────────────────────┘

1. Selector Optimization
   ┌──────────────────────────────┐
   │ Zustand Shallow Comparison   │
   │ useStore(selector, shallow)  │
   │ - Array/object values        │
   │ - Prevents unnecessary rerenders│
   └──────────────────────────────┘

2. Component Memoization
   ┌──────────────────────────────┐
   │ React.memo + Custom Compare  │
   │ - Expensive components       │
   │ - ParticipantCard            │
   │ - ResponseTimeline           │
   └──────────────────────────────┘

3. Virtual Scrolling
   ┌──────────────────────────────┐
   │ @tanstack/react-virtual      │
   │ - Long debate histories      │
   │ - 1000+ messages             │
   │ - Windowed rendering         │
   └──────────────────────────────┘

4. Debouncing Streams
   ┌──────────────────────────────┐
   │ Debounce chunk updates       │
   │ - 50-100ms intervals         │
   │ - Batch state updates        │
   │ - Reduce re-render frequency │
   └──────────────────────────────┘

5. Code Splitting
   ┌──────────────────────────────┐
   │ React.lazy + Suspense        │
   │ - Route-based splitting      │
   │ - Heavy components (charts)  │
   │ - Reduce initial bundle      │
   └──────────────────────────────┘

6. State Normalization
   ┌──────────────────────────────┐
   │ Flat structure               │
   │ debates: { [id]: {...} }     │
   │ participants: { [id]: {...} }│
   │ - Fast lookups (O(1))        │
   │ - Easier updates             │
   └──────────────────────────────┘

Performance Budgets:
┌────────────────────────────────┐
│ Initial Load: < 3s             │
│ Time to Interactive: < 5s      │
│ Stream Chunk Render: < 16ms    │
│ State Update: < 100ms          │
│ Bundle Size: < 500kb (gzipped) │
└────────────────────────────────┘
```

## 12. Testing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Strategy                         │
└─────────────────────────────────────────────────────────────┘

Unit Tests
├── Zustand Store
│   ├── State mutations
│   ├── Selector logic
│   ├── Middleware behavior
│   └── Error handling
│
├── XState Machine
│   ├── State transitions
│   ├── Guard conditions
│   ├── Actions execution
│   └── Service invocations
│
├── Utilities
│   ├── Token counter
│   ├── Context builder
│   ├── Encryption
│   └── Export formatters
│
└── Hooks
    ├── useStream
    ├── useDebate
    ├── useJudge
    └── Custom selectors

Integration Tests
├── Debate Flow
│   ├── Setup → Running → Complete
│   ├── Error recovery
│   ├── Pause/Resume
│   └── Round progression
│
├── Streaming
│   ├── Simultaneous mode
│   ├── Sequential mode
│   ├── Reconnection
│   └── Rate limiting
│
└── Persistence
    ├── Save/Load debates
    ├── API key storage
    ├── Multi-tab sync
    └── Export functionality

E2E Tests (Playwright/Cypress)
├── Critical Paths
│   ├── Complete debate flow
│   ├── API key management
│   ├── Format switching
│   └── Export debate
│
├── Error Scenarios
│   ├── Network failures
│   ├── Invalid API keys
│   ├── Context overflow
│   └── Rate limit handling
│
└── Cross-browser
    ├── Chrome
    ├── Firefox
    ├── Safari
    └── Edge

Test Coverage Goals:
┌────────────────────────────────┐
│ Store logic: > 90%             │
│ State machine: 100%            │
│ Hooks: > 85%                   │
│ Components: > 70%              │
│ Integration: Critical paths    │
└────────────────────────────────┘
```

These diagrams provide visual representations of the state management architecture, helping contributors understand the system's complexity and data flow patterns.
