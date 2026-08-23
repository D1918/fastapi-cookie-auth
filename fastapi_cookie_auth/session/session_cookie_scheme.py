from typing import NamedTuple, Optional
from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyCookie


class SessionCredentials(NamedTuple):
    session_id: str
    csrf_token: Optional[str]


class SessionCookieScheme(APIKeyCookie):
    """
    Security scheme that extracts a session ID from an HttpOnly cookie
    and the CSRF token from a custom header.
    """

    def __init__(
        self,
        cookie_name: str = "SESSION-ID",
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
        csrf_header_name: str = "X-CSRF-TOKEN",
        require_csrf: bool = True,
    ):
        super().__init__(
            name=cookie_name, scheme_name=scheme_name, auto_error=auto_error
        )

        self.cookie_name = cookie_name
        self.csrf_header_name = csrf_header_name
        self.require_csrf = require_csrf

    async def __call__(self, request: Request) -> Optional[SessionCredentials]:
        session_id = request.cookies.get(self.cookie_name)
        csrf_token = (
            request.headers.get(self.csrf_header_name) if self.require_csrf else None
        )

        if not session_id or (self.require_csrf and not csrf_token):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )
            else:
                return None

        return SessionCredentials(session_id=session_id, csrf_token=csrf_token)
