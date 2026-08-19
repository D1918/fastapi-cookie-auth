from fastapi import Depends, HTTPException, status
from fastapi_oauth2_cookie import OAuth2PasswordCookie, Tokens

from examples.full_lifecycle.settings import PRODUCTION_MODE
from .auth_service import WebAuthService

oauth2_scheme = OAuth2PasswordCookie(
    tokenUrl="/sign-in",
    require_csrf=PRODUCTION_MODE,
)


def get_auth_service() -> WebAuthService:
    return WebAuthService()


async def get_current_user(tokens: Tokens = Depends(oauth2_scheme)) -> dict:
    """
    Simplified user dependency. In real app you should do heavy DB/JWT checks.
    """
    access_token = tokens.access_token

    if not access_token or "access_token_for_" not in access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    email = access_token.replace("access_token_for_", "").replace(
        "new_access_token_for_", ""
    )
    return {"email": email, "is_active": True}
