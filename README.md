# FastAPI OAuth2 Cookie Authentication

A lightweight, production-ready FastAPI library for handling OAuth2 authentication using **HttpOnly Cookies** and **CSRF headers**.

## Features

* 🔒 **HttpOnly Cookies**: Keeps JWT access and refresh tokens out of `localStorage` to prevent XSS attacks.
* ⚡️ **Swagger UI Compatible**: Extends FastAPI's native `OAuth2` class to keep your OpenAPI docs working.
* 🛡️ **CSRF Defense**: Native support for extracting and requiring CSRF tokens via headers (`X-CSRF-TOKEN`).
* 🪶 **Zero Overhead**: No third-party dependencies outside of FastAPI.

## Installation

```bash
pip install fastapi-oauth2-cookie
# or using uv:
uv add fastapi-oauth2-cookie

```

## Quickstart

Here is everything you need to set up login, logout, and a protected route.

```python
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_oauth2_cookie import AuthCookieManager, OAuth2PasswordCookie, Tokens

app = FastAPI()

cookie_manager = AuthCookieManager(secure=False) # set True in production

oauth2_scheme = OAuth2PasswordCookie(
    tokenUrl="token",
    access_cookie_name=cookie_manager.access_cookie_name,
    require_csrf=False # set to True in production to avoid CSRF attacks 
)

FAKE_USERS_DB = {
    "johndoe": {
        "username": "johndoe",
        "hashed_password": "fakehashedsecretpassword",
    }
}

def fake_hash_password(password: str):
    return "fakehashed" + password

def fake_decode_token(token: str):
    return FAKE_USERS_DB.get(token)

async def get_current_user(tokens: Tokens = Depends(oauth2_scheme)):
    user = fake_decode_token(tokens.access_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user

@app.post("/token")
async def login(
    response: Response, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or fake_hash_password(form_data.password) != user["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Incorrect username or password"
        )

    # 1. Set the HttpOnly cookie for the browser
    cookie_manager.set_auth_cookies(response, access_token=user["username"])
    
    # 2. Return standard OAuth2 JSON so Swagger UI works correctly
    return {"access_token": user["username"], "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}

@app.post("/logout")
def logout(response: Response):
    cookie_manager.clear_auth_cookies(response)
    return {"message": "Successfully logged out"}

```

## Core API

### `AuthCookieManager`

Handles the configuration and application of cookies

* `set_auth_cookies(response, access_token, refresh_token=None, ...)`: Attaches `HttpOnly` cookies to the response.
* `clear_auth_cookies(response)`: Clears the authentication cookies.

### `OAuth2PasswordCookie`

The FastAPI dependency you inject into your routes.

* Extracts the token from the configured `access_cookie_name`.
* Optionally enforces and extracts a CSRF token from the `csrf_header_name` (defaults to `X-CSRF-TOKEN`).
* Returns a named tuple `Tokens`: `(access_token, csrf_token)`. Raises `401 Unauthorized` if tokens are missing or invalid.

## Development

### Run dev server
```bash
uv run fastapi dev dev/main.py
```

### Run tests
```bash
uv run pytest
```

## License

MIT
