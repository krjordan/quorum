"""
Mock LLM Response Fixtures

Provides realistic mock responses for different LLM providers
to ensure consistent testing without API calls.
"""

from typing import List, Dict, Any, Iterator
import json


class AnthropicMockResponses:
    """Mock responses for Anthropic Claude API."""

    @staticmethod
    def simple_response(content: str) -> List[Dict[str, Any]]:
        """Generate simple streaming response."""
        return [
            {
                "type": "message_start",
                "message": {
                    "id": "msg_test123",
                    "model": "claude-3-5-sonnet-20241022",
                    "role": "assistant"
                }
            },
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""}
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": content}
            },
            {
                "type": "content_block_stop",
                "index": 0
            },
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 50}
            },
            {
                "type": "message_stop"
            }
        ]

    @staticmethod
    def chunked_response(content: str, num_chunks: int = 5) -> List[Dict[str, Any]]:
        """Generate chunked streaming response."""
        chunk_size = len(content) // num_chunks
        chunks = []

        # Add message start
        chunks.append({
            "type": "message_start",
            "message": {
                "id": "msg_test123",
                "model": "claude-3-5-sonnet-20241022",
                "role": "assistant"
            }
        })

        chunks.append({
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""}
        })

        # Add content chunks
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(content)
            chunk_text = content[start:end]

            chunks.append({
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": chunk_text}
            })

        # Add stop events
        chunks.extend([
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": len(content.split())}
            },
            {"type": "message_stop"}
        ])

        return chunks


class OpenRouterMockResponses:
    """Mock responses for OpenRouter API."""

    @staticmethod
    def simple_response(content: str) -> List[Dict[str, Any]]:
        """Generate simple streaming response."""
        return [
            {
                "id": "chatcmpl-test123",
                "model": "anthropic/claude-3.5-sonnet",
                "choices": [{
                    "delta": {"role": "assistant", "content": content},
                    "index": 0,
                    "finish_reason": None
                }]
            },
            {
                "id": "chatcmpl-test123",
                "model": "anthropic/claude-3.5-sonnet",
                "choices": [{
                    "delta": {},
                    "index": 0,
                    "finish_reason": "stop"
                }]
            }
        ]

    @staticmethod
    def chunked_response(content: str, num_chunks: int = 5) -> List[Dict[str, Any]]:
        """Generate chunked streaming response."""
        chunk_size = len(content) // num_chunks
        chunks = []

        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(content)
            chunk_text = content[start:end]

            chunks.append({
                "id": "chatcmpl-test123",
                "model": "anthropic/claude-3.5-sonnet",
                "choices": [{
                    "delta": {"content": chunk_text},
                    "index": 0,
                    "finish_reason": None
                }]
            })

        # Add final chunk
        chunks.append({
            "id": "chatcmpl-test123",
            "model": "anthropic/claude-3.5-sonnet",
            "choices": [{
                "delta": {},
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": len(content.split()),
                "total_tokens": 10 + len(content.split())
            }
        })

        return chunks


# Sample conversation data
SAMPLE_CONVERSATIONS = {
    "technical": {
        "id": "conv_tech_001",
        "messages": [
            {
                "role": "user",
                "content": "Explain how neural networks work"
            },
            {
                "role": "assistant",
                "content": (
                    "Neural networks are computational models inspired by biological "
                    "neural networks. They consist of layers of interconnected nodes "
                    "(neurons) that process information through weighted connections."
                )
            }
        ]
    },
    "simple": {
        "id": "conv_simple_001",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you today?"}
        ]
    },
    "multi_turn": {
        "id": "conv_multi_001",
        "messages": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language."},
            {"role": "user", "content": "What makes it popular?"},
            {
                "role": "assistant",
                "content": "Python is popular due to its simple syntax and versatility."
            }
        ]
    }
}


# Error responses
class ErrorResponses:
    """Mock error responses."""

    RATE_LIMIT = {
        "error": {
            "type": "rate_limit_error",
            "message": "Rate limit exceeded"
        }
    }

    INVALID_REQUEST = {
        "error": {
            "type": "invalid_request_error",
            "message": "Invalid request parameters"
        }
    }

    AUTHENTICATION = {
        "error": {
            "type": "authentication_error",
            "message": "Invalid API key"
        }
    }

    SERVER_ERROR = {
        "error": {
            "type": "api_error",
            "message": "Internal server error"
        }
    }
