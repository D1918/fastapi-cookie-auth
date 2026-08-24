# FastAPI Cookie Auth

A lightweight FastAPI library for secure cookie-based authentication, supporting both OAuth2 flows and standard Sessions with built-in CSRF protection. Zero third-party dependencies outside of FastAPI.

## Installation

```bash
pip install fastapi-cookie-auth
# or using uv:
uv add fastapi-cookie-auth

```

## Quickstart

This library supports two paradigms: **OAuth2** (access and refresh tokens) and **Sessions** (single session identifier).

**Note:** This library handles the *extraction and presence* of cookies. You are responsible for cryptographically validating the token (e.g., verifying a JWT signature) or looking up the token/session in your database inside your dependency.

### Option 1: OAuth2 Authentication

This example demonstrates sign-in, sign-out, token rotation, and extraction using standard OAuth2 flows. This integrates cleanly with FastAPI's native OAuth2 Swagger UI.

```python
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_cookie_auth import OAuth2CookieManager, OAuth2CookieScheme, Tokens

app = FastAPI()

# 1. Initialize the Cookie Manager
oauth2_manager = OAuth2CookieManager(
    secure=False,  # Set to True in production (HTTPS)
    samesite="lax",
    refresh_path="/refresh-token",  # this path should be the same as router' refresh path
)

# 2. Configure the Dependency
oauth2_scheme = OAuth2CookieScheme(
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
    oauth2_manager.set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token,
        max_age_access_seconds=900,
        max_age_refresh_seconds=604800,
    )

    return {"csrf_token": csrf_token}


@app.post("/refresh-token")
async def refresh_token(request: Request, response: Response):
    # Extract the refresh token securely from the cookie
    refresh_token = request.cookies.get(oauth2_manager.refresh_cookie_name)

    # IN REALITY: Validate the refresh token against your DB/JWT secret
    if not refresh_token or refresh_token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Issue new tokens (rotation)
    new_access_token = "new-fake-access-token"
    new_csrf_token = "new-fake-csrf-token"
    new_refresh_token = "new-fake-refresh-token"

    # Overwrite the old cookies with the new access token
    oauth2_manager.set_auth_cookies(
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
    oauth2_manager.clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
```

### Option 2: Session Authentication

If you prefer a standard session cookie without the complexity of refresh tokens, use the Session Authentication. This registers natively as an `APIKey` cookie in your OpenAPI schema.

```python
from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel
from fastapi_cookie_auth import (
    SessionCookieManager,
    SessionCookieScheme,
    SessionCredentials,
)

app = FastAPI()

# 1. Initialize the Session Manager
session_manager = SessionCookieManager(
    secure=False, samesite="lax"  # Set to True in production
)

# 2. Configure the Dependency
session_scheme = SessionCookieScheme(
    require_csrf=False,  # Set to True in production
)


class LoginRequest(BaseModel):
    username: str
    password: str


# 3. Session extraction and validation
async def get_session_user(credentials: SessionCredentials = Depends(session_scheme)):
    # IN REALITY: Look up credentials.session_id in your database/Redis
    if credentials.session_id != "valid-session-id":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )
    return "user_id_456"


@app.post("/sign-in")
async def login(response: Response, login_data: LoginRequest):
    if login_data.username != "johndoe" or login_data.password != "johndoe":
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    session_id = "valid-session-id"
    csrf_token = "fake-csrf-token"

    # 4. Set the session cookie
    session_manager.set_cookie(response, session_id=session_id)
    return {"csrf_token": csrf_token}


@app.get("/profile")
async def profile(user_id: str = Depends(get_session_user)):
    return {"user_id": user_id}


@app.post("/sign-out")
def logout(response: Response):
    # IN REALITY: Also delete the session from your database/Redis here
    session_manager.clear_cookie(response)
    return {"message": "Logged out"}
```

## Core API

### OAuth2 Implementation

#### `OAuth2CookieManager`

Handles the global configuration and injection of `Set-Cookie` headers into your FastAPI responses for OAuth2 flows.

**Initialization Parameters:**

* **`access_cookie_name`** (`str`): The name of the cookie storing the access token. *Default*: `"ACCESS-TOKEN"`
* **`refresh_cookie_name`** (`str`): The name of the cookie storing the refresh token. *Default*: `"REFRESH-TOKEN"`
* **`refresh_path`** (`str`): The Absolute URL path where the refresh cookie is sent. Restricting this path enhances security by preventing the refresh token from being sent to other endpoints. *Default*: `"/refresh-token"`. This must exactly match the path of your FastAPI refresh route.
* **`secure`** (`bool`): If `True`, cookies are only sent over HTTPS. Set this to `False` during local development. *Default*: `True`
* **`samesite`** (`"lax" | "strict" | "none"`): Controls cross-site request forgery (CSRF) protection at the browser level. `"strict"` is highly recommended for production if your frontend and API share the same site. *Default*: `"lax"`

