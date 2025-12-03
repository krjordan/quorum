# Phase 2 Testing Strategy - Multi-LLM Debate Engine

**Agent:** Test Engineer (Quorum Hive Mind)
**Phase:** Phase 2 - Multi-LLM Debate Engine
**Date:** 2025-12-02
**Status:** ✅ Complete - Ready for Phase 4 Implementation

---

## 📋 Overview

This comprehensive testing strategy covers all aspects of Phase 2: Multi-LLM Debate Engine. The strategy includes unit tests, integration tests, E2E scenarios, performance benchmarks, and reusable test fixtures.

**Testing Philosophy:** Test-Driven Development (TDD) with 85%+ coverage target

---

## 📚 Documentation Structure

| Document | Purpose | Test Count |
|----------|---------|------------|
| [unit-tests.md](./unit-tests.md) | Backend & frontend unit tests | 150+ tests |
| [integration-tests.md](./integration-tests.md) | End-to-end workflow integration | 50+ tests |
| [e2e-scenarios.md](./e2e-scenarios.md) | Playwright browser scenarios | 25+ scenarios |
| [performance-tests.md](./performance-tests.md) | Latency, memory, concurrency | 40+ tests |
| [test-fixtures.md](./test-fixtures.md) | Reusable mock data & fixtures | 30+ fixtures |

**Total Estimated Tests:** 315+

---

## 🎯 Testing Pyramid

```
         /\
        /  \  E2E Tests (25+)
       /    \  - Playwright scenarios
      /------\  - 6 user workflows
     /        \ - 4 browsers
    /----------\
   / Integration\ Integration Tests (50+)
  /    Tests     \ - Complete debate flows
 /--------------\ - Parallel streaming
/                \ - Cost tracking
/--Unit--Tests---\ Unit Tests (150+)
- Backend (100+)   - Frontend (50+)
- Service layer    - Components
- Business logic   - State management
```

---

## 🔧 Test Categories

### 1. Unit Tests (85%+ coverage target)

**Backend Tests:**
- ✅ `debate_service.py` - Debate orchestration logic
- ✅ `context_manager.py` - Sliding window, token counting
- ✅ `judge_service.py` - Rubric evaluation, verdict generation
- ✅ `parallel_streaming.py` - Multi-stream coordination
- ✅ `cost_calculator.py` - Cost tracking accuracy

**Frontend Tests:**
- ✅ `debate-store.ts` - State management (XState)
- ✅ `useParallelStreaming.ts` - SSE connection management
- ✅ `useCostTracker.ts` - Real-time cost updates
- ✅ Components: DebateArena, ParticipantCard, JudgeAssessment

### 2. Integration Tests

**Workflow Tests:**
- ✅ Simple 2-debater free-form debate
- ✅ 4-debater structured debate (3 phases)
- ✅ Convergence-seeking debate (stops when consensus reached)
- ✅ Round-limited debate (exactly N rounds)
- ✅ Error handling (participant/judge failures)
- ✅ Cost tracking accuracy (end-to-end)

**Streaming Tests:**
- ✅ Parallel streaming (4 simultaneous debaters)
- ✅ Stream reconnection on disconnect
- ✅ Individual stream error isolation

### 3. E2E Scenarios (Playwright)

**6 Key User Workflows:**
1. ✅ **Simple Debate** - 2 debaters, watch streaming, see verdict
2. ✅ **Multi-Debater** - 4 participants, structured phases
3. ✅ **Cost Warning** - Warning triggers, user override/stop
4. ✅ **Stream Failure** - Automatic reconnection, manual retry
5. ✅ **Judge Intervention** - Stops on repetition/convergence
6. ✅ **Export** - Download as Markdown/JSON

**Browser Coverage:**
- ✅ Desktop Chrome
- ✅ Desktop Firefox
- ✅ Desktop Safari
- ✅ Mobile Chrome (Pixel 5)

### 4. Performance Tests

