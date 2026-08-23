from .schemas import WebAuthTokenData


class WebAuthService:
    async def sign_in(self, email: str, password: str) -> WebAuthTokenData:
        # In a real app, verify credentials against DB.
        return WebAuthTokenData(
            access_token=f"access_token_for_{email}",
            refresh_token=f"refresh_token_for_{email}",
            csrf_token=f"csrf_token_for_{email}",
        )

    async def refresh_token(self, refresh_token: str) -> WebAuthTokenData:
        # In a real app, validate refresh token and rotate values.
        email = refresh_token.replace("refresh_token_for_", "")
        return WebAuthTokenData(
            access_token=f"new_access_token_for_{email}",
            refresh_token=f"new_refresh_token_for_{email}",
            csrf_token=f"new_csrf_token_for_{email}",
        )
