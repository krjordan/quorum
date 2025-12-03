# Phase 2 Integration Test Plan - Multi-LLM Debate Engine

**Date:** 2025-12-02
**Agent:** Test Engineer
**Phase:** Phase 2 - Multi-LLM Debate Engine

---

## Overview

Integration tests validate the complete debate flow from configuration through execution to completion, ensuring all components work together correctly. These tests use real API clients (with mocks) but avoid actual LLM API calls to maintain speed and determinism.

**Coverage Focus:** Critical user workflows and component interactions

---

## 1. Test Structure

```
tests/integration/phase2/
├── conftest.py                           # Integration fixtures
├── test_debate_flow.py                   # Complete debate workflows
├── test_parallel_streaming_flow.py       # Multi-debater streaming
├── test_cost_tracking_flow.py            # End-to-end cost tracking
├── test_context_management_flow.py       # Context window handling
├── test_judge_integration.py             # Judge coordination
└── test_export_flow.py                   # Debate export functionality
```

---

## 2. Complete Debate Flow Tests

**File:** `tests/integration/phase2/test_debate_flow.py`

### 2.1 Basic Debate Flows

```python
@pytest.mark.integration
@pytest.mark.debate
class TestDebateFlow:
    """Test complete debate workflows"""

    async def test_simple_two_debater_free_form(
        self, client, mock_litellm_provider
    ):
        """Test simple 2-debater free-form debate"""
        # Step 1: Configure debate
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Is AI beneficial for humanity?",
            "participants": [
                {
                    "model": "claude-3-5-sonnet-20241022",
                    "persona": "Optimist"
                },
                {
                    "model": "gpt-4",
                    "persona": "Skeptic"
                }
            ],
            "judge": {
                "model": "claude-3-opus-20240229"
            },
            "format": "free-form",
            "mode": "simultaneous"
        })

        assert config_response.status_code == 200
        debate_id = config_response.json()["debate_id"]

        # Step 2: Start debate
        start_response = await client.post(
            f"/api/debates/{debate_id}/start"
        )
        assert start_response.status_code == 200

        # Step 3: Monitor progress via SSE
        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream"
        ) as stream:
            events = []
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event)

                    # Check for completion
                    if event.get("type") == "debate_complete":
                        break

        # Verify we got expected events
        event_types = [e["type"] for e in events]
        assert "round_start" in event_types
        assert "participant_response_chunk" in event_types
        assert "round_complete" in event_types
        assert "judge_assessment" in event_types
        assert "debate_complete" in event_types

        # Step 4: Get final results
        results_response = await client.get(
            f"/api/debates/{debate_id}"
        )
        assert results_response.status_code == 200

        debate = results_response.json()
        assert debate["status"] == "completed"
        assert len(debate["rounds"]) >= 1
        assert debate["judge"]["final_verdict"] is not None

    async def test_four_debater_structured_rounds(
        self, client, mock_litellm_provider
    ):
        """Test 4-debater structured debate"""
        # Configure with 4 participants
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Best programming language",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "Python"},
                {"model": "gpt-4", "persona": "JavaScript"},
                {"model": "claude-3-5-haiku-20241022", "persona": "Rust"},
                {"model": "gpt-3.5-turbo", "persona": "Go"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "structured-rounds",
            "round_limit": 3,
            "mode": "simultaneous"
        })

        debate_id = config_response.json()["debate_id"]

        # Start and complete debate
        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for completion
        for attempt in range(60):  # 60 second timeout
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        # Verify completion
        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        assert debate["status"] == "completed"
        assert len(debate["rounds"]) == 3
        assert len(debate["rounds"][0]["responses"]) == 4

        # Verify phases (opening, middle, closing)
        assert debate["rounds"][0]["phase"] == "opening"
        assert debate["rounds"][1]["phase"] == "middle"
        assert debate["rounds"][2]["phase"] == "closing"

    async def test_convergence_seeking_debate(
        self, client, mock_litellm_provider
    ):
        """Test convergence-seeking format stops when consensus reached"""
        # Configure convergence-seeking debate
        config_response = await client.post("/api/debates/configure", json={
            "topic": "What is 2+2?",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "Math A"},
                {"model": "gpt-4", "persona": "Math B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "convergence-seeking",
            "mode": "simultaneous"
        })

        debate_id = config_response.json()["debate_id"]

        # Mock convergence detection
        mock_litellm_provider.set_judge_response({
            "quality_scores": [...],
            "should_continue": False,
            "flags": {
                "convergence_reached": True,
                "diminishing_returns": False,
                "repetition_detected": False
            }
        })

        # Start debate
        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for completion
        for attempt in range(30):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        # Verify early termination due to convergence
        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        assert debate["status"] == "completed"
        assert len(debate["rounds"]) < 5  # Should stop early
        assert debate["termination_reason"] == "convergence_reached"
```