**Benchmarks:**
- ✅ Latency: <10ms backend overhead per debater
- ✅ Memory: <100MB per debate (4 simultaneous streams)
- ✅ Concurrency: 5+ simultaneous debates
- ✅ Token accuracy: Within 1% of provider counts
- ✅ Cost accuracy: Exact match with provider pricing

**Load Testing:**
- ✅ Locust scenarios (10-50 concurrent users)
- ✅ SSE connection limits (10+ connections)
- ✅ Memory leak detection

---

## 🚀 Quick Start

### Prerequisites

```bash
# Backend dependencies
pip install pytest pytest-cov pytest-asyncio pytest-benchmark httpx memory-profiler locust

# Frontend dependencies
npm install -D vitest @vitest/ui @testing-library/react @testing-library/user-event

# E2E dependencies
npm install -D @playwright/test
npx playwright install --with-deps
```

### Running Tests

#### Backend Tests

```bash
# Run all Phase 2 unit tests
pytest tests/backend/phase2/ -m "unit" --cov

# Run integration tests
pytest tests/integration/phase2/ -m "integration"

# Run performance tests
pytest tests/performance/phase2/ -m "performance" --benchmark-only

# Run with coverage report
pytest tests/backend/phase2/ --cov=backend/app --cov-report=html
```

#### Frontend Tests

```bash
# Run all Phase 2 tests
npm run test:phase2

# Run with coverage
npm run test:coverage -- tests/frontend/phase2/

# Watch mode
npm run test:watch tests/frontend/phase2/

# UI mode (interactive)
npm run test:ui
```

#### E2E Tests

```bash
# Run all E2E scenarios
npm run test:e2e:phase2

# Run specific scenario
npm run test:e2e:phase2 -- simple-debate.spec.ts

# Run in headed mode (see browser)
npm run test:e2e:phase2 -- --headed

# Debug mode
npm run test:e2e:phase2 -- --debug

# Generate HTML report
npm run test:e2e:phase2 -- --reporter=html
```

#### Load Testing

```bash
# Run Locust load test
locust -f tests/performance/phase2/locustfile.py --users 20 --spawn-rate 5

# Headless with report
locust -f tests/performance/phase2/locustfile.py \
  --users 50 --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --html tests/coverage/performance/locust-report.html
```

---

## 📊 Coverage Targets

| Component | Target | Priority |
|-----------|--------|----------|
| **Backend** | | |
| debate_service.py | 90%+ | Critical |
| context_manager.py | 90%+ | Critical |
| judge_service.py | 85%+ | High |
| parallel_streaming.py | 85%+ | High |
| cost_calculator.py | 95%+ | Critical |
| **Frontend** | | |
| debate-store.ts | 90%+ | Critical |
| useParallelStreaming.ts | 85%+ | High |
| useCostTracker.ts | 85%+ | High |
| Components | 80%+ | Medium |
| **Overall** | **85%+** | **Critical** |

---

## 🧪 Test Data & Fixtures

### Available Fixtures

**Debate Configurations:**
- `simple_2_debater_config` - Basic 2-participant debate
- `four_debater_structured_config` - 4 participants with phases
- `convergence_seeking_config` - Stops when consensus reached
- `round_limited_config` - Fixed number of rounds
- `mock_debate_config_factory` - Custom config factory

**LLM Responses:**
- `mock_anthropic_streaming_response` - Anthropic SSE chunks
- `mock_openai_streaming_response` - OpenAI SSE chunks
- `mock_complete_responses` - Full responses by model
- `mock_litellm_response_factory` - Custom response factory

**Judge Verdicts:**
- `mock_judge_assessment_continue` - Assessment recommending continuation
- `mock_judge_assessment_stop_repetition` - Stops due to repetition
- `mock_judge_assessment_stop_convergence` - Stops due to consensus
- `mock_final_verdict` - Complete final verdict

**Cost Data:**
- `cost_test_cases` - Pricing validation cases
- `debate_cost_scenarios` - Full debate cost scenarios
- `pricing_tables` - Current provider pricing

