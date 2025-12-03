"""
SSE Streaming Service - Server-Sent Events implementation
Handles real-time streaming of LLM responses
"""
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class SSEStreamingService:
    """Service for Server-Sent Events streaming"""

    @staticmethod
    def format_sse(data: dict, event: str = "message") -> str:
        """
        Format data as SSE event

        Args:
            data: Dictionary to send
            event: Event type name

        Returns:
            Formatted SSE string
        """
        json_data = json.dumps(data)
        return f"event: {event}\ndata: {json_data}\n\n"

    @staticmethod
    async def create_stream(
        generator: AsyncGenerator
    ) -> StreamingResponse:
        """
        Create SSE StreamingResponse from async generator

        Args:
            generator: Async generator yielding chat chunks

        Returns:
            StreamingResponse configured for SSE
        """
        async def event_generator():
            try:
                logger.info("🌊 Starting SSE stream")
                chunk_count = 0

                async for chunk in generator:
                    # Send message event
                    yield SSEStreamingService.format_sse(chunk, "message")
                    chunk_count += 1

                    # Small delay to prevent overwhelming client
                    await asyncio.sleep(0.01)

                # Send completion event
                logger.info(f"✅ SSE stream complete - {chunk_count} chunks sent")
                yield SSEStreamingService.format_sse(
                    {"finish_reason": "stop"},
                    "done"
                )

            except Exception as e:
                logger.error(f"❌ Streaming error: {e}", exc_info=True)
                # Send error event
                yield SSEStreamingService.format_sse(
                    {"error": str(e), "error_type": type(e).__name__},
                    "error"
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for nginx
            }
        )


# Singleton instance
sse_service = SSEStreamingService()
