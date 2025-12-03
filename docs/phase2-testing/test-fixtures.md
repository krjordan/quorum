# Phase 2 Test Fixtures & Mock Data

**Date:** 2025-12-02
**Agent:** Test Engineer
**Phase:** Phase 2 - Multi-LLM Debate Engine

---

## Overview

This document defines reusable test fixtures and mock data for Phase 2 testing. These fixtures provide consistent, predictable test data across unit, integration, and E2E tests.

---

## 1. Fixture Organization

```
tests/fixtures/phase2/
├── __init__.py
├── debate_configs.py          # Mock debate configurations
├── llm_responses.py            # Mock LLM responses
├── judge_verdicts.py           # Mock judge assessments
├── cost_data.py                # Cost calculation test cases
├── context_histories.py        # Mock debate histories
└── streaming_data.py           # Mock streaming events
```

---

## 2. Debate Configuration Fixtures

**File:** `tests/fixtures/phase2/debate_configs.py`

```python
import pytest
from typing import List, Optional
from app.models.debate import DebateConfig, ParticipantConfig, JudgeConfig

@pytest.fixture
def simple_2_debater_config() -> DebateConfig:
    """Simple 2-debater free-form debate"""
    return DebateConfig(
        topic="Is artificial intelligence beneficial for humanity?",
        participants=[
            ParticipantConfig(
                id="p1",
                model="claude-3-5-sonnet-20241022",
                persona="Optimistic AI Researcher",
                system_prompt="You are an optimistic AI researcher..."
            ),
            ParticipantConfig(
                id="p2",
                model="gpt-4",
                persona="Cautious Ethicist",
                system_prompt="You are a cautious technology ethicist..."
            )
        ],
        judge=JudgeConfig(
            model="claude-3-opus-20240229",
            rubric={
                "criteria": [
                    {"name": "Clarity", "weight": 0.3},
                    {"name": "Evidence", "weight": 0.4},
                    {"name": "Logic", "weight": 0.3}
                ]
            }
        ),
        format="free-form",
        mode="simultaneous",
        max_rounds=10
    )

@pytest.fixture
def four_debater_structured_config() -> DebateConfig:
    """4-debater structured debate with phases"""
    return DebateConfig(
        topic="What is the best programming language?",
        participants=[
            ParticipantConfig(
                id="p1",
                model="claude-3-5-sonnet-20241022",
                persona="Python Advocate"
            ),
            ParticipantConfig(
                id="p2",
                model="gpt-4",
                persona="JavaScript Advocate"
            ),
            ParticipantConfig(
                id="p3",
                model="claude-3-5-haiku-20241022",
                persona="Rust Advocate"
            ),
            ParticipantConfig(
                id="p4",
                model="gpt-3.5-turbo",
                persona="Go Advocate"
            )
        ],
        judge=JudgeConfig(model="claude-3-opus-20240229"),
        format="structured-rounds",
        mode="simultaneous",
        round_limit=3
    )

@pytest.fixture
def convergence_seeking_config() -> DebateConfig:
    """Convergence-seeking debate configuration"""
    return DebateConfig(
        topic="What is 2 + 2?",
        participants=[
            ParticipantConfig(id="p1", model="claude-3-5-sonnet-20241022", persona="Math A"),
            ParticipantConfig(id="p2", model="gpt-4", persona="Math B")
        ],
        judge=JudgeConfig(model="claude-3-opus-20240229"),
        format="convergence-seeking",
        mode="simultaneous"
    )

@pytest.fixture
def round_limited_config() -> DebateConfig:
    """Round-limited debate (exactly 5 rounds)"""
    return DebateConfig(
        topic="Climate change policy",
        participants=[
            ParticipantConfig(id="p1", model="claude-3-5-sonnet-20241022", persona="A"),
            ParticipantConfig(id="p2", model="gpt-4", persona="B")
        ],
        judge=JudgeConfig(model="claude-3-opus-20240229"),
        format="round-limited",
        round_limit=5,
        mode="simultaneous"
    )

@pytest.fixture
def sequential_mode_config() -> DebateConfig:
    """Sequential mode (participants respond one at a time)"""
    return DebateConfig(
        topic="Test topic",
        participants=[
            ParticipantConfig(id="p1", model="claude-3-5-sonnet-20241022", persona="A"),
            ParticipantConfig(id="p2", model="gpt-4", persona="B")
        ],
        judge=JudgeConfig(model="claude-3-opus-20240229"),
        format="free-form",
        mode="sequential"  # Key difference
    )

@pytest.fixture
def cost_limited_config() -> DebateConfig:
    """Debate with cost warning threshold"""
    return DebateConfig(
        topic="Test topic",
        participants=[
            ParticipantConfig(id="p1", model="claude-3-5-sonnet-20241022", persona="A"),
            ParticipantConfig(id="p2", model="gpt-4", persona="B")
        ],
        judge=JudgeConfig(model="claude-3-opus-20240229"),
        format="free-form",
        mode="simultaneous",
        cost_warning_threshold=0.50  # $0.50 warning
    )

@pytest.fixture
def mock_debate_config_factory():
    """Factory for creating custom debate configurations"""
    def _factory(
        num_debaters: int = 2,
        mode: str = "simultaneous",
        format: str = "free-form",
        **kwargs
    ) -> DebateConfig:
        participants = [
            ParticipantConfig(
                id=f"p{i}",
                model="claude-3-5-sonnet-20241022" if i % 2 == 1 else "gpt-4",
                persona=f"Debater {i}"
            )
            for i in range(1, num_debaters + 1)
        ]

        return DebateConfig(
            topic=kwargs.get("topic", "Test debate topic"),
            participants=participants,
            judge=JudgeConfig(model="claude-3-opus-20240229"),
            format=format,
            mode=mode,
            **kwargs
        )

    return _factory
```

