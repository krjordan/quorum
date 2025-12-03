import uuid
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from app.models.chat import ChatCompletionRequest, ChatCompletionResponse, StreamChunk
from app.services.llm_service import llm_service

router = APIRouter()


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    try:
        messages = []
        if request.conversation_history:
            messages.extend([
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ])
        messages.append({"role": "user", "content": request.message})

        response_content = await llm_service.get_completion(
            messages=messages,
            model=request.model,
        )

        return ChatCompletionResponse(
            id=str(uuid.uuid4()),
            content=response_content,
            model=request.model or llm_service.default_model,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_chat_completion(request: ChatCompletionRequest):
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Build message history
            messages = []
            if request.conversation_history:
                messages.extend([
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_history
                ])
            messages.append({"role": "user", "content": request.message})

            chunk_id = str(uuid.uuid4())

            async for content_chunk in llm_service.stream_completion(
                messages=messages,
                model=request.model,
            ):
                chunk = StreamChunk(
                    id=chunk_id,
                    content=content_chunk,
                    done=False,
                )
                yield f"data: {chunk.model_dump_json()}\n\n"

            final_chunk = StreamChunk(
                id=chunk_id,
                content="",
                done=True,
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"

        except Exception as e:
            error_chunk = {
                "id": str(uuid.uuid4()),
                "content": f"Error: {str(e)}",
                "done": True,
                "error": True,
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
