from typing import Literal
from fastapi import Response


class SessionCookieManager:
    """
    Basic session cookie management
    """

    def __init__(
        self,
        cookie_name: str = "SESSION-ID",
        secure: bool = True,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ):
        self.cookie_name = cookie_name
        self.secure = secure
        self.samesite: Literal["lax", "strict", "none"] = samesite

    def set_cookie(
        self,
        response: Response,
        session_id: str,
        max_age_seconds: int = 86400,
    ) -> None:
        """Sets the session cookie."""
        response.set_cookie(
            key=self.cookie_name,
            value=session_id,
            httponly=True,
            secure=self.secure,
            samesite=self.samesite,
            max_age=max_age_seconds,
        )

    def clear_cookie(self, response: Response) -> None:
        """Clears the session cookie."""
        response.delete_cookie(
            key=self.cookie_name,
            secure=self.secure,
            samesite=self.samesite,
            httponly=True,
        )
