from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    message: str = Field(min_length=1)

class CreateConversationResponse(BaseModel):
    thread_id: str

class ChatResponse(BaseModel):
    thread_id: str
    answer: str

class ConversationMessageResponse(BaseModel):
    thread_id: str
    role: str
    message: str
    created_at: str

class HealthResponse(BaseModel):
    status: str
