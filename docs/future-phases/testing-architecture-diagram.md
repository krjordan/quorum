# Testing Architecture Diagram - Hive Mind Phase 1

## System Architecture with Testing Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD Pipeline (GitHub Actions)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐│
│  │  Backend   │  │  Frontend  │  │Integration │  │    E2E     │  │Security││
│  │   Tests    │  │   Tests    │  │   Tests    │  │   Tests    │  │ Tests  ││
│  │  (pytest)  │  │  (Vitest)  │  │  (pytest)  │  │(Playwright)│  │(Bandit)││
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────┘│
│         │                │                │               │             │    │
│         └────────────────┴────────────────┴───────────────┴─────────────┘    │
│                                    │                                         │
│                          ┌─────────▼─────────┐                              │
│                          │  Coverage Reports  │                              │
│                          │    (Codecov)       │                              │
│                          └────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              E2E Testing Layer                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Playwright E2E Tests                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │  │
│  │  │ Chromium │  │ Firefox  │  │  Safari  │  │  Mobile  │  │ Mobile │ │  │
│  │  │ Desktop  │  │ Desktop  │  │ Desktop  │  │  Chrome  │  │ Safari │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │  │
│  │                                                                        │  │
│  │  Test Scenarios:                                                      │  │
│  │  • Load chat interface                                                │  │
│  │  • Send message and receive streaming response                       │  │
│  │  • Handle errors and retry                                           │  │
│  │  • Multi-turn conversations                                          │  │
│  │  • Model switching                                                   │  │
│  │  • Auto-scroll behavior                                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Real Browser Environment                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Integration Testing Layer                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                 Integration Tests (pytest + httpx)                    │  │
│  │                                                                        │  │
│  │  ┌────────────────────┐         ┌────────────────────┐               │  │
│  │  │  SSE Streaming     │         │  Provider          │               │  │
│  │  │  Flow Tests        │         │  Switching Tests   │               │  │
│  │  │  • Anthropic       │         │  • Context         │               │  │
│  │  │  • OpenRouter      │         │    Maintenance     │               │  │
│  │  │  • Persistence     │         │  • Format          │               │  │
│  │  │  • Error Recovery  │         │    Conversion      │               │  │
│  │  └────────────────────┘         └────────────────────┘               │  │
│  │                                                                        │  │
│  │  ┌────────────────────┐         ┌────────────────────┐               │  │
│  │  │  Concurrent        │         │  Performance       │               │  │
│  │  │  Sessions          │         │  Benchmarks        │               │  │
│  │  │  • Multi-user      │         │  • Latency         │               │  │
│  │  │  • Isolation       │         │  • Throughput      │               │  │
│  │  └────────────────────┘         └────────────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              Full Stack (Frontend + Backend + LLM Mock)               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Frontend Testing Layer                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                Frontend Tests (Vitest + React Testing Library)        │  │
│  │                                                                        │  │
│  │  Component Tests              Hook Tests               Utility Tests  │  │
│  │  ┌──────────────┐            ┌──────────────┐         ┌────────────┐ │  │
│  │  │ Chat         │            │ useSSE       │         │ Formatters │ │  │
│  │  │ • Render     │            │ • Connect    │         │ • Parse    │ │  │
│  │  │ • Input      │            │ • Stream     │         │ • Format   │ │  │
│  │  │ • Send       │            │ • Error      │         │ • Validate │ │  │
│  │  │ • Display    │            │ • Reconnect  │         └────────────┘ │  │
│  │  └──────────────┘            └──────────────┘                        │  │
│  │                                                                        │  │
│  │  ┌──────────────┐            ┌──────────────┐                        │  │
│  │  │ MessageList  │            │ useChat      │                        │  │
│  │  │ • Scroll     │            │ • State      │                        │  │
│  │  │ • Render     │            │ • History    │                        │  │
│  │  │ • Streaming  │            │ • Send       │                        │  │
│  │  └──────────────┘            └──────────────┘                        │  │
│  │                                                                        │  │
│  │  ┌──────────────┐                                                     │  │
│  │  │ MessageInput │                                                     │  │
│  │  │ • Typing     │         Mock Setup:                                │  │
│  │  │ • Validation │         • EventSource (SSE)                        │  │
│  │  │ • Submit     │         • window.matchMedia                        │  │
│  │  └──────────────┘         • IntersectionObserver                     │  │
│  │                           • ResizeObserver                            │  │
│  │  ┌──────────────┐         • fetch API                                │  │
│  │  │ModelSelector │                                                     │  │
│  │  │ • Options    │                                                     │  │
│  │  │ • Selection  │                                                     │  │
│  │  │ • Switching  │                                                     │  │
│  │  └──────────────┘                                                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                 React Components (Isolated Testing)                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend Testing Layer                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Backend Tests (pytest)                           │  │
│  │                                                                        │  │
│  │  API Tests                  Service Tests             Model Tests     │  │
│  │  ┌──────────────┐           ┌──────────────┐         ┌────────────┐  │  │
│  │  │ /chat/stream │           │ LLM Service  │         │ Message    │  │  │
│  │  │ • POST       │           │ • Anthropic  │         │ • Validate │  │  │
│  │  │ • SSE        │           │ • OpenRouter │         │ • Serialize│  │  │
│  │  │ • Streaming  │           │ • Streaming  │         └────────────┘  │  │
│  │  └──────────────┘           │ • Format     │                        │  │
│  │                             └──────────────┘                        │  │
│  │  ┌──────────────┐                                                   │  │
│  │  │ /chat/msg    │           ┌──────────────┐                        │  │
│  │  │ • POST       │           │ Conversation │                        │  │
│  │  │ • Non-stream │           │ • Load       │                        │  │
│  │  └──────────────┘           │ • Save       │                        │  │
│  │                             │ • History    │                        │  │
│  │  ┌──────────────┐           └──────────────┘                        │  │
│  │  │ /history/:id │                                                   │  │
│  │  │ • GET        │                                                   │  │
│  │  │ • Retrieve   │           Fixtures:                               │  │
│  │  └──────────────┘           • Mock Anthropic Response               │  │
│  │                             • Mock OpenRouter Response               │  │
│  │  ┌──────────────┐           • Sample Conversations                  │  │
│  │  │ /health      │           • Auth Tokens                           │  │
│  │  │ • GET        │           • SSE Event Parser                      │  │
│  │  └──────────────┘           • Database Session                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Application (Isolated)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Mock/Fixture Layer                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        LLM Response Mocks                             │  │
│  │                                                                        │  │
│  │  Anthropic Mock              OpenRouter Mock          Error Mocks     │  │
│  │  ┌──────────────┐            ┌──────────────┐        ┌────────────┐  │  │
│  │  │ Simple       │            │ Simple       │        │ Rate Limit │  │  │
│  │  │ Response     │            │ Response     │        │ Invalid    │  │  │
│  │  │ • Message    │            │ • Choices    │        │ Auth Error │  │  │
│  │  │   Start      │            │ • Delta      │        │ Server Err │  │  │
│  │  │ • Content    │            │ • Finish     │        └────────────┘  │  │
│  │  │   Delta      │            │              │                        │  │
│  │  │ • Message    │            │              │                        │  │
│  │  │   Stop       │            │              │                        │  │
│  │  └──────────────┘            └──────────────┘                        │  │
│  │                                                                        │  │
│  │  ┌──────────────┐            ┌──────────────┐                        │  │
│  │  │ Chunked      │            │ Chunked      │                        │  │
│  │  │ Response     │            │ Response     │                        │  │
│  │  │ • 5 chunks   │            │ • 5 chunks   │                        │  │
│  │  │ • Realistic  │            │ • Realistic  │                        │  │
│  │  │   timing     │            │   timing     │                        │  │
│  │  └──────────────┘            └──────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Sample Conversation Data                         │  │
│  │                                                                        │  │
│  │  • Technical conversation (neural networks)                           │  │
│  │  • Simple conversation (hello/hi)                                     │  │
│  │  • Multi-turn conversation (Python Q&A)                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          Coverage & Reporting Layer                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Backend Coverage         Frontend Coverage        E2E Coverage             │
│  ┌────────────────┐      ┌────────────────┐      ┌────────────────┐        │
│  │ coverage.py    │      │ Vitest v8      │      │ Playwright     │        │
│  │ • Line: 80%+   │      │ • Line: 80%+   │      │ • Screenshots  │        │
│  │ • Branch: 80%+ │      │ • Branch: 80%+ │      │ • Videos       │        │
│  │ • Function:80%+│      │ • Function:80%+│      │ • Traces       │        │
│  │ • HTML Report  │      │ • HTML Report  │      │ • HTML Report  │        │
│  │ • XML (Codecov)│      │ • JSON/LCOV    │      │ • JSON Results │        │
│  └────────────────┘      └────────────────┘      └────────────────┘        │
│         │                        │                        │                 │
│         └────────────────────────┴────────────────────────┘                 │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌──────────────────────────┐                             │
│                    │   Codecov Dashboard      │                             │
│                    │   • Trend Analysis       │                             │
│                    │   • PR Comments          │                             │
│                    │   • Coverage Gates       │                             │
│                    └──────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Test Execution Flow

