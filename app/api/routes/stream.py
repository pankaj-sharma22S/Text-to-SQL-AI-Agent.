import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.api.schemas.requests import ChatRequest
from app.guardrails.input import InputGuardrailError
router = APIRouter()

@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    async def events():
        try:
            async for item in request.app.state.chat_service.stream_chat(payload.thread_id, payload.message):
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
        except InputGuardrailError as exc:
            yield f"event: error\ndata: {json.dumps(str(exc))}\n\n"
        except Exception as exc:
            from app.llm.model import safe_provider_error
            yield f"event: error\ndata: {json.dumps(safe_provider_error(exc))}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