---

## 3. LLM Response Fixtures

**File:** `tests/fixtures/phase2/llm_responses.py`

```python
import pytest
from typing import Dict, List

@pytest.fixture
def mock_anthropic_streaming_response():
    """Mock Anthropic streaming response chunks"""
    return [
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""}
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "I "}
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "believe "}
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "that "}
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "artificial intelligence "}
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "is fundamentally beneficial."}
        },
        {
            "type": "content_block_stop",
            "index": 0
        },
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {
                "output_tokens": 12
            }
        },
        {
            "type": "message_stop"
        }
    ]

@pytest.fixture
def mock_openai_streaming_response():
    """Mock OpenAI streaming response chunks"""
    return [
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {"content": "I "}, "finish_reason": None}]
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {"content": "think "}, "finish_reason": None}]
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {"content": "AI "}, "finish_reason": None}]
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {"content": "is beneficial."}, "finish_reason": None}]
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 8,
                "total_tokens": 108
            }
        }
    ]

@pytest.fixture
def mock_complete_responses():
    """Mock complete responses for different models"""
    return {
        "claude-3-5-sonnet-20241022": {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "I believe that artificial intelligence represents a transformative opportunity for humanity. When developed responsibly with proper safeguards, AI can address pressing challenges in healthcare, climate change, and education."
                }
            ],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 150,
                "output_tokens": 45
            }
        },
        "gpt-4": {
            "id": "chatcmpl-456",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "While I acknowledge AI's potential benefits, we must proceed with extreme caution. The risks of misalignment, job displacement, and algorithmic bias are substantial and not yet fully understood."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 38,
                "total_tokens": 158
            }
        }
    }

@pytest.fixture
def mock_litellm_response_factory():
    """Factory for creating mock LiteLLM responses"""
    def _factory(
        model: str = "claude-3-5-sonnet-20241022",
        content: str = "Test response",
        prompt_tokens: int = 100,
        completion_tokens: int = 50
    ):
        return {
            "id": f"mock-{model}-123",
            "model": model,
            "content": content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        }

    return _factory
```

