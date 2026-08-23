import uuid
from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel

from fastapi_cookie_auth.session import (
    SessionCookieManager,
    SessionCookieScheme,
    SessionCredentials,
)

app = FastAPI(title="Dev App - Session Auth")

session_manager = SessionCookieManager(secure=False)

session_scheme = SessionCookieScheme(
    cookie_name=session_manager.cookie_name,
    require_csrf=False,  # Disabled to allow testing through Swagger UI
)

FAKE_USERS_DB = {
    "johndoe": {
        "username": "johndoe",
        "hashed_password": "fakehashedjohndoe",
    }
}

FAKE_SESSIONS_DB = {}


def fake_hash_password(password: str):
    return "fakehashed" + password


async def get_current_user(credentials: SessionCredentials = Depends(session_scheme)):
    username = FAKE_SESSIONS_DB.get(credentials.session_id)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = FAKE_USERS_DB.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    return user


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/")
async def root():
    return {
        "message": "Dev app is running (Session Auth)!",
        "docs": "Go to http://127.0.0.1:8081/docs to test the auth flow.",
    }


@app.post("/login")
async def login(response: Response, login_data: LoginRequest):
    user = FAKE_USERS_DB.get(login_data.username)

    if not user or fake_hash_password(login_data.password) != user["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    session_id = str(uuid.uuid4())

    FAKE_SESSIONS_DB[session_id] = user["username"]

    session_manager.set_cookie(response, session_id=session_id)

    return {"message": "Successfully logged in"}


@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}


@app.post("/logout")
def logout(
    response: Response, credentials: SessionCredentials = Depends(session_scheme)
):
    session_manager.clear_cookie(response)

    if credentials.session_id in FAKE_SESSIONS_DB:
        del FAKE_SESSIONS_DB[credentials.session_id]

    return {"message": "Successfully logged out"}
