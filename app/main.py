import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.services.chat_service import ChatService
from app.api.routes import chat, conversations, health, stream, profile
from app.services.profile_service import ProfileService

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chat_service = ChatService.create()
    app.state.profile_service = ProfileService(app.state.chat_service.engine)
    await asyncio.to_thread(app.state.profile_service.ensure_table)
    yield

app = FastAPI(title="Text-to-SQL API", lifespan=lifespan)
origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
