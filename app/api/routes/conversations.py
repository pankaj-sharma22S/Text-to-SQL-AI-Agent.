from fastapi import APIRouter, HTTPException, Request
from app.api.schemas.requests import CreateConversationResponse, ConversationMessageResponse
router = APIRouter()

@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(request: Request):
    return CreateConversationResponse(thread_id=request.app.state.chat_service.create_conversation())

@router.get("/conversations")
async def list_conversations(request: Request):
    return {"conversations": await request.app.state.chat_service.list_conversations()}

@router.get("/conversations/{thread_id}", response_model=list[ConversationMessageResponse])
async def get_conversation(thread_id: str, request: Request):
    rows = await request.app.state.chat_service.history(thread_id)
    if not rows: raise HTTPException(status_code=404, detail="Conversation not found")
    return [{**row, "created_at": row["created_at"].isoformat()} for row in rows]

@router.delete("/conversations/{thread_id}")
async def delete_conversation(thread_id: str, request: Request):
    rows = await request.app.state.chat_service.history(thread_id)
    if not rows: raise HTTPException(status_code=404, detail="Conversation not found")
    await request.app.state.chat_service.delete_conversation(thread_id)
    return {"deleted": True, "thread_id": thread_id}
