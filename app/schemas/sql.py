from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class SQLQuery(BaseModel):
    sql: str = Field(description="A read-only SQL query")
    explanation: str = Field(description="Brief explanation")

SQLGeneration = SQLQuery

class MemoryUpdate(BaseModel):
    preferences: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    important_context: list[str] = Field(default_factory=list)

class ConversationMessage(BaseModel):
    thread_id: str = Field(min_length=1)
    role: Literal["user", "assistant"]
    message: str = Field(min_length=1)
    created_at: datetime | None = None
