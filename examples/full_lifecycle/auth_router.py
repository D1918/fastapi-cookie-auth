from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_oauth2_cookie import AuthCookieManager

from .settings import PRODUCTION_MODE
from .schemas import CSRFToken
from .auth_service import WebAuthService
from .user_dependencies import get_auth_service

router = APIRouter()

cookie_manager = AuthCookieManager(
    secure=PRODUCTION_MODE,
    samesite="strict" if PRODUCTION_MODE else "lax",
)


@router.post("/sign-in", response_model=CSRFToken)
async def sign_in(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: WebAuthService = Depends(get_auth_service),
):
    tokens = await service.sign_in(form_data.username, form_data.password)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
        )

    cookie_manager.set_auth_cookies(
        response=response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        max_age_access_seconds=900,
        max_age_refresh_seconds=604800,
    )

    return CSRFToken(csrf_token=tokens.csrf_token)


@router.post("/refresh-token", response_model=CSRFToken)
async def refresh_token(
    response: Response,
    request: Request,
    service: WebAuthService = Depends(get_auth_service),
):
    refresh_token = request.cookies.get(cookie_manager.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No refresh token found in cookies",
        )

    tokens = await service.refresh_token(refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    cookie_manager.set_auth_cookies(
        response=response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        max_age_access_seconds=900,
        max_age_refresh_seconds=604800,
    )

    return CSRFToken(csrf_token=tokens.csrf_token)


@router.post("/sign-out")
async def sign_out(response: Response):
    cookie_manager.clear_auth_cookies(response)
    return {"message": "Successfully signed out"}
