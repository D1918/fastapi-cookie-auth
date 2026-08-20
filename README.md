# FastAPI OAuth2 Cookie

A minimalist FastAPI dependency for handling OAuth2 authentication using `HttpOnly` cookies and CSRF headers. Zero third-party dependencies outside of FastAPI.

## Installation

```bash
pip install fastapi-oauth2-cookie
# or using uv:
uv add fastapi-oauth2-cookie

```

## Quickstart

This example demonstrates sign-in, sign-out, and token extraction.

**Note:** This library handles the *extraction and presence* of cookies. You are responsible for cryptographically validating the token (e.g., verifying JWT signatures) inside your `get_current_user` dependency.

```python
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_oauth2_cookie import AuthCookieManager, OAuth2PasswordCookie, Tokens

app = FastAPI()

# 1. Initialize the Cookie Manager
cookie_manager = AuthCookieManager(
    secure=False,  # Set to True in production (HTTPS)
    samesite="lax",  # "strict" is much more preferable in production
)

# 2. Configure the Dependency
oauth2_scheme = OAuth2PasswordCookie(
    tokenUrl="/sign-in",
    require_csrf=False,  # Set to True in production
)

# Dummy tokens
valid_tokens = (
    "fake-access-token",
    "new-fake-access-token",
    "fake-refresh-token",
    "new-fake-refresh-token",
)


# 3. User extraction and token validation
async def get_current_user(tokens: Tokens = Depends(oauth2_scheme)):
    if not tokens.access_token or tokens.access_token not in valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    return "user_id_123"  # Dummy user id


@app.post("/sign-in")
async def sign_in(
    response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    # Verify credentials (mocked)
    if form_data.username != "johndoe" or form_data.password != "johndoe":
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    # Generate tokens
    access_token = "fake-access-token"
    refresh_token = "fake-refresh-token"
    csrf_token = "fake-csrf-token"

    # 4. Set Both HttpOnly cookies
    cookie_manager.set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token,
        max_age_access_seconds=900,
        max_age_refresh_seconds=604800,
    )

    return {"csrf_token": csrf_token}


@app.post(cookie_manager.refresh_path)
async def refresh(request: Request, response: Response):
    # Extract the refresh token securely from the cookie
    refresh_token = request.cookies.get(cookie_manager.refresh_cookie_name)

    # IN REALITY: Validate the refresh token against your DB/JWT secret
    if not refresh_token or refresh_token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Issue new tokens (rotation)
    new_access_token = "new-fake-access-token"
    new_csrf_token = "new-fake-csrf-token"
    new_refresh_token = "new-fake-refresh-token"

    # Overwrite the old cookies with the new access token
    cookie_manager.set_auth_cookies(
        response,
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        max_age_access_seconds=900,
        max_age_refresh_seconds=604800,
    )

    return {"csrf_token": new_csrf_token}


@app.get("/users/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"user_id": current_user}


@app.post("/sign-out")
def sign_out(response: Response):
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

Handles the global configuration and injection of `Set-Cookie` headers into your FastAPI responses. 

**Initialization Parameters:**

*   **`access_cookie_name`** (`str`): The name of the cookie storing the access token. *Default: `"ACCESS-TOKEN"`*
*   **`refresh_cookie_name`** (`str`): The name of the cookie storing the refresh token. *Default: `"REFRESH-TOKEN"`*
*   **`refresh_path`** (`str`): The URL path where the refresh cookie is sent. Restricting this path enhances security by preventing the refresh token from being sent to other endpoints. *Default: `"/refresh-token"`*
*   **`secure`** (`bool`): If `True`, cookies are only sent over HTTPS. Set this to `False` during local development. *Default: `True`*
*   **`samesite`** (`"lax" | "strict" | "none"`): Controls cross-site request forgery (CSRF) protection at the browser level. `"strict"` is highly recommended for production if your frontend and API share the same site. *Default: `"lax"`*

**Methods:**

*   **`set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None, max_age_access_seconds: int = 900, max_age_refresh_seconds: int = 604800)`**: Applies configured `HttpOnly` auth cookies to the response object.
*   **`clear_auth_cookies(response: Response)`**: Instructs the browser to delete the auth cookies by expiring them and clearing their values.

### `OAuth2PasswordCookie`

The FastAPI dependency injected into your protected routes. It extracts the access token from the cookies and (optionally) the CSRF token from the headers.

**Initialization Parameters:**

*   **`tokenUrl`** (`str`): The endpoint URL where the user authenticates (e.g., `"/sign-in"`).
*   **`require_csrf`** (`bool`): If `True`, the dependency will strictly enforce the presence of the CSRF header. *Default: `True`*
*   **`access_cookie_name`** (`str`): Must match the `access_cookie_name` used in your `AuthCookieManager`. *Default: `"ACCESS-TOKEN"`*
*   **`csrf_header_name`** (`str`): The HTTP header the dependency looks for to extract the CSRF token. *Default: `"X-CSRF-TOKEN"`*
*   **`scheme_name`** (`str`, optional): Override the default scheme name used in OpenAPI documentation.
*   **`scopes`** (`dict`, optional): A dictionary of OAuth2 scopes to define permissions.
*   **`auto_error`** (`bool`): If `True`, automatically raises a `401 Unauthorized` exception if required tokens are missing. If `False`, it returns `None`, allowing for optional authentication routes. *Default: `True`*

**Returns:** 

A `Tokens` named tuple containing `(access_token, csrf_token)`.

**Raises:** 

`401 Unauthorized` if `auto_error=True` and the required tokens (access token, or CSRF token if `require_csrf=True`) are missing. *(Note: It does not check cryptographic validity, only presence).*