### 2.2 Error Handling & Recovery

```python
@pytest.mark.integration
class TestDebateErrorHandling:
    """Test error handling during debates"""

    async def test_participant_failure_continues_debate(
        self, client, mock_litellm_provider
    ):
        """Test debate continues when one participant fails"""
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"},
                {"model": "claude-3-5-haiku-20241022", "persona": "C"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "free-form"
        })

        debate_id = config_response.json()["debate_id"]

        # Configure one participant to fail
        mock_litellm_provider.set_participant_error(
            participant_id="B",
            error=RateLimitError("Rate limited", retry_after=60)
        )

        # Start debate
        await client.post(f"/api/debates/{debate_id}/start")

        # Monitor for error event
        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream"
        ) as stream:
            events = []
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event)

                    if event.get("type") == "participant_error":
                        assert event["participant_id"] == "B"
                        assert event["error_type"] == "rate_limit"
                        assert event["retryable"] == True

                    if event.get("type") == "round_complete":
                        break

        # Debate should continue with remaining participants
        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        round_responses = debate["rounds"][0]["responses"]
        successful = [r for r in round_responses if r["status"] == "completed"]
        failed = [r for r in round_responses if r["status"] == "error"]

        assert len(successful) == 2  # A and C succeeded
        assert len(failed) == 1  # B failed

    async def test_judge_failure_retries(
        self, client, mock_litellm_provider
    ):
        """Test judge failure triggers retry"""
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "free-form"
        })

        debate_id = config_response.json()["debate_id"]

        # Configure judge to fail once then succeed
        mock_litellm_provider.set_judge_failures(count=1)

        # Start debate
        await client.post(f"/api/debates/{debate_id}/start")

        # Monitor events
        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream"
        ) as stream:
            events = []
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

                    if len([e for e in events if e.get("type") == "judge_retry"]) > 0:
                        # Retry event detected
                        break

        # Verify judge retry occurred
        retry_events = [e for e in events if e.get("type") == "judge_retry"]
        assert len(retry_events) > 0

        # Debate should eventually complete
        for attempt in range(30):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        debate = (await client.get(f"/api/debates/{debate_id}")).json()
        assert debate["status"] == "completed"
```

---

## 3. Parallel Streaming Integration Tests

**File:** `tests/integration/phase2/test_parallel_streaming_flow.py`

```python
@pytest.mark.integration
@pytest.mark.parallel
class TestParallelStreamingFlow:
    """Test parallel streaming coordination"""

    async def test_simultaneous_streaming_four_debaters(
        self, client, mock_litellm_provider
    ):
        """Test 4 debaters streaming simultaneously"""
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": f"model-{i}", "persona": f"Debater {i}"}
                for i in range(1, 5)
            ],
            "judge": {"model": "judge-model"},
            "mode": "simultaneous"
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Track when each participant starts streaming
        participant_start_times = {}
        participant_chunks = {f"p{i}": [] for i in range(1, 5)}

        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream"
        ) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])

                    if event.get("type") == "participant_response_chunk":
                        participant_id = event["participant_id"]

                        if participant_id not in participant_start_times:
                            participant_start_times[participant_id] = time.time()

                        participant_chunks[participant_id].append(
                            event["content"]
                        )

                    if event.get("type") == "round_complete":
                        break

        # Verify all participants started within 2 seconds of each other
        start_times = list(participant_start_times.values())
        time_spread = max(start_times) - min(start_times)
        assert time_spread < 2.0  # Simultaneous within 2s

        # Verify all participants completed
        assert all(len(chunks) > 0 for chunks in participant_chunks.values())

    async def test_stream_reconnection_on_disconnect(
        self, client, mock_litellm_provider
    ):
        """Test stream reconnection when connection drops"""
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"}
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Simulate disconnect after receiving some events
        events_received = 0
        reconnected = False

        try:
            async with client.stream(
                "GET",
                f"/api/debates/{debate_id}/stream"
            ) as stream:
                async for line in stream.aiter_lines():
                    events_received += 1

                    # Simulate disconnect after 5 events
                    if events_received == 5:
                        raise ConnectionError("Simulated disconnect")
        except ConnectionError:
            reconnected = True

        assert reconnected

        # Reconnect and continue
        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream?last_event_id={events_received}"
        ) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event.get("type") == "round_complete":
                        break

        # Verify debate completed successfully
        debate = (await client.get(f"/api/debates/{debate_id}")).json()
        assert debate["status"] == "completed"
```

