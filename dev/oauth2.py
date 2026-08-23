from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from fastapi_cookie_auth.oauth2 import OAuth2CookieManager, OAuth2CookieScheme, Tokens

app = FastAPI(title="Dev App - OAuth2 ")

cookie_manager = OAuth2CookieManager(secure=False)

oauth2_scheme = OAuth2CookieScheme(
    tokenUrl="token",
    access_cookie_name=cookie_manager.access_cookie_name,
    require_csrf=False,  # Disabled to allow testing through Swagger UI
)

FAKE_USERS_DB = {
    "johndoe": {
        "username": "johndoe",
        "hashed_password": "fakehashedjohndoe",
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


@app.get("/")
async def root():
    return {
        "message": "Dev app is running!",
        "docs": "Go to http://127.0.0.1:8000/docs to test the auth flow.",
    }


@app.post("/token")
async def login(
    response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or fake_hash_password(form_data.password) != user["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    cookie_manager.set_auth_cookies(response, access_token=user["username"])

    return {"access_token": user["username"]}


@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}


@app.post("/logout")
def logout(response: Response):
    cookie_manager.clear_auth_cookies(response)
    return {"message": "Successfully logged out"}
