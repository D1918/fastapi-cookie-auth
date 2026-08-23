from typing import Dict, NamedTuple, Optional
from fastapi import HTTPException, Request, status
from fastapi.openapi.models import OAuthFlowPassword
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2


class Tokens(NamedTuple):
    access_token: str
    csrf_token: Optional[str]


class OAuth2CookieScheme(OAuth2):
    """
    OAuth2 security scheme that extracts the access token from an HttpOnly cookie
    and the CSRF token from a custom header.
    """

    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
        access_cookie_name: str = "ACCESS-TOKEN",
        csrf_header_name: str = "X-CSRF-TOKEN",
        require_csrf: bool = True,
    ):
        if not scopes:
            scopes = {}

        flows = OAuthFlowsModel(
            password=OAuthFlowPassword(tokenUrl=tokenUrl, scopes=scopes)
        )
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

        self.access_cookie_name = access_cookie_name
        self.csrf_header_name = csrf_header_name
        self.require_csrf = require_csrf

    async def __call__(  # type: ignore[override]
        self, request: Request
    ) -> Optional[Tokens]:
        access_token = request.cookies.get(self.access_cookie_name)
        csrf_token = (
            request.headers.get(self.csrf_header_name) if self.require_csrf else None
        )

        if not access_token or (self.require_csrf and not csrf_token):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None

        return Tokens(access_token=access_token, csrf_token=csrf_token)
