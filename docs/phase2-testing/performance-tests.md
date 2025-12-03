# Phase 2 Performance Test Plan - Multi-LLM Debate Engine

**Date:** 2025-12-02
**Agent:** Test Engineer
**Phase:** Phase 2 - Multi-LLM Debate Engine

---

## Overview

Performance testing ensures the debate engine scales efficiently under load and maintains acceptable latency. These tests measure backend overhead, memory usage, concurrent handling, and cost calculation accuracy.

**Test Tools:** pytest-benchmark, locust, memory_profiler

---

## 1. Performance Test Categories

```
tests/performance/phase2/
├── conftest.py                       # Performance fixtures
├── test_latency.py                   # Latency benchmarks
├── test_memory.py                    # Memory usage tests
├── test_concurrent.py                # Concurrent debate handling
├── test_token_accuracy.py            # Token counting accuracy
└── test_cost_accuracy.py             # Cost calculation accuracy
```

---

## 2. Latency Benchmarks

**Target:** <10ms backend overhead per debater

**File:** `tests/performance/phase2/test_latency.py`

```python
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

@pytest.mark.performance
class TestLatencyBenchmarks:
    """Test backend latency and overhead"""

    def test_debate_orchestration_overhead(
        self, benchmark: BenchmarkFixture, mock_debate_service, mock_config
    ):
        """Measure time to orchestrate round (excluding LLM API time)"""

        config = mock_config(num_debaters=2)

        # Mock LiteLLM to return instantly (measure only orchestration time)
        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = instant_response()

            result = benchmark(
                lambda: asyncio.run(
                    mock_debate_service.orchestrate_round(
                        config, round_number=1, context_history=[]
                    )
                )
            )

        # Verify overhead is minimal
        assert benchmark.stats['mean'] < 0.010  # <10ms mean
        assert benchmark.stats['max'] < 0.050   # <50ms max

    def test_parallel_streaming_setup_time(
        self, benchmark: BenchmarkFixture, streaming_service, mock_config
    ):
        """Measure time to set up parallel streams"""

        config = mock_config(num_debaters=4)

        result = benchmark(
            lambda: asyncio.run(
                streaming_service.create_parallel_streams(config, round_number=1)
            )
        )

        # Setup should be fast
        assert benchmark.stats['mean'] < 0.020  # <20ms mean

    def test_context_management_overhead(
        self, benchmark: BenchmarkFixture, context_manager, large_history
    ):
        """Measure context window processing time"""

        history = large_history(num_rounds=20)
        config = ContextConfig(max_tokens=4096, window_size=5)

        result = benchmark(
            lambda: context_manager.apply_sliding_window(history, config)
        )

        # Context management should be fast
        assert benchmark.stats['mean'] < 0.005  # <5ms mean

    def test_judge_assessment_overhead(
        self, benchmark: BenchmarkFixture, judge_service, mock_round_data
    ):
        """Measure judge assessment processing time (excluding LLM call)"""

        round_data = mock_round_data(num_participants=4)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = instant_judge_response()

            result = benchmark(
                lambda: asyncio.run(
                    judge_service.evaluate_round(round_data)
                )
            )

        # Assessment overhead should be minimal
        assert benchmark.stats['mean'] < 0.015  # <15ms mean

    def test_cost_calculation_performance(
        self, benchmark: BenchmarkFixture, context_manager
    ):
        """Measure cost calculation speed"""

        tokens = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )

        result = benchmark(
            lambda: context_manager.calculate_cost(
                tokens, "claude-3-5-sonnet-20241022"
            )
        )

        # Cost calculation should be instant
        assert benchmark.stats['mean'] < 0.001  # <1ms mean

    @pytest.mark.parametrize("num_debaters", [2, 3, 4])
    def test_orchestration_scales_linearly(
        self, benchmark: BenchmarkFixture, mock_debate_service, num_debaters
    ):
        """Verify orchestration time scales linearly with debater count"""

        config = mock_config(num_debaters=num_debaters)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = instant_response()

            result = benchmark(
                lambda: asyncio.run(
                    mock_debate_service.orchestrate_round(
                        config, round_number=1, context_history=[]
                    )
                )
            )

        # Store results for comparison
        # Time should scale ~linearly (within 2x for 2x debaters)
        pass  # Results logged by pytest-benchmark
```