---

## 4. Judge Verdict Fixtures

**File:** `tests/fixtures/phase2/judge_verdicts.py`

```python
import pytest
from typing import Dict, List

@pytest.fixture
def mock_judge_assessment_continue():
    """Judge assessment that recommends continuing"""
    return {
        "quality_scores": [
            {
                "participant_id": "p1",
                "score": 8.5,
                "criteria_scores": {
                    "Clarity": 9.0,
                    "Evidence": 8.5,
                    "Logic": 8.0
                },
                "strengths": ["Clear arguments", "Good evidence"],
                "weaknesses": ["Could use more examples"]
            },
            {
                "participant_id": "p2",
                "score": 7.5,
                "criteria_scores": {
                    "Clarity": 8.0,
                    "Evidence": 7.0,
                    "Logic": 7.5
                },
                "strengths": ["Logical reasoning"],
                "weaknesses": ["Weaker evidence"]
            }
        ],
        "round_summary": "Both participants presented strong arguments. Participant 1 had slightly better evidence, while Participant 2 focused on logical reasoning. The debate is productive and should continue.",
        "should_continue": True,
        "flags": {
            "convergence_reached": False,
            "diminishing_returns": False,
            "repetition_detected": False
        }
    }

@pytest.fixture
def mock_judge_assessment_stop_repetition():
    """Judge assessment that stops due to repetition"""
    return {
        "quality_scores": [
            {"participant_id": "p1", "score": 6.0},
            {"participant_id": "p2", "score": 6.0}
        ],
        "round_summary": "Both participants are repeating previous arguments without adding new insights. The debate has reached diminishing returns.",
        "should_continue": False,
        "flags": {
            "convergence_reached": False,
            "diminishing_returns": True,
            "repetition_detected": True
        }
    }

@pytest.fixture
def mock_judge_assessment_stop_convergence():
    """Judge assessment that stops due to convergence"""
    return {
        "quality_scores": [
            {"participant_id": "p1", "score": 8.0},
            {"participant_id": "p2", "score": 8.0}
        ],
        "round_summary": "Both participants have reached substantial agreement on the core issues. Further debate is unlikely to yield new insights.",
        "should_continue": False,
        "flags": {
            "convergence_reached": True,
            "diminishing_returns": False,
            "repetition_detected": False
        }
    }

@pytest.fixture
def mock_final_verdict():
    """Mock final verdict from judge"""
    return {
        "summary": "This debate explored the benefits and risks of artificial intelligence for humanity. Both sides presented compelling arguments backed by evidence and logical reasoning.",
        "key_points": [
            "AI has transformative potential in healthcare, education, and climate",
            "Significant risks exist around misalignment and job displacement",
            "Responsible development with safeguards is crucial",
            "More research is needed to fully understand long-term implications"
        ],
        "areas_of_agreement": [
            "AI is a powerful technology with significant impact",
            "Responsible development is important",
            "Both benefits and risks are real and substantial"
        ],
        "areas_of_disagreement": [
            "Relative weight of benefits vs. risks",
            "Appropriate pace of AI development",
            "Level of caution required"
        ],
        "winner": {
            "participant_id": "p1",
            "reasoning": "Participant 1 provided slightly more comprehensive evidence for their position and addressed counterarguments more thoroughly.",
            "margin": "narrow"
        },
        "verdict": "Both participants demonstrated strong reasoning and evidence. Participant 1 edges ahead with more comprehensive evidence and counterargument handling. This was a high-quality debate that illuminated multiple perspectives on AI's role in society.",
        "cost_usd": 0.045
    }

@pytest.fixture
def mock_judge_factory():
    """Factory for creating custom judge assessments"""
    def _factory(
        should_continue: bool = True,
        convergence: bool = False,
        repetition: bool = False,
        scores: List[float] = None
    ):
        if scores is None:
            scores = [7.5, 7.5]

        return {
            "quality_scores": [
                {"participant_id": f"p{i+1}", "score": score}
                for i, score in enumerate(scores)
            ],
            "round_summary": "Judge summary here.",
            "should_continue": should_continue,
            "flags": {
                "convergence_reached": convergence,
                "diminishing_returns": not should_continue and not convergence,
                "repetition_detected": repetition
            }
        }

    return _factory
```

