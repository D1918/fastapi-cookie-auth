from typing import Literal, Optional
from fastapi import Response


class OAuth2CookieManager:
    """
    Basic auth cookie management
    """

    def __init__(
        self,
        access_cookie_name: str = "ACCESS-TOKEN",
        refresh_cookie_name: str = "REFRESH-TOKEN",
        refresh_path: str = "/refresh-token",
        secure: bool = True,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ):
        self.access_cookie_name: str = access_cookie_name
        self.refresh_cookie_name: str = refresh_cookie_name
        self.refresh_path = refresh_path
        self.secure: bool = secure
        self.samesite: Literal["lax", "strict", "none"] = samesite

    def set_auth_cookies(
        self,
        response: Response,
        access_token: str,
        refresh_token: Optional[str] = None,
        max_age_access_seconds: int = 900,
        max_age_refresh_seconds: int = 604800,
    ) -> None:
        """Sets auth cookies using the manager's global configuration."""
        response.set_cookie(
            key=self.access_cookie_name,
            value=access_token,
            httponly=True,
            secure=self.secure,
            samesite=self.samesite,
            max_age=max_age_access_seconds,
        )
        if refresh_token:
            response.set_cookie(
                key=self.refresh_cookie_name,
                value=refresh_token,
                path=self.refresh_path,
                httponly=True,
                secure=self.secure,
                samesite=self.samesite,
                max_age=max_age_refresh_seconds,
            )

    def clear_auth_cookies(self, response: Response) -> None:
        """Clears auth cookies using the manager's global configuration."""
        response.delete_cookie(
            key=self.access_cookie_name,
            secure=self.secure,
            samesite=self.samesite,
            httponly=True,
        )
        response.delete_cookie(
            key=self.refresh_cookie_name,
            secure=self.secure,
            samesite=self.samesite,
            httponly=True,
            path=self.refresh_path,
        )