**Context Histories:**
- `simple_debate_history` - 3-round history
- `large_debate_history` - 20+ rounds (factory)
- `convergent_debate_history` - Gradual consensus
- `repetitive_debate_history` - Repetitive arguments

---

## 🎯 Testing Strategy by Component

### Debate Service

**What to Test:**
- Round orchestration (simultaneous vs sequential)
- Parallel LLM API calls
- Error handling (rate limits, auth, context overflow)
- Cost tracking per participant

**How to Test:**
- Mock LiteLLM responses for predictability
- Use fixtures for debate configurations
- Verify timing for parallel execution
- Assert cost calculations match expected

### Context Manager

**What to Test:**
- Sliding window correctness (keeps last N rounds)
- Token counting accuracy (within 1%)
- Context overflow detection
- Summarization strategy

**How to Test:**
- Use tiktoken as ground truth for token counts
- Test with large histories (20+ rounds)
- Verify memory doesn't grow linearly with window
- Compare pricing calculations with provider rates

### Judge Service

**What to Test:**
- Rubric-based evaluation
- Structured output validation (JSON schema)
- Convergence/repetition detection
- Final verdict generation

**How to Test:**
- Mock judge LLM responses
- Validate JSON structure matches schema
- Test flag triggers (convergence, repetition)
- Verify scoring logic

### Parallel Streaming

**What to Test:**
- Multiple SSE connections
- Error isolation (one stream fails, others continue)
- Reconnection logic
- Backpressure handling

**How to Test:**
- Mock EventSource in frontend tests
- Simulate network failures
- Verify event ordering
- Test concurrent stream limits

---

## 📈 Performance Benchmarks

### Target Metrics

| Metric | Target | Test Method |
|--------|--------|-------------|
| Backend overhead per debater | <10ms | pytest-benchmark |
| Stream setup time (4 debaters) | <20ms | pytest-benchmark |
| Context processing | <5ms | pytest-benchmark |
| Judge assessment overhead | <15ms | pytest-benchmark |
| Cost calculation | <1ms | pytest-benchmark |
| Memory per debate | <100MB | memory_profiler |
| Memory per stream | <10MB | memory_profiler |
| Concurrent debates | 5+ | Integration test |
| SSE connections | 10+ | Integration test |
| Token accuracy | Within 1% | tiktoken comparison |
| Cost accuracy | Exact | Provider pricing |

---

## 🐛 Debugging Failed Tests

### Backend Test Failures

```bash
# Run single test with verbose output
pytest tests/backend/phase2/test_debate_service.py::TestDebateService::test_orchestrate_round_simultaneous_mode -v -s

# Run with debugger
pytest tests/backend/phase2/ --pdb

# Generate detailed failure report
pytest tests/backend/phase2/ --tb=long --maxfail=1
```

### Frontend Test Failures

```bash
# Run single test
npm run test debate-store.test.ts

# Run with UI (interactive debugging)
npm run test:ui

# Run with verbose output
npm run test -- --reporter=verbose
```

### E2E Test Failures

```bash
# Run with video recording
npm run test:e2e:phase2 -- --video=on

# Run in headed mode to watch
npm run test:e2e:phase2 -- --headed --slowMo=1000

# Generate trace for debugging
npm run test:e2e:phase2 -- --trace=on
npx playwright show-trace trace.zip
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Phase 2 Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          pip install -r requirements.txt
          pytest tests/backend/phase2/ tests/integration/phase2/ --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run frontend tests
        run: |
          npm ci
          npm run test:coverage -- tests/frontend/phase2/
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Run E2E tests
        run: npm run test:e2e:phase2
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/coverage/e2e/phase2

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run performance tests
        run: pytest tests/performance/phase2/ --benchmark-only
```

---

## 📚 Additional Resources

### Test Writing Guidelines

1. **Naming Convention:** `test_<what>_<scenario>`
   - ✅ `test_orchestrate_round_simultaneous_mode`
   - ❌ `test_function1`