---

## 5. Cost Calculation Test Cases

**File:** `tests/fixtures/phase2/cost_data.py`

```python
import pytest
from typing import Tuple

@pytest.fixture
def cost_test_cases():
    """Test cases for cost calculation validation"""
    return [
        # (model, prompt_tokens, completion_tokens, expected_cost)
        ("claude-3-5-sonnet-20241022", 1_000_000, 1_000_000, 18.00),  # $3 + $15
        ("claude-3-5-haiku-20241022", 1_000_000, 1_000_000, 4.80),    # $0.80 + $4
        ("claude-3-opus-20240229", 1_000_000, 1_000_000, 90.00),      # $15 + $75
        ("gpt-4", 1_000_000, 1_000_000, 90.00),                       # $30 + $60 (approx)
        ("gpt-3.5-turbo", 1_000_000, 1_000_000, 3.50),                # $1.50 + $2

        # Smaller scales
        ("claude-3-5-sonnet-20241022", 1000, 500, 0.0105),   # $0.003 + $0.0075
        ("claude-3-5-haiku-20241022", 1000, 500, 0.0028),    # $0.0008 + $0.002

        # Edge cases
        ("claude-3-5-sonnet-20241022", 0, 1000, 0.015),      # Only output tokens
        ("claude-3-5-sonnet-20241022", 1000, 0, 0.003),      # Only input tokens
    ]

@pytest.fixture
def debate_cost_scenarios():
    """Complete debate cost scenarios"""
    return [
        {
            "name": "Simple 2-debater, 3 rounds",
            "config": {
                "num_debaters": 2,
                "debater_model": "claude-3-5-sonnet-20241022",
                "judge_model": "claude-3-opus-20240229",
                "num_rounds": 3
            },
            "tokens_per_response": (1000, 500),
            "expected_total_cost": lambda: (
                # 3 rounds * 2 debaters * sonnet_cost
                3 * 2 * ((1000/1_000_000 * 3) + (500/1_000_000 * 15)) +
                # 3 assessments * opus_cost
                3 * ((1000/1_000_000 * 15) + (500/1_000_000 * 75)) +
                # 1 final verdict * opus_cost
                1 * ((2000/1_000_000 * 15) + (1000/1_000_000 * 75))
            )
        },
        {
            "name": "4-debater structured, 3 rounds",
            "config": {
                "num_debaters": 4,
                "debater_model": "claude-3-5-sonnet-20241022",
                "judge_model": "claude-3-opus-20240229",
                "num_rounds": 3
            },
            "tokens_per_response": (1200, 600),
            "expected_total_cost": lambda: (
                3 * 4 * ((1200/1_000_000 * 3) + (600/1_000_000 * 15)) +
                3 * ((1500/1_000_000 * 15) + (700/1_000_000 * 75)) +
                1 * ((3000/1_000_000 * 15) + (1500/1_000_000 * 75))
            )
        }
    ]

@pytest.fixture
def pricing_tables():
    """Current pricing tables for all supported models"""
    return {
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,   # per million tokens
            "output": 15.00
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,
            "output": 4.00
        },
        "claude-3-opus-20240229": {
            "input": 15.00,
            "output": 75.00
        },
        "gpt-4": {
            "input": 30.00,
            "output": 60.00
        },
        "gpt-3.5-turbo": {
            "input": 1.50,
            "output": 2.00
        }
    }
```

---

## 6. Context History Fixtures

