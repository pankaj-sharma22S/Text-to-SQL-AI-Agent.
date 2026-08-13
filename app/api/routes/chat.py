from fastapi import APIRouter, HTTPException, Request
from app.api.schemas.requests import ChatRequest, ChatResponse
from app.guardrails.input import InputGuardrailError
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    try:
        answer = await request.app.state.chat_service.chat(payload.thread_id, payload.message)
        return ChatResponse(thread_id=payload.thread_id, answer=answer)
    except InputGuardrailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        from app.llm.model import safe_provider_error
        raise HTTPException(status_code=502, detail=safe_provider_error(exc)) from exc