2. **Arrange-Act-Assert Pattern:**
   ```python
   def test_example():
       # Arrange
       config = mock_config()

       # Act
       result = service.orchestrate(config)

       # Assert
       assert result.success == True
   ```

3. **One Assertion Per Test (when possible):**
   - Focus tests on single behavior
   - Use multiple tests for multiple aspects

4. **Use Fixtures for DRY:**
   - Don't repeat setup code
   - Use parametrize for variations

### Reference Documentation

- **Phase 1 Testing:** [docs/future-phases/testing-strategy.md](../future-phases/testing-strategy.md)
- **Phase 2 Architecture:** [docs/future-phases/debate-engine-testing-architecture.md](../future-phases/debate-engine-testing-architecture.md)
- **Pytest Documentation:** https://docs.pytest.org/
- **Vitest Documentation:** https://vitest.dev/
- **Playwright Documentation:** https://playwright.dev/

---

## ✅ Implementation Checklist

### Phase 4 Team: Use this checklist when implementing tests

**Unit Tests:**
- [ ] Backend: debate_service.py (30+ tests)
- [ ] Backend: context_manager.py (25+ tests)
- [ ] Backend: judge_service.py (20+ tests)
- [ ] Backend: parallel_streaming.py (15+ tests)
- [ ] Backend: cost_calculator.py (10+ tests)
- [ ] Frontend: debate-store.ts (20+ tests)
- [ ] Frontend: useParallelStreaming.ts (15+ tests)
- [ ] Frontend: Components (15+ tests)

**Integration Tests:**
- [ ] Complete debate workflows (10+ tests)
- [ ] Parallel streaming flows (8+ tests)
- [ ] Cost tracking flows (6+ tests)
- [ ] Context management flows (6+ tests)
- [ ] Judge integration (8+ tests)
- [ ] Export flows (4+ tests)

**E2E Scenarios:**
- [ ] Scenario 1: Simple 2-debater (5 tests)
- [ ] Scenario 2: 4-debater structured (4 tests)
- [ ] Scenario 3: Cost warning (4 tests)
- [ ] Scenario 4: Stream failure (3 tests)
- [ ] Scenario 5: Judge intervention (3 tests)
- [ ] Scenario 6: Export (3 tests)

**Performance Tests:**
- [ ] Latency benchmarks (6+ tests)
- [ ] Memory usage tests (5+ tests)
- [ ] Concurrent handling (4+ tests)
- [ ] Token accuracy (5+ tests)
- [ ] Cost accuracy (5+ tests)
- [ ] Load testing (Locust setup)

**Fixtures:**
- [ ] Debate configurations (10+ fixtures)
- [ ] LLM responses (8+ fixtures)
- [ ] Judge verdicts (6+ fixtures)
- [ ] Cost data (3+ fixtures)
- [ ] Context histories (5+ fixtures)
- [ ] Streaming events (4+ fixtures)

**Documentation:**
- [ ] Update package.json test scripts
- [ ] Update pytest.ini with Phase 2 markers
- [ ] Update Playwright config for Phase 2
- [ ] Add test commands to main README
- [ ] Document test data management

---

## 🎓 Next Steps

1. **Phase 4 Implementation:**
   - Implement source code following TDD
   - Write tests BEFORE implementation
   - Aim for 85%+ coverage

2. **Continuous Improvement:**
   - Monitor test execution times
   - Identify and fix flaky tests
   - Update fixtures as API evolves

3. **Performance Monitoring:**
   - Track benchmark trends
   - Set up alerts for regression
   - Regular load testing

4. **Documentation:**
   - Keep test docs up to date
   - Document new test patterns
   - Share learnings with team

---

## 📞 Support & Questions

- **Issues:** Create GitHub issue with `testing` label
- **Questions:** Tag @test-engineer in project discussions
- **Documentation:** See individual test plan documents

---

**Status:** ✅ Complete - Ready for Phase 4 Implementation
**Last Updated:** 2025-12-02
**Maintained By:** Test Engineer (Quorum Hive Mind)