---

## 3. Memory Usage Tests

**Target:** <100MB per debate with 4 simultaneous streams

**File:** `tests/performance/phase2/test_memory.py`

```python
import pytest
from memory_profiler import profile, memory_usage

@pytest.mark.performance
class TestMemoryUsage:
    """Test memory consumption during debate execution"""

    def test_debate_memory_footprint(self, mock_debate_service, mock_config):
        """Measure memory used by complete debate"""

        config = mock_config(num_debaters=4)

        # Measure memory before
        import gc
        gc.collect()
        mem_before = memory_usage()[0]

        # Run debate
        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = mock_response()

            asyncio.run(
                mock_debate_service.run_complete_debate(
                    config, num_rounds=5
                )
            )

        # Measure memory after
        gc.collect()
        mem_after = memory_usage()[0]

        memory_used = mem_after - mem_before

        # Should use <100MB for full debate
        assert memory_used < 100.0  # MB

        # Log for tracking
        print(f"Memory used: {memory_used:.2f} MB")

    def test_streaming_memory_per_debater(
        self, streaming_service, mock_config
    ):
        """Measure memory per active stream"""

        config = mock_config(num_debaters=4)

        mem_before = memory_usage()[0]

        # Create 4 active streams
        streams = asyncio.run(
            streaming_service.create_parallel_streams(config, round_number=1)
        )

        mem_after = memory_usage()[0]
        memory_per_stream = (mem_after - mem_before) / 4

        # Each stream should use <10MB
        assert memory_per_stream < 10.0  # MB

        print(f"Memory per stream: {memory_per_stream:.2f} MB")

    def test_context_history_memory_growth(
        self, context_manager, mock_debate_config
    ):
        """Test memory growth with increasing context history"""

        config = mock_debate_config()

        memories = []
        for num_rounds in [5, 10, 20, 50]:
            history = create_mock_history(num_rounds)

            mem_before = memory_usage()[0]
            windowed = context_manager.apply_sliding_window(
                history,
                ContextConfig(max_tokens=4096, window_size=5)
            )
            mem_after = memory_usage()[0]

            memories.append((num_rounds, mem_after - mem_before))

        # With sliding window, memory should NOT grow linearly
        # Memory at 50 rounds should be <2x memory at 5 rounds
        mem_5_rounds = memories[0][1]
        mem_50_rounds = memories[-1][1]

        assert mem_50_rounds < mem_5_rounds * 2

        print("Memory growth:")
        for rounds, mem in memories:
            print(f"  {rounds} rounds: {mem:.2f} MB")

    @profile
    def test_judge_assessment_memory(self, judge_service, mock_round_data):
        """Profile memory during judge assessment"""

        round_data = mock_round_data(num_participants=4)

        with mock.patch('litellm.completion') as mock_completion:
            mock_completion.return_value = mock_judge_response()

            asyncio.run(judge_service.evaluate_round(round_data))

        # Memory profile printed by @profile decorator
        pass

    def test_memory_cleanup_after_debate(
        self, mock_debate_service, mock_config
    ):
        """Verify memory is freed after debate completion"""

        config = mock_config(num_debaters=4)

        import gc
        gc.collect()
        mem_baseline = memory_usage()[0]

        # Run multiple debates
        for i in range(3):
            asyncio.run(
                mock_debate_service.run_complete_debate(
                    config, num_rounds=3
                )
            )

        # Force garbage collection
        gc.collect()
        mem_after = memory_usage()[0]

        # Memory should return close to baseline
        memory_retained = mem_after - mem_baseline

        assert memory_retained < 50.0  # <50MB retained

        print(f"Memory retained after 3 debates: {memory_retained:.2f} MB")
```

---

## 4. Concurrent Debate Handling

**Target:** Handle 5+ simultaneous debates

