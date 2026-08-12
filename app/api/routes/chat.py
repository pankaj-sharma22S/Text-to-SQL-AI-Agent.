from fastapi import APIRouter, HTTPException, Request
from app.api.schemas.requests import ChatRequest, ChatResponse
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    try:
        answer = await request.app.state.chat_service.chat(payload.thread_id, payload.message)
        return ChatResponse(thread_id=payload.thread_id, answer=answer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Chat processing failed") from exc
