# Phase 2 Unit Test Plan - Multi-LLM Debate Engine

**Date:** 2025-12-02
**Agent:** Test Engineer
**Phase:** Phase 2 - Multi-LLM Debate Engine

---

## Overview

This document defines the comprehensive unit testing strategy for Phase 2 backend and frontend components. Unit tests focus on isolated component behavior with all external dependencies mocked.

**Coverage Target:** 85%+ (higher than Phase 1's 80% due to increased complexity)

---

## 1. Backend Unit Tests (pytest)

### 1.1 Test File Structure

```
tests/backend/phase2/
├── conftest.py                      # Phase 2 fixtures
├── test_debate_service.py           # Debate orchestration
├── test_context_manager.py          # Context window management
├── test_judge_service.py            # Judge evaluation logic
├── test_parallel_streaming.py       # Parallel LLM calls
├── test_cost_calculator.py          # Cost tracking
└── test_debate_state_machine.py     # FSM validation
```

### 1.2 debate_service.py Tests

**File:** `tests/backend/phase2/test_debate_service.py`

**Class Under Test:** `DebateService`

#### Test Cases

**A. Debate Orchestration**

```python
@pytest.mark.unit
class TestDebateService:
    """Test debate orchestration logic"""

    def test_orchestrate_round_simultaneous_mode(
        self, debate_service, mock_debate_config, mock_litellm_responses
    ):
        """Test simultaneous debater response generation"""
        config = mock_debate_config(
            num_debaters=3,
            mode="simultaneous"
        )

        # Mock LiteLLM to return predictable responses
        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = mock_litellm_responses["anthropic_response"]

            result = await debate_service.orchestrate_round(
                config=config,
                round_number=1,
                context_history=[]
            )

        # Assertions
        assert len(result.responses) == 3
        assert all(r.status == "completed" for r in result.responses)
        assert result.round_number == 1
        assert result.duration_ms > 0

        # Verify parallel execution (should be ~simultaneous)
        response_times = [r.timestamp for r in result.responses]
        time_spread = max(response_times) - min(response_times)
        assert time_spread < 500  # Within 500ms of each other

    def test_orchestrate_round_sequential_mode(
        self, debate_service, mock_debate_config
    ):
        """Test sequential debater response generation"""
        config = mock_debate_config(num_debaters=2, mode="sequential")

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = mock_litellm_responses["openai_response"]

            result = await debate_service.orchestrate_round(
                config=config,
                round_number=1,
                context_history=[]
            )

        # Verify sequential execution order
        assert result.responses[0].started_at < result.responses[1].started_at
        assert result.responses[0].completed_at < result.responses[1].started_at

    def test_orchestrate_round_with_context(
        self, debate_service, mock_debate_config, mock_context_history
    ):
        """Test that previous rounds are included in context"""
        config = mock_debate_config(num_debaters=2)

        with mock.patch('litellm.completion') as mock_completion:
            await debate_service.orchestrate_round(
                config=config,
                round_number=2,
                context_history=mock_context_history(num_rounds=1)
            )

            # Verify the prompt includes previous round
            call_args = mock_completion.call_args[1]
            messages = call_args['messages']

            # Should have system prompt + previous round context
            assert len(messages) >= 3
            assert any("round 1" in str(m).lower() for m in messages)

    def test_orchestrate_round_handles_participant_error(
        self, debate_service, mock_debate_config
    ):
        """Test graceful handling of single participant failure"""
        config = mock_debate_config(num_debaters=3)

        # Mock one participant to fail
        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.side_effect = [
                mock_litellm_responses["success"],
                Exception("API Error"),
                mock_litellm_responses["success"]
            ]

            result = await debate_service.orchestrate_round(
                config=config,
                round_number=1,
                context_history=[]
            )

        # Should have 2 successes and 1 error
        assert len([r for r in result.responses if r.status == "completed"]) == 2
        assert len([r for r in result.responses if r.status == "error"]) == 1

        # Error should be captured
        error_response = next(r for r in result.responses if r.status == "error")
        assert error_response.error_message == "API Error"
        assert error_response.retryable == True
```

**B. Error Handling & Recovery**

```python
@pytest.mark.unit
class TestDebateServiceErrors:
    """Test error handling in debate service"""

    def test_handle_rate_limit_error(self, debate_service, mock_debate_config):
        """Test rate limit error is properly categorized"""
        config = mock_debate_config(num_debaters=2)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.side_effect = RateLimitError(
                message="Rate limit exceeded",
                retry_after=60
            )

            result = await debate_service.orchestrate_round(
                config=config, round_number=1, context_history=[]
            )

        assert result.responses[0].status == "rate_limited"
        assert result.responses[0].retry_after == 60
        assert result.responses[0].retryable == True

    def test_handle_context_length_error(
        self, debate_service, mock_debate_config
    ):
        """Test context length exceeded error"""
        config = mock_debate_config(num_debaters=2)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.side_effect = ContextLengthExceededError(
                message="Context too long"
            )

            result = await debate_service.orchestrate_round(
                config=config, round_number=1, context_history=[]
            )

        assert result.responses[0].status == "context_exceeded"
        assert result.responses[0].retryable == False

    def test_handle_authentication_error(
        self, debate_service, mock_debate_config
    ):
        """Test authentication error is non-retryable"""
        config = mock_debate_config(num_debaters=2)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.side_effect = AuthenticationError(
                message="Invalid API key"
            )

            result = await debate_service.orchestrate_round(
                config=config, round_number=1, context_history=[]
            )

        assert result.responses[0].status == "authentication_error"
        assert result.responses[0].retryable == False
```

**C. Cost Tracking**

```python
@pytest.mark.unit
class TestDebateServiceCostTracking:
    """Test cost calculation during debate execution"""

    def test_track_costs_per_participant(
        self, debate_service, mock_debate_config
    ):
        """Test that costs are tracked per participant"""
        config = mock_debate_config(num_debaters=3)

        # Mock responses with token counts
        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                usage={
                    "prompt_tokens": 500,
                    "completion_tokens": 300,
                    "total_tokens": 800
                }
            )

            result = await debate_service.orchestrate_round(
                config=config, round_number=1, context_history=[]
            )

        # Each participant should have cost data
        for response in result.responses:
            assert response.token_usage.prompt_tokens == 500
            assert response.token_usage.completion_tokens == 300
            assert response.cost_usd > 0

    def test_calculate_total_debate_cost(
        self, debate_service, mock_completed_debate
    ):
        """Test total debate cost calculation"""
        debate = mock_completed_debate(num_rounds=3, num_debaters=2)

        total_cost = debate_service.calculate_total_cost(debate)

        # Should sum all participant costs + judge costs
        expected_cost = (
            sum(r.cost_usd for round in debate.rounds for r in round.responses) +
            sum(a.cost_usd for a in debate.judge.assessments) +
            debate.judge.final_verdict.cost_usd
        )

        assert total_cost == expected_cost
        assert total_cost > 0
```

### 1.3 context_manager.py Tests

**File:** `tests/backend/phase2/test_context_manager.py`

**Class Under Test:** `ContextManager`

#### Test Cases

```python
@pytest.mark.unit
class TestContextManager:
    """Test context window management"""

    def test_sliding_window_basic(self, context_manager):
        """Test basic sliding window functionality"""
        history = create_mock_history(num_rounds=10)
        config = ContextConfig(max_tokens=4096, window_size=3)

        windowed = context_manager.apply_sliding_window(history, config)

        # Should only keep last 3 rounds
        assert len(windowed) == 3
        assert windowed[0].round_number == 8
        assert windowed[-1].round_number == 10

    def test_estimate_token_count(self, context_manager):
        """Test token estimation for context"""
        messages = [
            {"role": "system", "content": "You are a debater."},
            {"role": "user", "content": "What is your position?"},
            {"role": "assistant", "content": "I believe that..."}
        ]

        token_count = context_manager.estimate_token_count(messages)

        # Should be reasonable estimate (not exact, uses approximation)
        assert 10 < token_count < 50

    def test_context_overflow_detection(self, context_manager):
        """Test detection of context overflow"""
        # Create very long history
        history = create_mock_history(
            num_rounds=50,
            avg_response_length=2000
        )
        config = ContextConfig(max_tokens=4096)

        overflow = context_manager.detect_overflow(history, config)

        assert overflow.is_overflowing == True
        assert overflow.current_tokens > config.max_tokens
        assert overflow.excess_tokens > 0

    def test_summarization_strategy(self, context_manager):
        """Test context summarization strategy"""
        long_history = create_mock_history(num_rounds=20)
        config = ContextConfig(max_tokens=4096, summarize=True)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                content="Summary: Key points from rounds 1-15..."
            )

            result = context_manager.apply_summarization(long_history, config)

        # Should have summary + recent rounds
        assert result.has_summary == True
        assert len(result.summary_text) > 0
        assert len(result.recent_rounds) < len(long_history)

    def test_cost_calculation_from_tokens(self, context_manager):
        """Test cost calculation from token counts"""
        tokens = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )

        # Anthropic Claude Sonnet pricing
        cost = context_manager.calculate_cost(
            tokens=tokens,
            model="claude-3-5-sonnet-20241022"
        )

        # $3/$15 per million tokens (input/output)
        expected_input_cost = (1000 / 1_000_000) * 3
        expected_output_cost = (500 / 1_000_000) * 15
        expected_total = expected_input_cost + expected_output_cost

        assert abs(cost - expected_total) < 0.0001

    def test_different_model_pricing(self, context_manager):
        """Test that different models have different pricing"""
        tokens = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )

        sonnet_cost = context_manager.calculate_cost(
            tokens, "claude-3-5-sonnet-20241022"
        )
        haiku_cost = context_manager.calculate_cost(
            tokens, "claude-3-5-haiku-20241022"
        )

        # Haiku is cheaper
        assert haiku_cost < sonnet_cost
```

### 1.4 judge_service.py Tests

**File:** `tests/backend/phase2/test_judge_service.py`

**Class Under Test:** `JudgeService`

#### Test Cases

```python
@pytest.mark.unit
class TestJudgeService:
    """Test judge evaluation logic"""

    def test_evaluate_round_basic(self, judge_service, mock_round_data):
        """Test basic round evaluation"""
        round_data = mock_round_data(num_participants=2)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                content=json.dumps({
                    "quality_scores": [
                        {"participant_id": "p1", "score": 8.5},
                        {"participant_id": "p2", "score": 7.0}
                    ],
                    "round_summary": "Strong arguments from both sides.",
                    "should_continue": True,
                    "flags": {
                        "convergence_reached": False,
                        "diminishing_returns": False,
                        "repetition_detected": False
                    }
                })
            )

            assessment = await judge_service.evaluate_round(round_data)

        assert len(assessment.quality_scores) == 2
        assert assessment.quality_scores[0].score == 8.5
        assert assessment.should_continue == True
        assert assessment.round_summary == "Strong arguments from both sides."

    def test_detect_convergence(self, judge_service, mock_converging_debate):
        """Test convergence detection"""
        debate = mock_converging_debate()

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                content=json.dumps({
                    "quality_scores": [...],
                    "round_summary": "Participants are reaching agreement.",
                    "should_continue": False,
                    "flags": {
                        "convergence_reached": True,
                        "diminishing_returns": False,
                        "repetition_detected": False
                    }
                })
            )

            assessment = await judge_service.evaluate_round(
                debate.rounds[-1]
            )

        assert assessment.flags.convergence_reached == True
        assert assessment.should_continue == False

    def test_detect_repetition(self, judge_service, mock_repetitive_round):
        """Test repetition detection"""
        round_data = mock_repetitive_round()

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                content=json.dumps({
                    "quality_scores": [...],
                    "round_summary": "Arguments are repeating.",
                    "should_continue": False,
                    "flags": {
                        "convergence_reached": False,
                        "diminishing_returns": True,
                        "repetition_detected": True
                    }
                })
            )

            assessment = await judge_service.evaluate_round(round_data)

        assert assessment.flags.repetition_detected == True
        assert assessment.should_continue == False

    def test_generate_final_verdict(self, judge_service, mock_debate):
        """Test final verdict generation"""
        debate = mock_debate(num_rounds=5)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                content=json.dumps({
                    "summary": "The debate covered...",
                    "key_points": ["Point 1", "Point 2"],
                    "areas_of_agreement": ["Both agreed on..."],
                    "areas_of_disagreement": ["They differed on..."],
                    "winner": {
                        "participant_id": "p1",
                        "reasoning": "Strongest arguments"
                    },
                    "verdict": "Overall assessment..."
                })
            )

            verdict = await judge_service.generate_final_verdict(debate)

        assert verdict.summary is not None
        assert len(verdict.key_points) > 0
        assert verdict.winner is not None
        assert verdict.winner.participant_id == "p1"

    def test_structured_output_validation(self, judge_service):
        """Test that judge output matches expected schema"""
        round_data = mock_round_data(num_participants=3)

        with mock.patch('litellm.completion') as mock_completion:
            # Invalid response missing required fields
            mock_completion.return_value = MockResponse(
                content=json.dumps({
                    "quality_scores": []  # Missing other fields
                })
            )

            with pytest.raises(ValidationError):
                await judge_service.evaluate_round(round_data)

    def test_rubric_evaluation_criteria(self, judge_service):
        """Test that judge evaluates based on rubric"""
        round_data = mock_round_data(num_participants=2)
        rubric = EvaluationRubric(
            criteria=[
                {"name": "Clarity", "weight": 0.3},
                {"name": "Evidence", "weight": 0.5},
                {"name": "Logic", "weight": 0.2}
            ]
        )

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MockResponse(
                content=json.dumps({
                    "quality_scores": [
                        {
                            "participant_id": "p1",
                            "score": 8.0,
                            "criteria_scores": {
                                "Clarity": 9.0,
                                "Evidence": 8.0,
                                "Logic": 7.5
                            }
                        }
                    ],
                    "round_summary": "...",
                    "should_continue": True,
                    "flags": {}
                })
            )

            assessment = await judge_service.evaluate_round(
                round_data, rubric=rubric
            )

        # Verify weighted scoring was applied
        participant_score = assessment.quality_scores[0]
        assert "Clarity" in participant_score.criteria_scores
        assert "Evidence" in participant_score.criteria_scores
```

### 1.5 parallel_streaming.py Tests

**File:** `tests/backend/phase2/test_parallel_streaming.py`

#### Test Cases

```python
@pytest.mark.unit
@pytest.mark.asyncio
class TestParallelStreaming:
    """Test parallel LLM streaming functionality"""

    async def test_parallel_streaming_multiple_debaters(
        self, streaming_service, mock_debate_config
    ):
        """Test streaming from multiple debaters simultaneously"""
        config = mock_debate_config(num_debaters=4)

        # Mock streaming responses
        async def mock_stream_generator(participant_id):
            chunks = ["This ", "is ", "response ", f"from {participant_id}"]
            for chunk in chunks:
                yield {"content": chunk, "participant_id": participant_id}
                await asyncio.sleep(0.01)

        streams = await streaming_service.create_parallel_streams(
            config, round_number=1
        )

        # Should have 4 active streams
        assert len(streams) == 4

        # Collect all chunks
        results = await streaming_service.collect_all_streams(streams)

        assert len(results) == 4
        for result in results:
            assert "response from" in result.full_text

    async def test_streaming_error_isolation(
        self, streaming_service, mock_debate_config
    ):
        """Test that one stream error doesn't affect others"""
        config = mock_debate_config(num_debaters=3)

        # Mock one stream to fail
        async def failing_stream(participant_id):
            if participant_id == "p2":
                raise Exception("Stream error")
            chunks = ["Normal ", "response"]
            for chunk in chunks:
                yield {"content": chunk, "participant_id": participant_id}

        with mock.patch.object(
            streaming_service,
            '_create_stream',
            side_effect=failing_stream
        ):
            streams = await streaming_service.create_parallel_streams(
                config, round_number=1
            )
            results = await streaming_service.collect_all_streams(streams)

        # Should have 2 successes and 1 error
        successful = [r for r in results if r.status == "completed"]
        errored = [r for r in results if r.status == "error"]

        assert len(successful) == 2
        assert len(errored) == 1
```

### 1.6 Pytest Markers & Configuration

**File:** `tests/pytest.ini` (update)

```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests
    e2e: End-to-end tests
    sse: Server-sent events tests
    debate: Debate engine tests (Phase 2)
    judge: Judge service tests (Phase 2)
    parallel: Parallel streaming tests (Phase 2)
    slow: Tests that take >1 second
    security: Security-related tests

asyncio_mode = auto
```

---

## 2. Frontend Unit Tests (Vitest)

### 2.1 Test File Structure

```
tests/frontend/phase2/
├── setup.ts                              # Phase 2 test setup
├── stores/
│   └── debate-store.test.ts              # Debate state management
├── hooks/
│   ├── useParallelStreaming.test.ts      # Parallel SSE hooks
│   └── useCostTracker.test.ts            # Cost tracking hook
├── components/
│   ├── DebateConfigPanel.test.tsx        # Configuration UI
│   ├── DebateArena.test.tsx              # Main debate interface
│   ├── ParticipantCard.test.tsx          # Individual debater display
│   ├── JudgeAssessment.test.tsx          # Judge verdict display
│   └── CostTracker.test.tsx              # Cost display component
└── utils/
    ├── cost-calculator.test.ts           # Cost calculation utilities
    └── debate-export.test.ts             # Export functionality
```

### 2.2 debate-store.test.ts

```typescript
describe('DebateStore', () => {
  beforeEach(() => {
    // Reset store state
    useDebateStore.setState({
      debates: {},
      activeDebateId: null,
      status: 'configuring'
    });
  });

  it('should initialize new debate', () => {
    const { initializeDebate } = useDebateStore.getState();

    const debateId = initializeDebate({
      topic: "Test topic",
      participants: [
        { id: "p1", model: "claude-3-5-sonnet-20241022" },
        { id: "p2", model: "gpt-4" }
      ],
      judge: { model: "claude-3-opus-20240229" }
    });

    const state = useDebateStore.getState();
    expect(state.debates[debateId]).toBeDefined();
    expect(state.debates[debateId].status).toBe('ready');
    expect(state.debates[debateId].participants).toHaveLength(2);
  });

  it('should update participant response during streaming', () => {
    const { initializeDebate, updateParticipantStream } =
      useDebateStore.getState();

    const debateId = initializeDebate(mockConfig);

    updateParticipantStream(
      debateId,
      'p1',
      { content: 'Hello', isComplete: false }
    );

    const debate = useDebateStore.getState().debates[debateId];
    const participant = debate.participants.find(p => p.id === 'p1');

    expect(participant?.currentResponse).toBe('Hello');
    expect(participant?.isStreaming).toBe(true);
  });

  it('should track costs correctly', () => {
    const { initializeDebate, updateParticipantCost } =
      useDebateStore.getState();

    const debateId = initializeDebate(mockConfig);

    // Add costs for participants
    updateParticipantCost(debateId, 'p1', {
      promptTokens: 1000,
      completionTokens: 500,
      costUsd: 0.0225
    });

    updateParticipantCost(debateId, 'p2', {
      promptTokens: 1200,
      completionTokens: 600,
      costUsd: 0.027
    });

    const debate = useDebateStore.getState().debates[debateId];
    const totalCost = debate.totalCost;

    expect(totalCost).toBeCloseTo(0.0495, 4);
  });

  it('should handle debate state transitions', async () => {
    const { initializeDebate, startDebate, pauseDebate } =
      useDebateStore.getState();

    const debateId = initializeDebate(mockConfig);

    // Start debate
    await startDebate(debateId);
    expect(useDebateStore.getState().debates[debateId].status)
      .toBe('running');

    // Pause debate
    pauseDebate(debateId);
    expect(useDebateStore.getState().debates[debateId].status)
      .toBe('paused');
  });
});
```

### 2.3 useParallelStreaming.test.ts

```typescript
describe('useParallelStreaming', () => {
  it('should establish multiple SSE connections', () => {
    const { result } = renderHook(() =>
      useParallelStreaming({
        debateId: 'test-debate',
        participantIds: ['p1', 'p2', 'p3'],
        onMessage: vi.fn()
      })
    );

    expect(result.current.streams).toHaveLength(3);
    expect(result.current.allConnected).toBe(true);
  });

  it('should handle individual stream errors', () => {
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useParallelStreaming({
        debateId: 'test-debate',
        participantIds: ['p1', 'p2'],
        onError
      })
    );

    // Simulate error on one stream
    const mockError = new Error('Stream failed');
    act(() => {
      result.current.streams[0].simulateError(mockError);
    });

    expect(onError).toHaveBeenCalledWith('p1', mockError);
    expect(result.current.streams[0].status).toBe('error');

    // Other stream should still be active
    expect(result.current.streams[1].status).toBe('connected');
  });

  it('should cleanup connections on unmount', () => {
    const { result, unmount } = renderHook(() =>
      useParallelStreaming({
        debateId: 'test-debate',
        participantIds: ['p1', 'p2']
      })
    );

    const closeSpy = vi.spyOn(result.current.streams[0], 'close');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });
});
```

### 2.4 Component Tests

```typescript
describe('DebateArena', () => {
  it('should render all participants', () => {
    const debate = mockDebate({ numParticipants: 4 });

    render(<DebateArena debate={debate} />);

    expect(screen.getAllByTestId('participant-card')).toHaveLength(4);
  });

  it('should display streaming responses in real-time', async () => {
    const debate = mockDebate({ numParticipants: 2 });

    render(<DebateArena debate={debate} />);

    // Simulate streaming chunk
    act(() => {
      useDebateStore.getState().updateParticipantStream(
        debate.id,
        'p1',
        { content: 'I think ', isComplete: false }
      );
    });

    expect(screen.getByText(/I think/)).toBeInTheDocument();

    // Simulate more chunks
    act(() => {
      useDebateStore.getState().updateParticipantStream(
        debate.id,
        'p1',
        { content: 'I think that...', isComplete: true }
      );
    });

    expect(screen.getByText(/I think that.../)).toBeInTheDocument();
  });

  it('should show judge assessment after round', async () => {
    const debate = mockDebate({ currentRound: 1 });

    render(<DebateArena debate={debate} />);

    // Add judge assessment
    act(() => {
      useDebateStore.getState().addJudgeAssessment(
        debate.id,
        mockJudgeAssessment()
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('judge-assessment')).toBeInTheDocument();
    });
  });
});

describe('CostTracker', () => {
  it('should display real-time cost updates', () => {
    const debate = mockDebate();

    const { rerender } = render(<CostTracker debate={debate} />);

    expect(screen.getByText(/\$0.00/)).toBeInTheDocument();

    // Update costs
    debate.totalCost = 0.15;
    rerender(<CostTracker debate={debate} />);

    expect(screen.getByText(/\$0.15/)).toBeInTheDocument();
  });

  it('should show cost warning when threshold exceeded', () => {
    const debate = mockDebate({ totalCost: 5.50 });

    render(<CostTracker debate={debate} warningThreshold={5.00} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Cost warning/i)).toBeInTheDocument();
  });
});
```

---

## 3. Test Fixtures & Mocks

### 3.1 Backend Fixtures (conftest.py)

```python
# tests/backend/phase2/conftest.py

@pytest.fixture
def mock_debate_config():
    """Factory for creating mock debate configurations"""
    def _factory(
        num_debaters: int = 2,
        mode: str = "simultaneous",
        format: str = "free-form"
    ):
        return DebateConfig(
            topic="Test debate topic",
            participants=[
                ParticipantConfig(
                    id=f"p{i}",
                    model="claude-3-5-sonnet-20241022",
                    persona="Debater"
                )
                for i in range(1, num_debaters + 1)
            ],
            judge=JudgeConfig(
                model="claude-3-opus-20240229",
                rubric=default_rubric()
            ),
            mode=mode,
            format=format
        )
    return _factory

@pytest.fixture
def mock_litellm_responses():
    """Mock LiteLLM API responses"""
    return {
        "anthropic_response": MockStreamResponse(
            id="msg_123",
            model="claude-3-5-sonnet-20241022",
            content="This is a test response.",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        ),
        "openai_response": MockStreamResponse(
            id="chatcmpl_123",
            model="gpt-4",
            content="This is another test response.",
            usage={
                "prompt_tokens": 120,
                "completion_tokens": 60,
                "total_tokens": 180
            }
        )
    }
```

### 3.2 Frontend Mocks (setup.ts)

```typescript
// tests/frontend/phase2/setup.ts

export class MockEventSource {
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState: number = 1; // OPEN

  constructor(url: string) {
    this.url = url;
  }

  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', {
        data: JSON.stringify(data)
      }));
    }
  }

  simulateError(error: Error) {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  close() {
    this.readyState = 2; // CLOSED
  }
}

// Mock multiple EventSource instances
global.EventSource = vi.fn().mockImplementation((url) => {
  return new MockEventSource(url);
});
```

---

## 4. Coverage Requirements

| Component | Target | Priority |
|-----------|--------|----------|
| debate_service.py | 90%+ | Critical |
| context_manager.py | 90%+ | Critical |
| judge_service.py | 85%+ | High |
| parallel_streaming.py | 85%+ | High |
| debate-store.ts | 90%+ | Critical |
| useParallelStreaming.ts | 85%+ | High |
| Components | 80%+ | Medium |

---

## 5. Running Tests

### Backend

```bash
# Run all Phase 2 unit tests
pytest tests/backend/phase2/ -m "unit"

# Run with coverage
pytest tests/backend/phase2/ --cov=backend/app/services --cov=backend/app/models

# Run specific test file
pytest tests/backend/phase2/test_debate_service.py -v

# Run parallel tests
pytest tests/backend/phase2/ -m "parallel" -v
```

### Frontend

```bash
# Run all Phase 2 tests
npm run test:phase2

# Run with coverage
npm run test:coverage -- tests/frontend/phase2/

# Watch mode
npm run test:watch tests/frontend/phase2/

# Run specific test
npm run test debate-store.test.ts
```

---

## 6. Next Steps

1. **Implementation**: Implement source code matching test specifications
2. **Mock Refinement**: Adjust mocks based on actual LiteLLM behavior
3. **CI Integration**: Add Phase 2 tests to GitHub Actions
4. **Coverage Monitoring**: Track coverage trends over time

---

**Status:** ✅ Ready for Implementation
**Estimated Test Count:** 150+ unit tests
**Estimated Coverage:** 85%+ across all components