**File:** `tests/performance/phase2/test_concurrent.py`

```python
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentDebates:
    """Test system handling multiple debates simultaneously"""

    async def test_5_concurrent_debates(self, client, mock_litellm_provider):
        """Test 5 debates running concurrently"""

        debate_ids = []

        # Create 5 debates
        for i in range(5):
            response = await client.post("/api/debates/configure", json={
                "topic": f"Debate {i}",
                "participants": [
                    {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                    {"model": "gpt-4", "persona": "B"}
                ],
                "judge": {"model": "claude-3-opus-20240229"},
                "format": "round-limited",
                "round_limit": 2
            })

            debate_ids.append(response.json()["debate_id"])

        # Start all debates concurrently
        start_time = time.time()

        start_tasks = [
            client.post(f"/api/debates/{debate_id}/start")
            for debate_id in debate_ids
        ]

        await asyncio.gather(*start_tasks)

        # Wait for all to complete
        while True:
            statuses = await asyncio.gather(*[
                client.get(f"/api/debates/{debate_id}/status")
                for debate_id in debate_ids
            ])

            status_values = [s.json()["status"] for s in statuses]

            if all(s == "completed" for s in status_values):
                break

            await asyncio.sleep(1)

        total_time = time.time() - start_time

        # All should complete within reasonable time
        assert total_time < 120  # <2 minutes for 5 debates

        print(f"5 concurrent debates completed in {total_time:.2f}s")

    async def test_concurrent_streaming_connections(
        self, client, mock_litellm_provider
    ):
        """Test multiple simultaneous SSE connections"""

        # Create debate
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"}
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Open 10 SSE connections simultaneously (simulating multiple clients)
        async def consume_stream(client_id):
            events = []
            async with client.stream(
                "GET",
                f"/api/debates/{debate_id}/stream"
            ) as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

                        if len(events) > 10:  # Consume some events
                            break

            return events

        # Run 10 concurrent consumers
        results = await asyncio.gather(*[
            consume_stream(i) for i in range(10)
        ])

        # All should receive events
        assert all(len(events) > 0 for events in results)

        print(f"10 concurrent SSE connections handled successfully")

    def test_debate_queue_capacity(self, client, mock_litellm_provider):
        """Test maximum debate queue capacity"""

        # Create many debates rapidly
        debate_ids = []

        for i in range(20):
            response = client.post("/api/debates/configure", json={
                "topic": f"Debate {i}",
                "participants": [...],
                "judge": {...}
            })

            debate_ids.append(response.json()["debate_id"])

        # Start all
        for debate_id in debate_ids:
            response = client.post(f"/api/debates/{debate_id}/start")
            assert response.status_code in [200, 202]  # 202 = queued

        # Verify system doesn't crash
        health = client.get("/health")
        assert health.status_code == 200
```

---

## 5. Token Counting Accuracy

**Target:** Within 1% of provider counts

**File:** `tests/performance/phase2/test_token_accuracy.py`

```python
import pytest
import tiktoken

@pytest.mark.performance
class TestTokenAccuracy:
    """Test token counting accuracy"""

    def test_token_estimation_accuracy(self, context_manager):
        """Test token estimation matches tiktoken"""

        test_texts = [
            "Simple test message.",
            "A longer message with more tokens to count accurately.",
            "Technical content: async/await, React.FC<Props>, TypeScript generics",
            "Very long " + "message " * 100
        ]

        # Use tiktoken as ground truth
        encoder = tiktoken.encoding_for_model("gpt-4")

        for text in test_texts:
            estimated = context_manager.estimate_token_count([
                {"role": "user", "content": text}
            ])

            actual = len(encoder.encode(text))

            # Should be within 5% for short texts, 2% for long texts
            margin = 0.05 if len(text) < 100 else 0.02
            acceptable_range = (actual * (1 - margin), actual * (1 + margin))

            assert acceptable_range[0] <= estimated <= acceptable_range[1], \
                f"Estimated {estimated} not within {margin*100}% of actual {actual}"

    def test_context_window_token_calculation(
        self, context_manager, large_history
    ):
        """Test accurate token counting for large context windows"""

        history = large_history(num_rounds=10)

        # Calculate tokens
        total_tokens = context_manager.calculate_total_tokens(history)

        # Verify by encoding with tiktoken
        encoder = tiktoken.encoding_for_model("gpt-4")

        all_text = ""
        for round in history:
            for response in round.responses:
                all_text += response.content

        actual_tokens = len(encoder.encode(all_text))

        # Should be within 2%
        margin = 0.02
        acceptable_range = (actual_tokens * (1 - margin), actual_tokens * (1 + margin))

        assert acceptable_range[0] <= total_tokens <= acceptable_range[1]

    @pytest.mark.parametrize("model", [
        "claude-3-5-sonnet-20241022",
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-5-haiku-20241022"
    ])
    def test_token_counting_per_model(self, context_manager, model):
        """Test token counting for different models"""

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."}
        ]

        tokens = context_manager.estimate_token_count(messages, model=model)

        # Should return reasonable count (10-50 tokens)
        assert 10 < tokens < 50

        print(f"{model}: {tokens} tokens")
```

