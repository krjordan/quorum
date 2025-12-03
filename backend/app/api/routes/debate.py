"""
Debate API Routes - Endpoints for multi-LLM debate orchestration
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from typing import AsyncGenerator

from app.models.debate import (
    DebateConfig, Debate, DebateStreamEvent, DebateExportRequest, DebateExportFormat
)
from app.models.responses import SuccessResponse, ErrorResponse
from app.services.debate_service import debate_service
from app.services.streaming import SSEStreamingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/debates", response_model=Debate, status_code=201)
async def create_debate(config: DebateConfig):
    """
    Create a new multi-LLM debate

    Creates a debate with 2-4 LLM participants and returns the initialized debate object.
    The debate will not start until you connect to the streaming endpoint.

    Args:
        config: Debate configuration with topic, participants, format, and settings

    Returns:
        Initialized Debate object with unique ID

    Example:
        ```json
        {
          "topic": "Should AI development be open source?",
          "participants": [
            {
              "model": "gpt-4o",
              "persona": {
                "name": "Open Source Advocate",
                "role": "Argue for open source AI development",
                "temperature": 0.8
              }
            },
            {
              "model": "claude-3-5-sonnet-20241022",
              "persona": {
                "name": "Safety Researcher",
                "role": "Argue for controlled AI development",
                "temperature": 0.7
              }
            }
          ],
          "format": "structured",
          "judge_model": "gpt-4o",
          "max_rounds": 5
        }
        ```
    """
    try:
        # Validate participant count
        if len(config.participants) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 participants required"
            )
        if len(config.participants) > 4:
            raise HTTPException(
                status_code=400,
                detail="Maximum 4 participants allowed"
            )

        debate = debate_service.create_debate(config)

        logger.info(f"Created debate {debate.id}")

        return debate

    except Exception as e:
        logger.error(f"Error creating debate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debates/{debate_id}", response_model=Debate)
async def get_debate(debate_id: str):
    """
    Get debate status and history

    Retrieves the current state of a debate including all completed rounds,
    assessments, and cost information.

    Args:
        debate_id: Unique debate identifier

    Returns:
        Complete Debate object with all rounds and metadata

    Raises:
        404: Debate not found
    """
    try:
        debate = debate_service.get_debate(debate_id)
        return debate

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving debate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debates/{debate_id}/stream")
async def stream_debate(debate_id: str):
    """
    Stream debate execution in real-time

    Connects to a debate and streams all rounds, responses, and assessments
    using Server-Sent Events (SSE). The debate will execute automatically
    until completion or max rounds reached.

    Args:
        debate_id: Unique debate identifier

    Returns:
        SSE stream with debate events

    Event Types:
        - round_start: New round beginning
        - response: Participant response received
        - judge_assessment: Round assessment complete
        - round_end: Round finished with metrics
        - cost_warning: Cost threshold warning
        - debate_end: Debate completed
        - error: Error occurred

    Example Client (JavaScript):
        ```javascript
        const eventSource = new EventSource('/api/v1/debates/{debate_id}/stream');

        eventSource.addEventListener('response', (event) => {
            const data = JSON.parse(event.data);
            console.log(`${data.participant}: ${data.content}`);
        });

        eventSource.addEventListener('debate_end', (event) => {
            const data = JSON.parse(event.data);
            console.log(`Winner: ${data.winner}`);
            eventSource.close();
        });
        ```
    """
    try:
        # Verify debate exists
        debate_service.get_debate(debate_id)

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                logger.info(f"Starting debate stream for {debate_id}")

                async for event in debate_service.stream_debate_responses(debate_id):
                    # Format as SSE
                    sse_data = SSEStreamingService.format_sse(
                        data=event.model_dump(),
                        event=event.event_type
                    )
                    yield sse_data

                logger.info(f"Debate stream completed for {debate_id}")

            except Exception as e:
                logger.error(f"Error streaming debate: {e}", exc_info=True)
                error_event = DebateStreamEvent(
                    event_type="error",
                    debate_id=debate_id,
                    round_number=0,
                    data={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                yield SSEStreamingService.format_sse(
                    data=error_event.model_dump(),
                    event="error"
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error initiating stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debates/{debate_id}/export")
async def export_debate(debate_id: str, request: DebateExportRequest):
    """
    Export debate in specified format

    Exports the complete debate transcript and analysis in markdown, JSON, or HTML format.

    Args:
        debate_id: Unique debate identifier
        request: Export format configuration

    Returns:
        Formatted debate transcript

    Supported Formats:
        - markdown: GitHub-flavored markdown
        - json: Complete JSON representation
        - html: Styled HTML document
        - pdf: PDF document (requires additional dependencies)

    Example:
        ```json
        {
          "format": "markdown",
          "include_timestamps": true,
          "include_metrics": true
        }
        ```
    """
    try:
        debate = debate_service.get_debate(debate_id)

        # Check if debate has content
        if not debate.rounds:
            raise HTTPException(
                status_code=400,
                detail="Cannot export debate with no rounds"
            )

        # Export in requested format
        content = debate_service.export_debate(
            debate_id=debate_id,
            format=request.format.value
        )

        # Set appropriate content type
        if request.format == DebateExportFormat.JSON:
            media_type = "application/json"
            filename = f"debate_{debate_id}.json"
        elif request.format == DebateExportFormat.MARKDOWN:
            media_type = "text/markdown"
            filename = f"debate_{debate_id}.md"
        elif request.format == DebateExportFormat.HTML:
            media_type = "text/html"
            filename = f"debate_{debate_id}.html"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Format {request.format} not yet implemented"
            )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting debate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/debates/{debate_id}", response_model=SuccessResponse)
async def delete_debate(debate_id: str):
    """
    Delete a debate

    Removes a debate from active memory. Note: This does not delete any
    persistent storage, only the in-memory state.

    Args:
        debate_id: Unique debate identifier

    Returns:
        Success confirmation

    Raises:
        404: Debate not found
    """
    try:
        debate = debate_service.get_debate(debate_id)

        # Remove from active debates
        del debate_service.active_debates[debate_id]

        logger.info(f"Deleted debate {debate_id}")

        return SuccessResponse(
            message=f"Debate {debate_id} deleted successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting debate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debates", response_model=list[Debate])
async def list_debates():
    """
    List all active debates

    Returns a list of all debates currently in memory.

    Returns:
        List of Debate objects
    """
    try:
        debates = list(debate_service.active_debates.values())
        return debates

    except Exception as e:
        logger.error(f"Error listing debates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