**File:** `tests/fixtures/phase2/context_histories.py`

```python
import pytest
from typing import List
from datetime import datetime, timedelta

@pytest.fixture
def simple_debate_history():
    """Simple 3-round debate history"""
    return [
        {
            "round_number": 1,
            "responses": [
                {
                    "participant_id": "p1",
                    "content": "I believe AI is beneficial because...",
                    "token_count": 250
                },
                {
                    "participant_id": "p2",
                    "content": "However, we must be cautious about...",
                    "token_count": 230
                }
            ],
            "judge_assessment": {
                "summary": "Good opening arguments from both sides.",
                "scores": [8.0, 7.5]
            }
        },
        {
            "round_number": 2,
            "responses": [
                {
                    "participant_id": "p1",
                    "content": "Building on that, consider healthcare...",
                    "token_count": 280
                },
                {
                    "participant_id": "p2",
                    "content": "But job displacement is a serious concern...",
                    "token_count": 260
                }
            ],
            "judge_assessment": {
                "summary": "Both developing their arguments well.",
                "scores": [8.5, 8.0]
            }
        },
        {
            "round_number": 3,
            "responses": [
                {
                    "participant_id": "p1",
                    "content": "In conclusion, with proper safeguards...",
                    "token_count": 220
                },
                {
                    "participant_id": "p2",
                    "content": "We need more research before moving forward...",
                    "token_count": 240
                }
            ],
            "judge_assessment": {
                "summary": "Strong closing arguments.",
                "scores": [8.5, 8.5]
            }
        }
    ]

@pytest.fixture
def large_debate_history():
    """Large debate history (20 rounds) for context management testing"""
    def _factory(num_rounds: int = 20, avg_response_length: int = 1000):
        history = []
        for round_num in range(1, num_rounds + 1):
            history.append({
                "round_number": round_num,
                "responses": [
                    {
                        "participant_id": f"p{i}",
                        "content": f"Response in round {round_num} " * (avg_response_length // 20),
                        "token_count": avg_response_length
                    }
                    for i in range(1, 3)
                ],
                "judge_assessment": {
                    "summary": f"Assessment for round {round_num}",
                    "scores": [7.5, 7.5]
                }
            })
        return history

    return _factory

@pytest.fixture
def convergent_debate_history():
    """Debate history showing gradual convergence"""
    return [
        {
            "round_number": 1,
            "responses": [
                {"participant_id": "p1", "content": "I strongly disagree..."},
                {"participant_id": "p2", "content": "I completely oppose that view..."}
            ]
        },
        {
            "round_number": 2,
            "responses": [
                {"participant_id": "p1", "content": "Perhaps there is some merit to your point about..."},
                {"participant_id": "p2", "content": "I can acknowledge that your concern is valid..."}
            ]
        },
        {
            "round_number": 3,
            "responses": [
                {"participant_id": "p1", "content": "We seem to agree that the key issue is..."},
                {"participant_id": "p2", "content": "Yes, I think we've reached common ground on..."}
            ]
        }
    ]

@pytest.fixture
def repetitive_debate_history():
    """Debate history with repetitive arguments"""
    return [
        {
            "round_number": i,
            "responses": [
                {"participant_id": "p1", "content": "As I mentioned before, my main point is X..."},
                {"participant_id": "p2", "content": "Again, I disagree because Y, as I said earlier..."}
            ]
        }
        for i in range(1, 6)
    ]
```

---

## 7. Streaming Event Fixtures

**File:** `tests/fixtures/phase2/streaming_data.py`