---

## 6. Cost Calculation Accuracy

**Target:** Exact match with provider pricing

**File:** `tests/performance/phase2/test_cost_accuracy.py`

```python
import pytest

@pytest.mark.performance
class TestCostAccuracy:
    """Test cost calculation accuracy"""

    def test_claude_sonnet_pricing(self, context_manager):
        """Test Claude 3.5 Sonnet cost calculation"""

        tokens = TokenUsage(
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000
        )

        cost = context_manager.calculate_cost(
            tokens, "claude-3-5-sonnet-20241022"
        )

        # Sonnet: $3/$15 per million tokens
        expected_cost = (1_000_000 / 1_000_000 * 3) + (1_000_000 / 1_000_000 * 15)
        assert cost == expected_cost  # Exact match

    def test_claude_haiku_pricing(self, context_manager):
        """Test Claude 3.5 Haiku cost calculation"""

        tokens = TokenUsage(
            prompt_tokens=500_000,
            completion_tokens=250_000,
            total_tokens=750_000
        )

        cost = context_manager.calculate_cost(
            tokens, "claude-3-5-haiku-20241022"
        )

        # Haiku: $0.80/$4 per million tokens
        expected_cost = (500_000 / 1_000_000 * 0.80) + (250_000 / 1_000_000 * 4)
        assert abs(cost - expected_cost) < 0.0001  # Within $0.0001

    def test_gpt4_pricing(self, context_manager):
        """Test GPT-4 cost calculation"""

        tokens = TokenUsage(
            prompt_tokens=100_000,
            completion_tokens=50_000,
            total_tokens=150_000
        )

        cost = context_manager.calculate_cost(tokens, "gpt-4")

        # GPT-4: $30/$60 per million tokens (approximate)
        expected_cost = (100_000 / 1_000_000 * 30) + (50_000 / 1_000_000 * 60)
        assert abs(cost - expected_cost) < 0.001

    def test_total_debate_cost_accuracy(
        self, debate_service, mock_completed_debate
    ):
        """Test total debate cost calculation"""

        debate = mock_completed_debate(
            num_rounds=3,
            num_debaters=2,
            tokens_per_response=(1000, 500)  # Fixed token counts
        )

        total_cost = debate_service.calculate_total_cost(debate)

        # Manually calculate expected cost
        # 3 rounds * 2 debaters * cost_per_response
        # + 3 judge assessments * cost_per_assessment
        # + 1 final verdict * cost_per_verdict

        debater_cost = 3 * 2 * calculate_response_cost(1000, 500, "claude-3-5-sonnet-20241022")
        judge_cost = 3 * calculate_response_cost(1000, 500, "claude-3-opus-20240229")
        verdict_cost = calculate_response_cost(2000, 1000, "claude-3-opus-20240229")

        expected_total = debater_cost + judge_cost + verdict_cost

        # Should match exactly
        assert abs(total_cost - expected_total) < 0.0001

    @pytest.mark.parametrize("token_counts", [
        (100, 50),
        (1000, 500),
        (10000, 5000),
        (100000, 50000)
    ])
    def test_cost_calculation_at_scale(
        self, context_manager, token_counts
    ):
        """Test cost calculation for different scales"""

        prompt_tokens, completion_tokens = token_counts

        tokens = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )

        cost = context_manager.calculate_cost(
            tokens, "claude-3-5-sonnet-20241022"
        )

        # Verify cost scales linearly
        expected_cost = (
            (prompt_tokens / 1_000_000) * 3 +
            (completion_tokens / 1_000_000) * 15
        )

        assert abs(cost - expected_cost) < 0.0001

        print(f"{prompt_tokens}/{completion_tokens} tokens: ${cost:.4f}")
```

