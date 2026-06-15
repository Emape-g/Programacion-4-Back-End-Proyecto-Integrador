"""
tests/integration/test_auth.py
==============================

Pruebas de integración del módulo Auth. Cubre:
  - POST /auth/register: happy path, validaciones, email duplicado.
  - POST /auth/login: OK (tokens + cookie), credenciales inválidas.
  - POST /auth/refresh: renovación del access token.
  - POST /auth/logout: revocación.
  - Rate limiting: 5 intentos fallidos por IP → 429 (spec 4.3).
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def _register(client: TestClient, email: str = "juan@test.com"):
    return client.post(REGISTER_URL, json={
        "nombre": "Juan",
        "apellido": "Perez",
        "email": email,
        "password": "Password123!",
    })


# ===========================================================================
# TESTS: POST /auth/register
# ===========================================================================
class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_returns_201_with_user_schema(self, client: TestClient, db_session):
        """Happy path: 201 con el usuario creado (sin password_hash)."""
        response = _register(client)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "juan@test.com"
        assert data["nombre"] == "Juan"
        assert "id" in data
        assert "password_hash" not in data

    def test_register_email_duplicado_returns_409(self, client: TestClient, db_session):
        """Unicidad de email validada en el servicio (spec 6.1)."""
        _register(client, "dup@test.com")
        response = _register(client, "dup@test.com")
        assert response.status_code == 409

    @pytest.mark.parametrize("payload", [
        pytest.param({"nombre": "J", "apellido": "Perez", "email": "a@t.com",
                      "password": "Password123!"}, id="nombre-muy-corto"),
        pytest.param({"nombre": "Juan", "apellido": "Perez", "email": "no-es-email",
                      "password": "Password123!"}, id="email-invalido"),
        pytest.param({"nombre": "Juan", "apellido": "Perez", "email": "a@t.com",
                      "password": "corta"}, id="password-corta"),
        pytest.param({"apellido": "Perez", "email": "a@t.com",
                      "password": "Password123!"}, id="sin-nombre"),
    ])
    def test_register_invalid_input_returns_422(self, client: TestClient, db_session, payload):
        """Datos inválidos → 422 (validación Pydantic)."""
        response = client.post(REGISTER_URL, json=payload)
        assert response.status_code == 422


# ===========================================================================
# TESTS: POST /auth/login
# ===========================================================================
class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_returns_tokens_and_cookie(self, client: TestClient, db_session):
        """Happy path: 200 con tokens en el body y cookie access_token."""
        _register(client, "login@test.com")
        response = client.post(LOGIN_URL, json={
            "email": "login@test.com", "password": "Password123!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "access_token" in response.cookies

    def test_login_credenciales_invalidas_returns_401(self, client: TestClient, db_session):
        """Email inexistente o password incorrecta → 401."""
        response = client.post(LOGIN_URL, json={
            "email": "noexiste@test.com", "password": "wrongpassword",
        })
        assert response.status_code == 401


# ===========================================================================
# TESTS: POST /auth/refresh y /auth/logout
# ===========================================================================
class TestRefreshLogout:
    """POST /api/v1/auth/refresh — POST /api/v1/auth/logout"""

    def test_refresh_renueva_access_token(self, client: TestClient, db_session):
        """Con la cookie de refresh del login, /refresh devuelve 200."""
        _register(client, "refresh@test.com")
        login = client.post(LOGIN_URL, json={
            "email": "refresh@test.com", "password": "Password123!",
        })
        assert login.status_code == 200
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_sin_cookie_returns_401(self, client: TestClient, db_session):
        """Sin refresh token no hay renovación."""
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    def test_logout_returns_204(self, client: TestClient, client_headers):
        """Logout con sesión activa → 204 No Content."""
        response = client.post("/api/v1/auth/logout", headers=client_headers)
        assert response.status_code == 204


# ===========================================================================
# TESTS: Rate limiting (spec 4.3 — 5 intentos fallidos / 15 min por IP)
# ===========================================================================
class TestRateLimit:
    """Login/Register rate limited: 6to intento → 429 con Retry-After."""

    def test_sexto_intento_fallido_returns_429(self, client: TestClient, db_session):
        for i in range(5):
            client.post(LOGIN_URL, json={
                "email": f"ratelimit{i}@test.com", "password": "wrong",
            })
        response = client.post(LOGIN_URL, json={
            "email": "ratelimit_extra@test.com", "password": "wrong",
        })
        assert response.status_code == 429
        assert "Retry-After" in response.headers
