# FastAPI OAuth2 Cookie

A minimalist FastAPI dependency for handling OAuth2 authentication using `HttpOnly` cookies and CSRF headers. Zero third-party dependencies outside of FastAPI.

## Installation

```bash
pip install fastapi-oauth2-cookie
# or using uv:
uv add fastapi-oauth2-cookie

```

## Quickstart

This example demonstrates login, logout, and token extraction.

**Note:** This library handles the *extraction and presence* of cookies. You are responsible for cryptographically validating the token (e.g., verifying JWT signatures) inside your `get_current_user` dependency.

```python
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_oauth2_cookie import AuthCookieManager, OAuth2PasswordCookie, Tokens

app = FastAPI()

# 1. Initialize the Cookie Manager
cookie_manager = AuthCookieManager(
    secure=False, # Set to True in production (HTTPS)
    samesite="lax" # "strict" is much more preferable production
)

# 2. Configure the Dependency
oauth2_scheme = OAuth2PasswordCookie(
    tokenUrl="/login",
    require_csrf=False
)

# 3. User extraction and token validation
async def get_current_user(tokens: Tokens = Depends(oauth2_scheme)):
    # IN REALITY: Validate your JWT here
    valid_tokens = ("fake-jwt-token", "new-fake-jwt-token")
    if not tokens.access_token or tokens.access_token not in valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
        
    return "user_id_123" # Dummy user id

@app.post("/login")
async def login(
    response: Response, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Verify credentials (mocked)
    if form_data.username != "admin" or form_data.password != "secret":
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    # Generate tokens
    access_token = "fake-jwt-token"
    refresh_token = "fake-refresh-token"
    csrf_token = "fake-csrf-token"

    # 4. Set Both HttpOnly cookies
    cookie_manager.set_auth_cookies(
        response, 
        access_token=access_token,
        refresh_token=refresh_token
    )
    
    return {"csrf_token": csrf_token}

# 5. The Refresh Endpoint
@app.post("/refresh")
async def refresh(request: Request, response: Response):
    # Extract the refresh token securely from the cookie
    refresh_token = request.cookies.get(cookie_manager.refresh_cookie_name)
    
    # IN REALITY: Validate the refresh token against your DB/JWT secret
    if not refresh_token or refresh_token != "fake-refresh-token":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Issue new tokens (rotation)
    new_access_token = "new-fake-jwt-token"
    new_csrf_token = "new-fake-csrf-token"

    # Overwrite the old cookies with the new access token
    cookie_manager.set_auth_cookies(
        response, 
        access_token=new_access_token,
        refresh_token=refresh_token # Or issue a new one if rotating refresh tokens
    )
    
    return {"csrf_token": new_csrf_token}

@app.get("/users/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"user_id": current_user}

@app.post("/logout")
def logout(response: Response):
    # Clears both access and refresh cookies
    cookie_manager.clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
```

## Technical Caveats

### CSRF Implementation

When you initialize `OAuth2PasswordCookie` with `require_csrf=True`, the dependency will strictly enforce the presence of the `X-CSRF-TOKEN` header.

* **The Catch:** This library does *not* issue CSRF tokens. You must generate the CSRF token and deliver it to your frontend yourself (e.g., via a standard, non-HttpOnly cookie or a separate meta endpoint) so the client can read it and attach it to subsequent API headers.

### Swagger UI Compatibility

This package is fully compatible with FastAPI’s Swagger UI. Authentication is supported both through the sign-in route and via the “Authorize” button in the Swagger UI.

* **The Catch:** If `require_csrf=True`, Swagger UI's "Try it out" feature will fail with `401 Unauthorized`. Swagger does not natively know how to extract or attach your custom `X-CSRF-TOKEN` header. You will need to disable CSRF requirements in your dev/swagger environment or inject custom JS into the Swagger template to handle the header.

* **Solution:** Disable CSRF protection when running outside production by setting require_csrf=False in development. This keeps Swagger UI usable locally while ensuring CSRF protection remains enabled in production.

## Core API

### `AuthCookieManager`

Handles configuration and injection of `Set-Cookie` headers.

* `set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None, ...)`: Applies configured `HttpOnly` auth cookies to the response object.
* `clear_auth_cookies(response: Response)`: Instructs the browser to delete the auth cookies.

### `OAuth2PasswordCookie`

The FastAPI dependency injected into protected routes.

* Extracts the token from `request.cookies`.
* Extracts the CSRF token from `request.headers` (defaults to `X-CSRF-TOKEN`).
* **Returns:** A `Tokens` named tuple containing `(access_token, csrf_token)`.
* **Raises:** `401 Unauthorized` if required tokens are *missing* (does not check validity).