**Methods:**

* **`set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None, max_age_access_seconds: int = 900, max_age_refresh_seconds: int = 604800)`**: Applies configured `HttpOnly` auth cookies to the response object.
* **`clear_auth_cookies(response: Response)`**: Instructs the browser to delete the auth cookies by expiring them and clearing their values.

#### `OAuth2CookieScheme`

The FastAPI dependency injected into your protected routes. Extracts the access token and CSRF token, and registers the OAuth2 scheme in OpenAPI.

**Initialization Parameters:**

* **`tokenUrl`** (`str`): The endpoint URL where the user authenticates (e.g., `"/sign-in"`).
* **`require_csrf`** (`bool`): If `True`, the dependency will strictly enforce the presence of the CSRF header. *Default*: `True`
* **`access_cookie_name`** (`str`): Must match the `access_cookie_name` used in your `OAuth2CookieManager`. *Default*: `"ACCESS-TOKEN"`
* **`csrf_header_name`** (`str`): The HTTP header the dependency looks for to extract the CSRF token. *Default*: `"X-CSRF-TOKEN"`
* **`scheme_name`** (`str`, optional): Override the default scheme name used in OpenAPI documentation.
* **`scopes`** (`dict`, optional): A dictionary of OAuth2 scopes to define permissions.
* **`auto_error`** (`bool`): If `True`, automatically raises a `401 Unauthorized` exception if required tokens are missing. If `False`, it returns `None`. *Default*: `True`

**Returns:** A `Tokens` named tuple containing `(access_token, csrf_token)`.

---

### Session Auth Implementation

#### `SessionCookieManager`

Handles the global configuration and injection of `Set-Cookie` headers for session-based flows.

**Initialization Parameters:**

* **`cookie_name`** (`str`): The name of the cookie storing the session ID. *Default*: `"SESSION-ID"`
* **`secure`** (`bool`): If `True`, cookies are only sent over HTTPS. *Default*: `True`
* **`samesite`** (`"lax" | "strict" | "none"`): Controls CSRF protection. *Default*: `"lax"`

**Methods:**

* **`set_cookie(response: Response, session_id: str, max_age_seconds: int = 86400)`**: Sets the `HttpOnly` session cookie.
* **`clear_cookie(response: Response)`**: Instructs the browser to delete the session cookie.

#### `SessionCookieScheme`

The FastAPI dependency injected into your protected routes. Extracts the session ID and CSRF token. Registers natively as an APIKeyCookie in OpenAPI.

**Initialization Parameters:**

* **`require_csrf`** (`bool`): If `True`, strictly enforces the CSRF header. *Default*: `True`
* **`cookie_name`** (`str`): Must match the `cookie_name` in your manager. *Default*: `"SESSION-ID"`
* **`csrf_header_name`** (`str`): The HTTP header for the CSRF token. *Default*: `"X-CSRF-TOKEN"`
* **`scheme_name`** (`str`, optional): Override the OpenAPI scheme name.
* **`auto_error`** (`bool`): Raise `401` on missing credentials or return `None`. *Default*: `True`

**Returns:** A `SessionCredentials` named tuple containing `(session_id, csrf_token)`.

## Technical Caveats

### CSRF Implementation

When you initialize `OAuth2CookieScheme` or `SessionCookieScheme` with `require_csrf=True`, the dependency will strictly enforce the presence of the `X-CSRF-TOKEN` header.

* **The Catch:** This library does *not* issue CSRF tokens. 

* **Solution:** You must generate the CSRF token and deliver it to your frontend yourself (e.g., via sign-in endpoint) so the client can read it and attach it to subsequent API headers.

### Swagger UI Compatibility

This package is fully compatible with FastAPI’s Swagger UI. OAuth2-based authentication is supported both through the sign-in route and the Swagger UI’s “Authorize” button, while session-based authentication requires users to authenticate through the sign-in route.

* **The Catch:** If `require_csrf=True`, Swagger UI's "Try it out" feature will fail with `401 Unauthorized`. Swagger does not natively know how to extract or attach your custom `X-CSRF-TOKEN` header.

* **Solution:** Disable CSRF protection when running outside production by setting `require_csrf=False` in development. This keeps Swagger UI usable locally while ensuring CSRF protection remains enabled in production.
