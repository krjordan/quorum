# Comprehensive Testing Strategy - Phase 1 Hive Mind

## Overview

This document outlines the complete testing strategy for Phase 1 implementation, covering backend (Python/FastAPI), frontend (React/TypeScript), integration testing, and end-to-end testing.

## Testing Objectives

- **Code Coverage**: Minimum 80% coverage across all components
- **Quality Assurance**: Prevent regressions and ensure reliability
- **Performance**: Validate streaming performance and responsiveness
- **Security**: Test authentication, authorization, and input validation
- **User Experience**: Validate complete user workflows

## Test Pyramid

```
         /\
        /  \  E2E Tests (Playwright)
       /    \  - Complete user workflows
      /------\ - Browser compatibility
     /        \ - UI/UX validation
    /----------\
   / Integration\ Integration Tests (pytest + httpx)
  /    Tests     \ - API endpoint integration
 /--------------\ - SSE streaming flow
/                \ - Provider switching
/--Unit--Tests---\ Unit Tests (pytest + Vitest)
- Backend logic    - Frontend components
- Service layer    - React hooks
- Data models      - Utility functions
```

## 1. Backend Testing (pytest)

### 1.1 Test Structure

```
tests/
├── backend/
│   ├── conftest.py              # Shared fixtures
│   ├── test_api_chat.py         # Chat API endpoints
│   ├── test_api_health.py       # Health check endpoints
│   ├── test_services_llm.py     # LLM service layer
│   ├── test_services_conv.py    # Conversation management
│   └── test_models.py           # Data models
├── fixtures/
│   ├── llm_responses.py         # Mock LLM responses
│   └── sample_data.py           # Test data
└── pytest.ini                   # Pytest configuration
```

### 1.2 Key Fixtures (conftest.py)

```python
# FastAPI test client
@pytest.fixture
def client() -> TestClient

# Async HTTP client
@pytest.fixture
async def async_client() -> AsyncClient

# Mock LLM providers
@pytest.fixture
def mock_anthropic_response()

@pytest.fixture
def mock_openrouter_response()

# Database session (future)
@pytest.fixture
async def db_session()

# Authentication
@pytest.fixture
def auth_token()
```