---

## 4. Cost Tracking Integration Tests

**File:** `tests/integration/phase2/test_cost_tracking_flow.py`

```python
@pytest.mark.integration
class TestCostTrackingFlow:
    """Test end-to-end cost tracking accuracy"""

    async def test_accurate_cost_calculation_full_debate(
        self, client, mock_litellm_provider
    ):
        """Test cost calculation matches provider counts"""
        # Configure debate with known token counts
        mock_litellm_provider.set_fixed_token_counts({
            "prompt_tokens": 1000,
            "completion_tokens": 500
        })

        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "claude-3-5-haiku-20241022", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "round-limited",
            "round_limit": 2
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for completion
        for attempt in range(30):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        # Get final costs
        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        # Calculate expected costs
        # Sonnet: $3/$15 per million (input/output)
        sonnet_cost_per_response = (
            (1000 / 1_000_000 * 3) +  # Input
            (500 / 1_000_000 * 15)     # Output
        )

        # Haiku: $0.80/$4 per million
        haiku_cost_per_response = (
            (1000 / 1_000_000 * 0.80) +
            (500 / 1_000_000 * 4)
        )

        # Opus judge: $15/$75 per million
        opus_cost_per_assessment = (
            (1000 / 1_000_000 * 15) +
            (500 / 1_000_000 * 75)
        )

        # 2 rounds * 2 participants + 2 assessments + 1 final verdict
        expected_total = (
            2 * (sonnet_cost_per_response + haiku_cost_per_response) +
            3 * opus_cost_per_assessment
        )

        # Verify within 1% margin
        assert abs(debate["total_cost"] - expected_total) < expected_total * 0.01

    async def test_cost_warning_triggers_correctly(
        self, client, mock_litellm_provider
    ):
        """Test cost warning is emitted when threshold exceeded"""
        # Set very low warning threshold
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "cost_warning_threshold": 0.10  # $0.10
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Monitor for cost warning event
        warning_received = False

        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream"
        ) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])

                    if event.get("type") == "cost_warning":
                        warning_received = True
                        assert event["current_cost"] >= 0.10
                        assert event["threshold"] == 0.10
                        break

        assert warning_received
```

---

## 5. Context Management Integration Tests

**File:** `tests/integration/phase2/test_context_management_flow.py`

```python
@pytest.mark.integration
class TestContextManagementFlow:
    """Test context window management across rounds"""

    async def test_sliding_window_maintains_recent_context(
        self, client, mock_litellm_provider
    ):
        """Test sliding window keeps only recent rounds"""
        # Create debate with long history
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "round-limited",
            "round_limit": 10,
            "context_window_size": 3  # Only keep last 3 rounds
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for completion
        for attempt in range(60):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        # Verify context was managed correctly
        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        # Check that prompts for later rounds only included last 3 rounds
        final_round_context = debate["rounds"][-1]["context_used"]
        assert len(final_round_context) == 3
        assert final_round_context[0]["round_number"] == 8
        assert final_round_context[-1]["round_number"] == 10

    async def test_context_overflow_stops_debate(
        self, client, mock_litellm_provider
    ):
        """Test debate stops when context window exceeded"""
        # Configure with very small context limit
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Very long debate topic " * 100,  # Artificially long
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "max_context_tokens": 1000  # Very low limit
        })

        debate_id = config_response.json()["debate_id"]

        # Mock responses to be very long
        mock_litellm_provider.set_response_length(5000)

        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for termination
        for attempt in range(30):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] in ["completed", "error"]:
                break
            await asyncio.sleep(1)

        # Verify termination due to context overflow
        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        assert debate["status"] in ["completed", "error"]
        assert debate["termination_reason"] == "context_overflow"
```

---

## 6. Judge Integration Tests

**File:** `tests/integration/phase2/test_judge_integration.py`

