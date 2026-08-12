import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.api.schemas.requests import ChatRequest
router = APIRouter()

@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    async def events():
        try:
            async for item in request.app.state.chat_service.stream_chat(payload.thread_id, payload.message):
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
        except Exception:
            yield "event: error\ndata: \"Chat streaming failed\"\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
