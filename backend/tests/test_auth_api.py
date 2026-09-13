def test_register_login_me_flow(client):
    resp = client.post("/auth/register", json={"email": "flow@example.com", "password": "password123", "full_name": "Flow"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "flow@example.com"
    assert "hashed_password" not in resp.json()

    resp = client.post("/auth/login", json={"email": "flow@example.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" not in body  # refresh token must never appear in the JSON body
    # the refresh token must be set as an httpOnly cookie instead
    assert "refresh_token" in resp.cookies

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "flow@example.com"


def test_login_sets_httponly_refresh_cookie(client):
    client.post("/auth/register", json={"email": "cookie@example.com", "password": "password123", "full_name": "C"})
    resp = client.post("/auth/login", json={"email": "cookie@example.com", "password": "password123"})
    assert resp.status_code == 200
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "path=/auth" in set_cookie_header.lower()


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "password123", "full_name": "Dupe"}
    resp1 = client.post("/auth/register", json=payload)
    assert resp1.status_code == 201
    resp2 = client.post("/auth/register", json=payload)
    assert resp2.status_code == 400


def test_login_wrong_password_rejected_with_generic_message(client):
    client.post("/auth/register", json={"email": "wp@example.com", "password": "password123", "full_name": "WP"})
    resp = client.post("/auth/login", json={"email": "wp@example.com", "password": "wrong-password"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


def test_login_nonexistent_user_same_generic_message(client):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


def test_register_rejects_short_password(client):
    resp = client.post("/auth/register", json={"email": "short@example.com", "password": "short", "full_name": "S"})
    assert resp.status_code == 422  # pydantic min_length validation


def test_refresh_uses_cookie_to_issue_new_access_token(client):
    client.post("/auth/register", json={"email": "refresh@example.com", "password": "password123", "full_name": "R"})
    login = client.post("/auth/login", json={"email": "refresh@example.com", "password": "password123"})
    assert "refresh_token" in client.cookies  # TestClient persists cookies across requests

    resp = client.post("/auth/refresh")
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_rotates_the_cookie(client):
    client.post("/auth/register", json={"email": "rotate@example.com", "password": "password123", "full_name": "R"})
    client.post("/auth/login", json={"email": "rotate@example.com", "password": "password123"})
    first_cookie = client.cookies.get("refresh_token")

    resp = client.post("/auth/refresh")
    assert resp.status_code == 200
    second_cookie = client.cookies.get("refresh_token")
    assert second_cookie != first_cookie  # rotated, not reused


def test_refresh_without_cookie_returns_401(client):
    resp = client.post("/auth/refresh")
    assert resp.status_code == 401


def test_logout_clears_refresh_cookie(client):
    client.post("/auth/register", json={"email": "logout@example.com", "password": "password123", "full_name": "L"})
    login = client.post("/auth/login", json={"email": "logout@example.com", "password": "password123"})
    access_token = login.json()["access_token"]

    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 204

    # after logout, the refresh cookie should no longer work
    refresh_resp = client.post("/auth/refresh")
    assert refresh_resp.status_code == 401


def test_protected_route_without_token_returns_401(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_protected_route_with_garbage_token_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_login_rate_limited_after_repeated_attempts(client):
    email = "ratelimited@example.com"
    client.post("/auth/register", json={"email": email, "password": "password123", "full_name": "RL"})

    responses = [
        client.post("/auth/login", json={"email": email, "password": "wrong-password"})
        for _ in range(15)
    ]
    statuses = [r.status_code for r in responses]
    assert 429 in statuses  # the 10/minute limit on /auth/login must eventually kick in


def test_register_rate_limited_after_repeated_attempts(client):
    responses = [
        client.post("/auth/register", json={"email": f"spam{i}@example.com", "password": "password123", "full_name": "S"})
        for i in range(10)
    ]
    statuses = [r.status_code for r in responses]
    assert 429 in statuses  # the 5/minute limit on /auth/register must eventually kick in
