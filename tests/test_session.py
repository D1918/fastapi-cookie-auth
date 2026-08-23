from fastapi import FastAPI, Depends, Response
from fastapi.testclient import TestClient
from fastapi_cookie_auth.session import (
    SessionCookieManager,
    SessionCookieScheme,
    SessionCredentials,
)

app = FastAPI()

session_manager = SessionCookieManager()
session_scheme_no_csrf = SessionCookieScheme(require_csrf=False)
session_scheme_with_csrf = SessionCookieScheme(require_csrf=True)


@app.post("/login")
def login(response: Response):
    session_manager.set_cookie(response, session_id="super-session-id")
    return {"message": "Logged in"}


@app.post("/logout")
def logout(response: Response):
    session_manager.clear_cookie(response)
    return {"message": "Logged out"}


@app.get("/protected-no-csrf")
def protected_route_no_csrf(
    credentials: SessionCredentials = Depends(session_scheme_no_csrf),
):
    return {"session_id": credentials.session_id, "csrf_token": credentials.csrf_token}


@app.get("/protected-with-csrf")
def protected_route_with_csrf(
    credentials: SessionCredentials = Depends(session_scheme_with_csrf),
):
    return {"session_id": credentials.session_id, "csrf_token": credentials.csrf_token}


client = TestClient(app, base_url="https://testserver")


def test_missing_cookie_fails():
    client.cookies.clear()
    response = client.get("/protected-no-csrf")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_successful_login_and_access_no_csrf():
    client.cookies.clear()
    client.post("/login")

    response = client.get("/protected-no-csrf")

    assert response.status_code == 200
    assert response.json() == {"session_id": "super-session-id", "csrf_token": None}


def test_csrf_required_but_missing():
    client.cookies.clear()
    client.post("/login")

    response = client.get("/protected-with-csrf")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_csrf_required_and_provided():
    client.cookies.clear()
    client.post("/login")

    headers = {"X-CSRF-TOKEN": "super-csrf-token"}
    response = client.get("/protected-with-csrf", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "super-session-id",
        "csrf_token": "super-csrf-token",
    }


def test_logout_clears_cookies():
    client.cookies.clear()

    client.post("/login")
    assert client.cookies.get(session_manager.cookie_name) == "super-session-id"

    client.post("/logout")

    assert session_manager.cookie_name not in client.cookies

    response = client.get("/protected-no-csrf")
    assert response.status_code == 401