```
Developer Makes Changes
        │
        ▼
┌───────────────┐
│ Pre-commit    │
│ Hooks (local) │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Push to GitHub│
└───────┬───────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│        GitHub Actions CI/CD Pipeline        │
├─────────────────────────────────────────────┤
│                                              │
│  Step 1: Install Dependencies (parallel)    │
│  ┌──────────┐    ┌──────────┐              │
│  │ Backend  │    │ Frontend │              │
│  │ pip      │    │ npm      │              │
│  └──────────┘    └──────────┘              │
│                                              │
│  Step 2: Run Tests (parallel)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Backend  │ │ Frontend │ │  E2E     │   │
│  │ pytest   │ │ Vitest   │ │Playwright│   │
│  └──────────┘ └──────────┘ └──────────┘   │
│                                              │
│  Step 3: Generate Coverage                  │
│  ┌──────────────────────────────────────┐  │
│  │ Collect coverage from all test types │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  Step 4: Upload to Codecov                  │
│  ┌──────────────────────────────────────┐  │
│  │ Aggregate and analyze coverage       │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  Step 5: Quality Gates                      │
│  ┌──────────────────────────────────────┐  │
│  │ ✓ Coverage >= 80%                    │  │
│  │ ✓ All tests pass                     │  │
│  │ ✓ No security issues                 │  │
│  │ ✓ Code quality checks pass           │  │
│  └──────────────────────────────────────┘  │
│                                              │
└─────────────────┬────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   ✅ SUCCESS          ❌ FAILURE
        │                   │
        │                   ▼
        │          ┌────────────────┐
        │          │ PR Block       │
        │          │ Notification   │
        │          │ Retry Option   │
        │          └────────────────┘
        │
        ▼
┌───────────────┐
│ PR Approved   │
│ Ready to Merge│
└───────────────┘
```