### 1.3 Test Categories (pytest markers)

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.sse` - SSE streaming tests
- `@pytest.mark.llm` - LLM interaction tests
- `@pytest.mark.slow` - Tests >1 second
- `@pytest.mark.security` - Security tests
- `@pytest.mark.async` - Async tests

### 1.4 Coverage Requirements

```ini
[coverage:run]
source = src
omit = */tests/*, */venv/*

[coverage:report]
precision = 2
fail_under = 80
```

## 2. Frontend Testing (Vitest + React Testing Library)

### 2.1 Test Structure

```
tests/
└── frontend/
    ├── setup.ts                    # Global test setup
    ├── components/
    │   ├── Chat.test.tsx           # Chat component
    │   ├── MessageList.test.tsx    # Message display
    │   ├── MessageInput.test.tsx   # Input handling
    │   └── ModelSelector.test.tsx  # Model selection
    ├── hooks/
    │   ├── useSSE.test.ts          # SSE hook
    │   └── useChat.test.ts         # Chat state hook
    └── utils/
        └── formatters.test.ts      # Utility functions
```

### 2.2 Test Utilities (setup.ts)

```typescript
// Global matchers
import '@testing-library/jest-dom/matchers'

// Mock EventSource for SSE
class MockEventSource { ... }

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', { ... })

// Cleanup after each test
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
```

### 2.3 Testing Patterns

**Component Testing:**
```typescript
describe('Chat Component', () => {
  it('renders chat interface', () => {
    render(<Chat />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('sends message on button click', async () => {
    const mockSend = vi.fn()
    render(<Chat onSend={mockSend} />)

    await userEvent.type(input, 'Test')
    await userEvent.click(sendButton)

    expect(mockSend).toHaveBeenCalledWith('Test')
  })
})
```

**Hook Testing:**
```typescript
describe('useSSE Hook', () => {
  it('establishes SSE connection', () => {
    const { result } = renderHook(() => useSSE('/api/chat/stream'))

    expect(result.current.isConnected).toBe(true)
  })
})
```

### 2.4 Coverage Configuration

```typescript
coverage: {
  provider: 'v8',
  reporter: ['text', 'json', 'html'],
  thresholds: {
    lines: 80,
    functions: 80,
    branches: 80,
    statements: 80
  }
}
```

## 3. Integration Testing

### 3.1 Test Scenarios

**SSE Streaming Flow:**
1. Frontend sends POST request
2. Backend establishes SSE connection
3. LLM provider streams response
4. Frontend receives and displays chunks
5. Conversation is persisted

**Provider Switching:**
1. Start conversation with Anthropic
2. Switch to OpenRouter mid-conversation
3. Verify context is maintained
4. Verify both providers work correctly

**Error Handling:**
1. Simulate connection failure
2. Verify error state display
3. Test retry mechanism
4. Verify graceful degradation

### 3.2 Example Integration Test

```python
@pytest.mark.integration
def test_end_to_end_streaming(client, mock_anthropic_response):
    request_data = {
        "message": "Test question",
        "provider": "anthropic",
        "stream": True
    }

    with client.stream("POST", "/api/chat/stream", json=request_data) as response:
        assert response.status_code == 200

        events = []
        for line in response.iter_lines():
            if line.startswith('data: '):
                events.append(json.loads(line[6:]))

        assert len(events) > 0
        assert "stop" in str(events[-1])
```

## 4. E2E Testing (Playwright)

### 4.1 Test Structure

```
tests/
└── e2e/
    ├── playwright.config.ts     # Playwright config
    ├── chat-flow.spec.ts        # Main chat flow
    ├── error-handling.spec.ts   # Error scenarios
    └── mobile.spec.ts           # Mobile viewport
```

### 4.2 Key Test Scenarios

**Happy Path:**
1. Load application
2. User types message
3. Click send
4. See streaming response
5. Continue conversation
6. Clear chat

**Error Scenarios:**
1. Network failure during streaming
2. Invalid API key
3. Rate limiting
4. Timeout handling

**Mobile Testing:**
1. Responsive layout
2. Touch interactions
3. Virtual keyboard handling

### 4.3 Playwright Configuration

```typescript
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
  ],

  webServer: [
    { command: 'npm run dev', url: 'http://localhost:5173' },
    { command: 'uvicorn main:app', url: 'http://localhost:8000' }
  ]
})
```

## 5. Mock Strategies

### 5.1 LLM API Mocking

**Anthropic:**
```python
def mock_anthropic_response(content: str):
    return [
        {"type": "content_block_delta", "delta": {"text": content}},
        {"type": "message_stop"}
    ]
```

**OpenRouter:**
```python
def mock_openrouter_response(content: str):
    return [
        {"choices": [{"delta": {"content": content}}]},
        {"choices": [{"finish_reason": "stop"}]}
    ]
```

### 5.2 SSE Mocking (Frontend)

```typescript
class MockEventSource {
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', {
        data: JSON.stringify(data)
      }))
    }
  }
}
```

## 6. CI/CD Integration

### 6.1 GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pytest
        run: pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm ci
      - name: Run vitest
        run: npm run test:coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Run E2E tests
        run: npm run test:e2e
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/coverage/e2e
```

## 7. Test Execution Commands

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific markers
pytest -m "unit"
pytest -m "integration"
pytest -m "sse"

# Run specific test file
pytest tests/backend/test_api_chat.py

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Frontend Tests
```bash
# Run all tests
npm run test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch

# UI mode
npm run test:ui

# Run specific test
npm run test Chat.test.tsx
```

### E2E Tests
```bash
# Run all E2E tests
npm run test:e2e

# Run specific browser
npm run test:e2e -- --project=chromium

# Debug mode
npm run test:e2e -- --debug

# Generate report
npm run test:e2e -- --reporter=html
```

## 8. Performance Testing

### 8.1 Streaming Latency
- **Target**: Time to first byte < 200ms
- **Method**: Measure time from request to first SSE chunk

### 8.2 Throughput
- **Target**: > 10 KB/s streaming throughput
- **Method**: Measure total bytes / total time

### 8.3 Load Testing
- **Tool**: Locust or k6
- **Scenario**: 10 concurrent users sending messages
- **Success Criteria**: 99th percentile response time < 2s

## 9. Security Testing

### 9.1 Test Areas
- API key protection
- Prompt injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Input validation

### 9.2 Example Security Tests
```python
@pytest.mark.security
def test_prompt_injection_protection(client):
    malicious_prompt = "Ignore previous instructions..."
    response = client.post("/api/chat/stream", json={
        "message": malicious_prompt
    })
    # Verify proper handling
```

## 10. Test Data Management

### 10.1 Fixtures Location
```
tests/fixtures/
├── llm_responses.py         # Mock API responses
├── sample_conversations.py  # Conversation data
└── test_users.py           # User data (future)
```

### 10.2 Data Isolation
- Each test runs in isolation
- Database transactions rolled back
- Mock data reset between tests

## 11. Continuous Improvement

### 11.1 Coverage Monitoring
- Track coverage trends over time
- Set coverage gates in CI/CD
- Require tests for new features

### 11.2 Test Quality Metrics
- Test execution time
- Flaky test detection
- Test failure patterns

### 11.3 Regular Reviews
- Weekly test suite review
- Monthly performance review
- Quarterly strategy update

## 12. Documentation

### 12.1 Test Documentation
- Docstrings for all test functions
- README in test directories
- Architecture decision records

### 12.2 Runbooks
- How to run tests locally
- How to debug failing tests
- How to add new tests

## Summary

This comprehensive testing strategy ensures:
- ✅ 80%+ code coverage
- ✅ Fast feedback loops
- ✅ Confidence in deployments
- ✅ Prevention of regressions
- ✅ Quality user experience

All test configurations and examples are ready for implementation.
