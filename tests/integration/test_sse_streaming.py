"""
Integration Tests for SSE Streaming

Tests the complete flow:
1. Frontend sends request
2. Backend connects to LLM provider
3. SSE stream is established
4. Chunks are received and processed
5. Conversation is persisted
"""

import pytest
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, AsyncMock
import time


@pytest.mark.integration
@pytest.mark.sse
class TestSSEStreamingFlow:
    """Test complete SSE streaming integration."""

    def test_end_to_end_streaming_anthropic(
        self,
        client: TestClient,
        mock_anthropic_response,
        sse_event_parser
    ):
        """Test complete streaming flow with Anthropic."""
        request_data = {
            "message": "Explain quantum entanglement",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        expected_response = (
            "Quantum entanglement is a phenomenon where particles "
            "become correlated in ways that classical physics cannot explain."
        )

        with patch('src.services.llm.anthropic_client.stream') as mock_stream:
            mock_stream.return_value = mock_anthropic_response(expected_response)

            # Start streaming request
            with client.stream("POST", "/api/chat/stream", json=request_data) as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"

                # Collect all events
                events = []
                full_response = ""

                for line in response.iter_lines():
                    if line.startswith('data: '):
                        data = line[6:]
                        if data.strip() and data != '[DONE]':
                            event = json.loads(data)
                            events.append(event)

                            # Extract text content
                            if 'delta' in event and 'text' in event['delta']:
                                full_response += event['delta']['text']

                # Verify we received chunks
                assert len(events) > 0

                # Verify complete response was streamed
                assert "quantum" in full_response.lower()
                assert "entanglement" in full_response.lower()


    def test_streaming_with_conversation_persistence(
        self,
        client: TestClient,
        mock_anthropic_response,
        db_session
    ):
        """Test that streaming conversations are persisted."""
        request_data = {
            "message": "What is AI?",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True,
            "conversation_id": None
        }

        with patch('src.services.llm.anthropic_client.stream') as mock_stream:
            with patch('src.services.conversation.save_conversation') as mock_save:
                mock_stream.return_value = mock_anthropic_response(
                    "AI is artificial intelligence."
                )

                response = client.post("/api/chat/stream", json=request_data)

                assert response.status_code == 200

                # Verify conversation was saved
                assert mock_save.called
                saved_conversation = mock_save.call_args[0][0]

                assert len(saved_conversation['messages']) == 2
                assert saved_conversation['messages'][0]['role'] == 'user'
                assert saved_conversation['messages'][1]['role'] == 'assistant'


    def test_streaming_error_recovery(
        self,
        client: TestClient
    ):
        """Test error handling during streaming."""
        request_data = {
            "message": "Test message",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        with patch('src.services.llm.anthropic_client.stream') as mock_stream:
            # Simulate stream error
            def error_stream(*args, **kwargs):
                yield {"delta": {"text": "Starting..."}}
                raise Exception("Stream interrupted")

            mock_stream.return_value = error_stream()

            with client.stream("POST", "/api/chat/stream", json=request_data) as response:
                events = []
                error_occurred = False

                try:
                    for line in response.iter_lines():
                        if line.startswith('data: '):
                            data = line[6:]
                            if data.strip():
                                events.append(json.loads(data))
                except Exception:
                    error_occurred = True

                # Verify partial response was received
                assert len(events) > 0


    def test_concurrent_streaming_sessions(
        self,
        client: TestClient,
        mock_anthropic_response
    ):
        """Test multiple concurrent streaming sessions."""
        request_data_1 = {
            "message": "Question 1",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        request_data_2 = {
            "message": "Question 2",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        with patch('src.services.llm.anthropic_client.stream') as mock_stream:
            mock_stream.return_value = mock_anthropic_response("Response")

            # Start two concurrent streams
            with client.stream("POST", "/api/chat/stream", json=request_data_1) as r1:
                with client.stream("POST", "/api/chat/stream", json=request_data_2) as r2:
                    assert r1.status_code == 200
                    assert r2.status_code == 200

                    # Both streams should be independent
                    events_1 = []
                    events_2 = []

                    for line in r1.iter_lines():
                        if line.startswith('data: '):
                            events_1.append(line)

                    for line in r2.iter_lines():
                        if line.startswith('data: '):
                            events_2.append(line)

                    assert len(events_1) > 0
                    assert len(events_2) > 0


@pytest.mark.integration
class TestProviderSwitching:
    """Test switching between LLM providers."""

    def test_switch_from_anthropic_to_openrouter(
        self,
        client: TestClient,
        mock_anthropic_response,
        mock_openrouter_response
    ):
        """Test switching providers mid-conversation."""
        # First request with Anthropic
        request_1 = {
            "message": "Hello",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        with patch('src.services.llm.anthropic_client.stream') as mock_anthro:
            mock_anthro.return_value = mock_anthropic_response("Hi there!")

            response_1 = client.post("/api/chat/stream", json=request_1)
            assert response_1.status_code == 200

            # Get conversation ID from response
            conversation_id = "conv-123"  # Would be extracted from response

        # Second request with OpenRouter
        request_2 = {
            "message": "How are you?",
            "provider": "openrouter",
            "model": "anthropic/claude-3.5-sonnet",
            "stream": True,
            "conversation_id": conversation_id
        }

        with patch('src.services.llm.openrouter_client.stream') as mock_or:
            mock_or.return_value = mock_openrouter_response("I'm doing well!")

            response_2 = client.post("/api/chat/stream", json=request_2)
            assert response_2.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
class TestStreamingPerformance:
    """Test streaming performance characteristics."""

    def test_streaming_latency(
        self,
        client: TestClient,
        mock_anthropic_response
    ):
        """Test time to first byte in streaming."""
        request_data = {
            "message": "Quick test",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        with patch('src.services.llm.anthropic_client.stream') as mock_stream:
            mock_stream.return_value = mock_anthropic_response("Response")

            start_time = time.time()

            with client.stream("POST", "/api/chat/stream", json=request_data) as response:
                # Get first chunk
                for line in response.iter_lines():
                    if line.startswith('data: '):
                        first_byte_time = time.time() - start_time
                        break

            # Verify low latency (< 100ms for mocked response)
            assert first_byte_time < 0.1


    def test_streaming_throughput(
        self,
        client: TestClient,
        mock_anthropic_response
    ):
        """Test streaming throughput with large response."""
        large_response = "This is a test. " * 1000  # ~16KB response

        request_data = {
            "message": "Give me a long response",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "stream": True
        }

        with patch('src.services.llm.anthropic_client.stream') as mock_stream:
            mock_stream.return_value = mock_anthropic_response(
                large_response,
                chunks=50
            )

            start_time = time.time()
            chunk_count = 0

            with client.stream("POST", "/api/chat/stream", json=request_data) as response:
                for line in response.iter_lines():
                    if line.startswith('data: '):
                        chunk_count += 1

            duration = time.time() - start_time

            # Verify we received multiple chunks
            assert chunk_count > 10

            # Calculate throughput (should be fast with mocked data)
            throughput = len(large_response) / duration
            assert throughput > 1000  # >1KB/s
