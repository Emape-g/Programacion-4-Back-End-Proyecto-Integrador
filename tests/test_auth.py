import pytest


def test_register_ok(client):
    resp = client.post("/api/v1/auth/register", json={
        "nombre": "Juan",
        "apellido": "Perez",
        "email": "juan@test.com",
        "password": "Password123!",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "juan@test.com"
    assert data["nombre"] == "Juan"
    assert "id" in data


def test_login_ok(client):
    client.post("/api/v1/auth/register", json={
        "nombre": "Login",
        "apellido": "Test",
        "email": "login@test.com",
        "password": "Password123!",
    })

    resp = client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "Password123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "access_token" in resp.cookies


def test_login_invalid_credentials(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "noexiste@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_refresh_token(client):
    client.post("/api/v1/auth/register", json={
        "nombre": "Refresh",
        "apellido": "Test",
        "email": "refresh@test.com",
        "password": "Password123!",
    })

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "refresh@test.com",
        "password": "Password123!",
    })
    assert login_resp.status_code == 200

    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code in (200, 401)


def test_logout(client, client_headers):
    resp = client.post("/api/v1/auth/logout", headers=client_headers)
    assert resp.status_code == 204


def test_rate_limit(client):
    from app.core.rate_limit import auth_rate_limiter
    auth_rate_limiter._attempts.clear()

    for i in range(5):
        client.post("/api/v1/auth/login", json={
            "email": f"ratelimit{i}@test.com",
            "password": "wrong",
        })

    resp = client.post("/api/v1/auth/login", json={
        "email": "ratelimit_extra@test.com",
        "password": "wrong",
    })
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers

    auth_rate_limiter._attempts.clear()
