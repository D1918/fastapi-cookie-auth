from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.testclient import TestClient
from fastapi_oauth2_cookie import AuthCookieManager, OAuth2PasswordCookie

app = FastAPI()

cookie_manager = AuthCookieManager()
oauth2_scheme_no_csrf = OAuth2PasswordCookie(tokenUrl="/login", require_csrf=False)
oauth2_scheme_with_csrf = OAuth2PasswordCookie(tokenUrl="/login", require_csrf=True)


@app.post("/login")
def login(response: Response):
    cookie_manager.set_auth_cookies(
        response, access_token="super-secret-token", refresh_token="super-refresh-token"
    )
    return {"message": "Logged in"}


@app.post("/logout")
def logout(response: Response):
    cookie_manager.clear_auth_cookies(response)
    return {"message": "Logged out"}


@app.get("/protected-no-csrf")
def protected_route_no_csrf(auth: tuple = Depends(oauth2_scheme_no_csrf)):
    access_token, csrf_token = auth
    return {"token": access_token, "csrf_token": csrf_token}


@app.get("/protected-with-csrf")
def protected_route_with_csrf(auth: tuple = Depends(oauth2_scheme_with_csrf)):
    access_token, csrf_token = auth
    return {"token": access_token, "csrf_token": csrf_token}


@app.post("/refresh-token")
def refresh_token_route(request: Request):
    refresh_token = request.cookies.get(cookie_manager.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    return {"refresh_token": refresh_token}


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
    assert response.json() == {"token": "super-secret-token", "csrf_token": None}


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
        "token": "super-secret-token",
        "csrf_token": "super-csrf-token",
    }


def test_refresh_token_set_and_accessible_on_correct_path():
    client.cookies.clear()
    login_response = client.post("/login")

    # 1. Verify Set-Cookie headers contain both tokens
    set_cookie_headers = login_response.headers.get_list("set-cookie")
    assert any(
        "ACCESS-TOKEN=super-secret-token" in cookie for cookie in set_cookie_headers
    )
    assert any(
        "REFRESH-TOKEN=super-refresh-token" in cookie for cookie in set_cookie_headers
    )
    assert any("Path=/refresh-token" in cookie for cookie in set_cookie_headers)

    # 2. Hitting the refresh route should succeed because the client sends the refresh cookie
    refresh_response = client.post("/refresh-token")
    assert refresh_response.status_code == 200
    assert refresh_response.json() == {"refresh_token": "super-refresh-token"}


def test_logout_clears_cookies():
    client.cookies.clear()

    client.post("/login")
    assert client.cookies.get(cookie_manager.access_cookie_name) == "super-secret-token"

    client.post("/logout")

    assert "ACCESS-TOKEN" not in client.cookies

    response = client.get("/protected-no-csrf")
    assert response.status_code == 401
