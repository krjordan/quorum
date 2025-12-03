"""
Debate V2 API Routes - Sequential turn-based debate endpoints
Phase 2 implementation: Sequential debates without AI judge.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from app.models.debate_v2 import (
    DebateConfigV2,
    DebateV2,
    DebateSummary
)
from app.services.sequential_debate_service import sequential_debate_service
from app.services.summary_service import summary_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v2", response_model=DebateV2, tags=["debates"])
async def create_debate(config: DebateConfigV2):
    """
    Create a new sequential debate

    Args:
        config: Debate configuration (topic, participants, max_rounds)

    Returns:
        DebateV2: Created debate instance

    Raises:
        HTTPException: If validation fails
    """
    try:
        debate = sequential_debate_service.create_debate(config)
        logger.info(f"Created debate {debate.id}")
        return debate

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating debate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/{debate_id}", response_model=DebateV2, tags=["debates"])
async def get_debate(debate_id: str):
    """
    Get debate by ID

    Args:
        debate_id: Debate identifier

    Returns:
        DebateV2: Debate instance

    Raises:
        HTTPException: If debate not found
    """
    debate = sequential_debate_service.get_debate(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")

    return debate


@router.get("/v2/{debate_id}/next-turn", tags=["debates"])
async def stream_next_turn(debate_id: str):
    """
    Execute next participant's turn and stream the response

    Args:
        debate_id: Debate identifier

    Returns:
        StreamingResponse: SSE stream of SequentialTurnEvent objects

    Raises:
        HTTPException: If debate not found or invalid state

    Event Types:
        - debate_start: Debate begins
        - round_start: New round starts
        - participant_start: Participant begins their turn
        - chunk: Text chunk from participant's response
        - participant_complete: Participant finished their turn
        - round_complete: All participants completed current round
        - debate_complete: All rounds completed or manually stopped
        - cost_update: Cost tracking update
        - error: Error occurred
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in sequential_debate_service.get_next_turn_response(debate_id):
                yield f"data: {event.model_dump_json()}\n\n"

        except ValueError as e:
            # Debate not found or invalid state
            error_event = {
                "event_type": "error",
                "debate_id": debate_id,
                "round_number": 0,
                "turn_index": 0,
                "data": {"error": str(e)}
            }
            yield f"data: {error_event}\n\n"

        except Exception as e:
            logger.error(f"Error streaming turn for debate {debate_id}: {str(e)}")
            error_event = {
                "event_type": "error",
                "debate_id": debate_id,
                "round_number": 0,
                "turn_index": 0,
                "data": {"error": str(e)}
            }
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v2/{debate_id}/stop", response_model=DebateV2, tags=["debates"])
async def stop_debate(debate_id: str):
    """
    Manually stop a running debate

    Args:
        debate_id: Debate identifier

    Returns:
        DebateV2: Updated debate with STOPPED status

    Raises:
        HTTPException: If debate not found
    """
    try:
        debate = sequential_debate_service.stop_debate(debate_id)
        logger.info(f"Stopped debate {debate_id}")
        return debate

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping debate {debate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/{debate_id}/pause", response_model=DebateV2, tags=["debates"])
async def pause_debate(debate_id: str):
    """
    Pause a running debate

    Args:
        debate_id: Debate identifier

    Returns:
        DebateV2: Updated debate with PAUSED status

    Raises:
        HTTPException: If debate not found
    """
    try:
        debate = sequential_debate_service.pause_debate(debate_id)
        logger.info(f"Paused debate {debate_id}")
        return debate

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error pausing debate {debate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/{debate_id}/resume", response_model=DebateV2, tags=["debates"])
async def resume_debate(debate_id: str):
    """
    Resume a paused debate

    Args:
        debate_id: Debate identifier

    Returns:
        DebateV2: Updated debate with RUNNING status

    Raises:
        HTTPException: If debate not found or not paused
    """
    try:
        debate = sequential_debate_service.resume_debate(debate_id)
        logger.info(f"Resumed debate {debate_id}")
        return debate

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming debate {debate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v2/{debate_id}/summary", response_model=DebateSummary, tags=["debates"])
async def get_debate_summary(debate_id: str):
    """
    Get formatted summary of a completed or stopped debate

    Args:
        debate_id: Debate identifier

    Returns:
        DebateSummary: Formatted summary with markdown transcript and statistics

    Raises:
        HTTPException: If debate not found
    """
    try:
        debate = sequential_debate_service.get_debate(debate_id)
        if not debate:
            raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")

        summary = summary_service.generate_summary(debate)
        logger.info(f"Generated summary for debate {debate_id}")
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary for debate {debate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
