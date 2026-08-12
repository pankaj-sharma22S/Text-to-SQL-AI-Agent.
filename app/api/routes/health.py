from fastapi import APIRouter
from app.api.schemas.requests import HealthResponse
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