```python
import pytest

@pytest.fixture
def mock_sse_events():
    """Mock Server-Sent Events for a complete round"""
    return [
        {
            "type": "round_start",
            "round_number": 1,
            "timestamp": "2025-12-02T10:00:00Z"
        },
        {
            "type": "participant_response_start",
            "participant_id": "p1",
            "timestamp": "2025-12-02T10:00:01Z"
        },
        {
            "type": "participant_response_chunk",
            "participant_id": "p1",
            "content": "I ",
            "timestamp": "2025-12-02T10:00:01.100Z"
        },
        {
            "type": "participant_response_chunk",
            "participant_id": "p1",
            "content": "believe ",
            "timestamp": "2025-12-02T10:00:01.200Z"
        },
        {
            "type": "participant_response_complete",
            "participant_id": "p1",
            "full_text": "I believe that...",
            "token_usage": {"prompt": 100, "completion": 50},
            "cost_usd": 0.0075,
            "timestamp": "2025-12-02T10:00:05Z"
        },
        {
            "type": "judge_assessment",
            "assessment": {
                "quality_scores": [...],
                "should_continue": True
            },
            "timestamp": "2025-12-02T10:00:10Z"
        },
        {
            "type": "round_complete",
            "round_number": 1,
            "timestamp": "2025-12-02T10:00:11Z"
        }
    ]

@pytest.fixture
def mock_parallel_streaming_events():
    """Mock simultaneous streaming from multiple participants"""
    return {
        "p1": [
            {"type": "chunk", "content": "I ", "timestamp": 1000},
            {"type": "chunk", "content": "think ", "timestamp": 1100},
            {"type": "complete", "full_text": "I think AI is beneficial.", "timestamp": 2000}
        ],
        "p2": [
            {"type": "chunk", "content": "However, ", "timestamp": 1050},
            {"type": "chunk", "content": "we must ", "timestamp": 1150},
            {"type": "complete", "full_text": "However, we must be cautious.", "timestamp": 2100}
        ]
    }

@pytest.fixture
def mock_error_events():
    """Mock error events during streaming"""
    return [
        {
            "type": "participant_error",
            "participant_id": "p2",
            "error_type": "rate_limit",
            "message": "Rate limit exceeded",
            "retryable": True,
            "retry_after": 60,
            "timestamp": "2025-12-02T10:00:05Z"
        },
        {
            "type": "connection_error",
            "message": "SSE connection lost",
            "timestamp": "2025-12-02T10:01:00Z"
        },
        {
            "type": "reconnecting",
            "attempt": 1,
            "max_attempts": 3,
            "timestamp": "2025-12-02T10:01:01Z"
        },
        {
            "type": "reconnected",
            "timestamp": "2025-12-02T10:01:05Z"
        }
    ]
```

---

## 8. Using Fixtures

### Example Usage

```python
# Unit test using fixtures
def test_debate_orchestration(simple_2_debater_config, mock_litellm_response_factory):
    config = simple_2_debater_config
    mock_response = mock_litellm_response_factory(
        model="claude-3-5-sonnet-20241022",
        content="Test response"
    )

    # Use in test...

# Integration test using fixtures
async def test_full_debate_flow(
    client,
    four_debater_structured_config,
    mock_judge_factory
):
    config = four_debater_structured_config

    # Create debate
    response = await client.post("/api/debates/configure", json=config.dict())

    # Mock judge responses
    judge_response = mock_judge_factory(should_continue=True, scores=[8.0, 8.5, 7.5, 8.0])

    # ...
```

---

## 9. Fixture Dependencies

```
Cost Fixtures
├── pricing_tables
└── cost_test_cases

Config Fixtures
├── simple_2_debater_config
├── four_debater_structured_config
└── mock_debate_config_factory

Response Fixtures
├── mock_anthropic_streaming_response
├── mock_openai_streaming_response
└── mock_litellm_response_factory

Judge Fixtures
├── mock_judge_assessment_continue
├── mock_judge_assessment_stop_repetition
└── mock_final_verdict

History Fixtures
├── simple_debate_history
├── large_debate_history (factory)
└── convergent_debate_history
```

---

**Status:** ✅ Ready for Implementation
**Total Fixtures:** 30+ reusable fixtures
**Coverage:** All test scenarios (unit, integration, E2E, performance)
