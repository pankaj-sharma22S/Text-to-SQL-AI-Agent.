from fastapi import APIRouter, Request
from app.api.schemas.profile import UserProfile
router = APIRouter()

@router.get("/profile", response_model=UserProfile)
async def get_profile(request: Request):
    return await request.app.state.profile_service.get()

@router.put("/profile", response_model=UserProfile)
async def update_profile(profile: UserProfile, request: Request):
    return await request.app.state.profile_service.update(profile)
