from fastapi import APIRouter, Depends

from .user_dependencies import get_current_user

router = APIRouter()


@router.get("/user-profile")
async def protected_profile(current_user: dict = Depends(get_current_user)):
    return {"message": "Welcome to your secure profile!", "user": current_user}
