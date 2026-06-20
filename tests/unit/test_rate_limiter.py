"""
tests/unit/test_rate_limiter.py
===============================

Tests unitarios del InMemoryRateLimiter (sin HTTP, sin BD).
Spec 4.3: máximo 5 intentos fallidos por IP en 15 minutos → 429.
"""

import pytest
from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter

pytestmark = pytest.mark.unit


class FakeRequest:
    """Simula request.client.host sin levantar HTTP."""
    def __init__(self, ip: str = "1.2.3.4"):
        self.client = type("C", (), {"host": ip})()


class TestInMemoryRateLimiter:
    """Lógica pura del limitador de intentos."""

    def test_permite_hasta_el_limite(self):
        limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=900)
        for _ in range(5):
            limiter.check(FakeRequest())  # no debe lanzar

    def test_sexto_intento_lanza_429_con_retry_after(self):
        limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=900)
        for _ in range(5):
            limiter.check(FakeRequest())
        with pytest.raises(HTTPException) as exc:
            limiter.check(FakeRequest())
        assert exc.value.status_code == 429
        assert "Retry-After" in exc.value.headers

    def test_ips_distintas_no_comparten_contador(self):
        limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=900)
        for _ in range(5):
            limiter.check(FakeRequest("1.1.1.1"))
        limiter.check(FakeRequest("2.2.2.2"))  # otra IP: no debe lanzar

    def test_ventana_expirada_resetea_contador(self, monkeypatch):
        """Pasados los 15 minutos, los intentos viejos se descartan."""
        import app.core.rate_limit as rl
        limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=900)

        t = [1000.0]
        monkeypatch.setattr(rl.time, "time", lambda: t[0])
        for _ in range(5):
            limiter.check(FakeRequest())

        t[0] += 901  # avanza el reloj más allá de la ventana
        limiter.check(FakeRequest())  # no debe lanzar
