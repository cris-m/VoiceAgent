import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from services.agent import get_agent_client
from services.agent.models import (
    ThreadCreate,
    ThreadResponse,
    ThreadState,
    ChatRequest,
    AssistantInfo,
    ThreadMetadataUpdate,
)
from utils import get_logger
from api.dependency import verify_api_key, check_rate_limit
from api.dependency.auth import get_current_user_id
from api.dependency.security import safe_chat_message

logger = get_logger(__name__)


def _handle_agent_error(e: Exception, resource_name: str = "resource") -> HTTPException:
    error_msg = str(e).lower()

    if "not found" in error_msg or "404" in error_msg or isinstance(e, ValueError):
        return HTTPException(status_code=404, detail=f"{resource_name} not found")

    if "timeout" in error_msg or "timed out" in error_msg:
        return HTTPException(status_code=504, detail="Service timeout")

    logger.error(f"Unexpected error: {e}")
    return HTTPException(status_code=500, detail="Internal server error")

router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)


@router.get("/assistants", response_model=list[AssistantInfo])
async def list_assistants():
    client = get_agent_client()
    try:
        return await client.list_assistants()
    except Exception as e:
        logger.error(f"Failed to list assistants: {e}")
        raise HTTPException(status_code=500, detail="Failed to list assistants")


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(request: Optional[ThreadCreate] = None):
    client = get_agent_client()
    try:
        metadata = request.metadata if request else None
        return await client.create_thread(metadata=metadata)
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to create thread")


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
):
    """List threads with optional filtering."""
    client = get_agent_client()
    try:
        return await client.list_threads(limit=limit, offset=offset, status=status)
    except Exception as e:
        logger.error(f"Failed to list threads: {e}")
        raise HTTPException(status_code=500, detail="Failed to list threads")


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str):
    """Get information about a specific thread."""
    client = get_agent_client()
    try:
        return await client.get_thread(thread_id)
    except Exception as e:
        logger.error(f"Failed to get thread {thread_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """Delete a thread and all its history."""
    client = get_agent_client()
    try:
        await client.delete_thread(thread_id)
        return {"status": "deleted", "thread_id": thread_id}
    except Exception as e:
        raise _handle_agent_error(e, "Thread")


@router.patch("/threads/{thread_id}/metadata", response_model=ThreadResponse)
async def update_thread_metadata(thread_id: str, request: ThreadMetadataUpdate):
    """Update thread metadata (name, pinned, etc.)."""
    client = get_agent_client()
    try:
        return await client.update_thread_metadata(thread_id, request.metadata)
    except Exception as e:
        raise _handle_agent_error(e, "Thread")


@router.get("/threads/{thread_id}/state", response_model=ThreadState)
async def get_thread_state(thread_id: str):
    """Get the current state of a thread."""
    client = get_agent_client()
    try:
        return await client.get_thread_state(thread_id)
    except Exception as e:
        raise _handle_agent_error(e, "Thread")


@router.get("/threads/{thread_id}/history")
async def get_thread_history(
    thread_id: str,
    limit: int = Query(default=10, ge=1, le=100),
):
    """Get run history for a thread."""
    client = get_agent_client()
    try:
        return await client.get_run_history(thread_id, limit=limit)
    except Exception as e:
        logger.error(f"Failed to get history for thread {thread_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Send a message and get a non-streaming response."""
    await safe_chat_message(request.message)

    client = get_agent_client()

    try:
        if request.thread_id:
            thread_id = request.thread_id
        else:
            thread = await client.create_thread(metadata=request.metadata)
            thread_id = thread.thread_id

        result = await client.invoke(
            thread_id=thread_id,
            message=request.message,
            metadata=request.metadata,
            user_id=str(current_user_id),
            mode="chat",
        )

        return {
            "thread_id": thread_id,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat request failed")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Send a message and stream the response via Server-Sent Events."""
    try:
        await safe_chat_message(request.message)
    except HTTPException:
        raise

    client = get_agent_client()

    async def event_generator():
        try:
            if request.thread_id:
                thread_id = request.thread_id
            else:
                thread = await client.create_thread(metadata=request.metadata)
                thread_id = thread.thread_id
                yield f"data: {json.dumps({'type': 'thread', 'thread_id': thread_id})}\n\n"

            async for event in client.stream_events(
                thread_id=thread_id,
                message=request.message,
                user_id=str(current_user_id),
                mode="chat",
            ):
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/threads/{thread_id}/stream")
async def stream_in_thread(
    thread_id: str,
    message: str = Query(...),
    assistant_id: Optional[str] = Query(default=None),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Stream a response in an existing thread via SSE."""
    try:
        await safe_chat_message(message)
    except HTTPException:
        raise

    client = get_agent_client()

    async def event_generator():
        try:
            async for event in client.stream_events(
                thread_id=thread_id,
                message=message,
                assistant_id=assistant_id,
                user_id=str(current_user_id),
                mode="chat",
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Stream error in thread {thread_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/threads/{thread_id}/runs/{run_id}/join")
async def join_run_stream(thread_id: str, run_id: str):
    """Join an existing run's stream for reconnection or monitoring."""
    client = get_agent_client()

    async def event_generator():
        try:
            async for event in client.join_stream(
                thread_id=thread_id,
                run_id=run_id,
            ):
                yield f"data: {json.dumps({'event': event.event, 'data': event.data})}\n\n"
        except Exception as e:
            logger.error(f"Join stream error for run {run_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