## Coverage Requirements Matrix

| Component | Lines | Functions | Branches | Statements | Tool |
|-----------|-------|-----------|----------|------------|------|
| Backend API | 80%+ | 80%+ | 80%+ | 80%+ | pytest + coverage.py |
| Backend Services | 85%+ | 85%+ | 85%+ | 85%+ | pytest + coverage.py |
| Frontend Components | 80%+ | 80%+ | 75%+ | 80%+ | Vitest + v8 |
| Frontend Hooks | 85%+ | 85%+ | 80%+ | 85%+ | Vitest + v8 |
| Integration Flows | Critical Paths | Critical Paths | Critical Paths | Critical Paths | pytest + httpx |
| E2E User Flows | All Happy Paths | All Happy Paths | Error Cases | All Happy Paths | Playwright |

## Test Priorities

### P0 (Must Have - Blocking)
- ✅ Backend API endpoints
- ✅ Frontend core chat component
- ✅ SSE streaming integration
- ✅ E2E happy path

### P1 (Should Have - Important)
- ✅ Error handling
- ✅ Provider switching
- ✅ Conversation persistence
- ✅ Multi-browser E2E

### P2 (Nice to Have - Enhancement)
- ✅ Performance benchmarks
- ✅ Security tests
- ✅ Mobile viewport tests
- ✅ Load testing

## File Organization

```
/Users/ryanjordan/Projects/quorum/
├── tests/
│   ├── pytest.ini                      ← Backend pytest config
│   ├── vitest.config.ts                ← Frontend vitest config
│   ├── backend/
│   │   ├── conftest.py                 ← Backend fixtures
│   │   └── test_api_chat.py            ← Backend API tests
│   ├── frontend/
│   │   ├── setup.ts                    ← Frontend test setup
│   │   └── components/
│   │       └── Chat.test.tsx           ← Component tests
│   ├── integration/
│   │   └── test_sse_streaming.py       ← Integration tests
│   ├── e2e/
│   │   ├── playwright.config.ts        ← E2E config
│   │   └── chat-flow.spec.ts           ← E2E tests
│   ├── fixtures/
│   │   └── llm_responses.py            ← Mock data
│   └── coverage/                       ← Coverage reports
│       ├── backend/
│       ├── frontend/
│       └── e2e/
└── docs/
    ├── testing-strategy.md             ← Comprehensive guide
    ├── testing-deliverables-summary.md ← Quick reference
    ├── testing-architecture-diagram.md  ← This file
    └── ci-cd-example.yml               ← CI/CD workflow
```

---

**Total Files Created:** 14
- **Test Files:** 10 (pytest.ini, configs, tests)
- **Documentation:** 4 (strategy, summary, architecture, CI/CD)

**Ready for Implementation:** ✅ All configurations and examples complete