---

## 7. Load Testing with Locust

**File:** `tests/performance/phase2/locustfile.py`

```python
from locust import HttpUser, task, between
import json

class DebateUser(HttpUser):
    """Simulated user running debates"""

    wait_time = between(1, 5)

    def on_start(self):
        """Initialize user session"""
        self.debate_id = None

    @task(1)
    def create_debate(self):
        """Create new debate"""
        response = self.client.post("/api/debates/configure", json={
            "topic": "Performance test debate",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "round-limited",
            "round_limit": 2
        })

        if response.status_code == 200:
            self.debate_id = response.json()["debate_id"]

    @task(2)
    def start_debate(self):
        """Start debate"""
        if self.debate_id:
            self.client.post(f"/api/debates/{self.debate_id}/start")

    @task(3)
    def check_status(self):
        """Check debate status"""
        if self.debate_id:
            self.client.get(f"/api/debates/{self.debate_id}/status")

    @task(1)
    def get_debate(self):
        """Get debate details"""
        if self.debate_id:
            self.client.get(f"/api/debates/{self.debate_id}")
```

**Run Load Test:**

```bash
# Run with 10 users
locust -f tests/performance/phase2/locustfile.py --users 10 --spawn-rate 2

# Run headless with report
locust -f tests/performance/phase2/locustfile.py \
  --users 50 --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --html tests/coverage/performance/locust-report.html
```

---

## 8. Running Performance Tests

```bash
# Run all performance tests
pytest tests/performance/phase2/ -m "performance"

# Run with benchmark output
pytest tests/performance/phase2/test_latency.py --benchmark-only

# Run with memory profiling
pytest tests/performance/phase2/test_memory.py -v -s

# Run load test
locust -f tests/performance/phase2/locustfile.py --users 20 --spawn-rate 5

# Generate performance report
pytest tests/performance/phase2/ \
  --benchmark-json=tests/coverage/performance/benchmark.json
```

---

## 9. Performance Targets Summary

| Metric | Target | Test |
|--------|--------|------|
| Backend overhead per debater | <10ms | test_debate_orchestration_overhead |
| Memory per debate (4 debaters) | <100MB | test_debate_memory_footprint |
| Memory per stream | <10MB | test_streaming_memory_per_debater |
| Concurrent debates | 5+ | test_5_concurrent_debates |
| SSE connections | 10+ | test_concurrent_streaming_connections |
| Token accuracy | Within 1% | test_token_estimation_accuracy |
| Cost accuracy | Exact match | test_claude_sonnet_pricing |
| Full debate completion | <120s | test_5_concurrent_debates |

---

## 10. Performance Monitoring

### Continuous Monitoring

```python
# tests/performance/phase2/monitor.py

import psutil
import time

class PerformanceMonitor:
    """Monitor performance during tests"""

    def __init__(self):
        self.start_time = None
        self.start_memory = None

    def start(self):
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024

    def report(self):
        elapsed = time.time() - self.start_time
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = current_memory - self.start_memory

        return {
            "elapsed_seconds": elapsed,
            "memory_mb": memory_used,
            "cpu_percent": psutil.cpu_percent()
        }
```

---

**Status:** ✅ Ready for Implementation
**Estimated Test Count:** 40+ performance tests
**Tools Required:** pytest-benchmark, memory_profiler, locust, psutil