```python
@pytest.mark.integration
@pytest.mark.judge
class TestJudgeIntegration:
    """Test judge integration with debate flow"""

    async def test_judge_evaluates_after_each_round(
        self, client, mock_litellm_provider
    ):
        """Test judge provides assessment after every round"""
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "round-limited",
            "round_limit": 3
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Track judge assessments
        assessments_received = 0

        async with client.stream(
            "GET",
            f"/api/debates/{debate_id}/stream"
        ) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])

                    if event.get("type") == "judge_assessment":
                        assessments_received += 1

                    if event.get("type") == "debate_complete":
                        break

        # Should have 3 round assessments + 1 final verdict
        assert assessments_received == 3

        debate = (await client.get(f"/api/debates/{debate_id}")).json()
        assert len(debate["judge"]["assessments"]) == 3
        assert debate["judge"]["final_verdict"] is not None

    async def test_judge_stops_repetitive_debate(
        self, client, mock_litellm_provider
    ):
        """Test judge stops debate when repetition detected"""
        # Configure judge to detect repetition
        mock_litellm_provider.set_judge_behavior("detect_repetition_after_round_3")

        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "free-form"  # No round limit
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for completion
        for attempt in range(60):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        debate = (await client.get(f"/api/debates/{debate_id}")).json()

        # Should stop early due to repetition
        assert len(debate["rounds"]) <= 4  # Stopped at round 3 or 4
        assert debate["termination_reason"] == "repetition_detected"
```

---

## 7. Export Integration Tests

**File:** `tests/integration/phase2/test_export_flow.py`

```python
@pytest.mark.integration
class TestExportFlow:
    """Test debate export functionality"""

    async def test_export_debate_as_markdown(
        self, client, mock_litellm_provider
    ):
        """Test exporting completed debate as Markdown"""
        # Create and complete debate
        config_response = await client.post("/api/debates/configure", json={
            "topic": "Test topic",
            "participants": [
                {"model": "claude-3-5-sonnet-20241022", "persona": "A"},
                {"model": "gpt-4", "persona": "B"}
            ],
            "judge": {"model": "claude-3-opus-20240229"},
            "format": "round-limited",
            "round_limit": 2
        })

        debate_id = config_response.json()["debate_id"]
        await client.post(f"/api/debates/{debate_id}/start")

        # Wait for completion
        for attempt in range(30):
            status = await client.get(f"/api/debates/{debate_id}/status")
            if status.json()["status"] == "completed":
                break
            await asyncio.sleep(1)

        # Export as Markdown
        export_response = await client.get(
            f"/api/debates/{debate_id}/export?format=markdown"
        )

        assert export_response.status_code == 200
        markdown_content = export_response.text

        # Verify Markdown structure
        assert "# Debate:" in markdown_content
        assert "## Round 1" in markdown_content
        assert "## Round 2" in markdown_content
        assert "## Judge's Final Verdict" in markdown_content

    async def test_export_debate_as_json(
        self, client, mock_litellm_provider
    ):
        """Test exporting debate as JSON"""
        # Create and complete debate (same as above)
        # ...

        export_response = await client.get(
            f"/api/debates/{debate_id}/export?format=json"
        )

        assert export_response.status_code == 200
        json_data = export_response.json()

        # Verify JSON structure
        assert "debate_id" in json_data
        assert "topic" in json_data
        assert "rounds" in json_data
        assert "judge" in json_data
        assert len(json_data["rounds"]) == 2
```

---

## 8. Running Integration Tests

```bash
# Run all Phase 2 integration tests
pytest tests/integration/phase2/ -m "integration"

# Run specific test file
pytest tests/integration/phase2/test_debate_flow.py -v

# Run with verbosity and log output
pytest tests/integration/phase2/ -v -s

# Run only judge tests
pytest tests/integration/phase2/ -m "judge" -v

# Run with coverage
pytest tests/integration/phase2/ --cov=backend/app
```

---

## 9. Success Criteria

| Scenario | Expected Result |
|----------|----------------|
| 2-debater free-form | Completes with ≥1 round |
| 4-debater structured | Completes 3 rounds (opening/middle/closing) |
| Convergence-seeking | Stops when consensus reached |
| Participant failure | Debate continues with remaining participants |
| Judge failure | Retries and completes assessment |
| Parallel streaming | All 4 debaters stream within 2s of each other |
| Cost tracking | Within 1% of expected costs |
| Context overflow | Debate stops gracefully |
| Export | Valid Markdown/JSON output |

---

**Status:** ✅ Ready for Implementation
**Estimated Test Count:** 50+ integration tests
**Estimated Runtime:** 5-10 minutes (with mocked LLM calls)
