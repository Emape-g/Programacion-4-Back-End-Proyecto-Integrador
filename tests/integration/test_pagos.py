"""
tests/integration/test_pagos.py
===============================

Pruebas del módulo Pagos (MercadoPago). El SDK se mockea: los tests
NO pegan a la API de MP. Cubre:
  - POST /pagos/crear: pago aprobado confirma el pedido, permisos,
    estados inválidos, idempotency_key.
  - POST /pagos/webhook: topic=payment aprueba pedido, topics ajenos
    se ignoran, validación de firma x-signature (spec 5.4).
"""

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

CREAR_URL = "/api/v1/pagos/crear"
WEBHOOK_URL = "/api/v1/pagos/webhook"


class FakePaymentClient:
    """Imita sdk.payment(): .create() y .get() con respuestas armadas."""

    def __init__(self, estado_create: str, payments_db: dict):
        self._estado = estado_create
        self._payments = payments_db

    def create(self, payment_data, request_options=None):
        # Refleja el monto y registra el pago "en MP" para que luego
        # el webhook pueda consultarlo por id.
        pago_mp = {
            "id": 999111,
            "status": self._estado,
            "status_detail": "accredited" if self._estado == "approved" else "pending_contingency",
            "transaction_amount": payment_data["transaction_amount"],
            "payment_method_id": payment_data.get("payment_method_id"),
            "external_reference": payment_data["external_reference"],
        }
        self._payments[999111] = pago_mp
        return {"status": 201, "response": pago_mp}

    def get(self, payment_id):
        return {"status": 200, "response": self._payments.get(int(payment_id), {})}


@pytest.fixture
def mock_mp(monkeypatch):
    """
    Reemplaza mercadopago.SDK por un fake. `estado["create"]` controla
    qué devuelve MP al crear el pago (approved / in_process / rejected).
    """
    import app.modules.pagos.service as pagos_service

    estado = {"create": "approved", "payments": {}}

    class FakeSDK:
        def __init__(self, *args, **kwargs):
            pass

        def payment(self):
            return FakePaymentClient(estado["create"], estado["payments"])

    monkeypatch.setattr(pagos_service.mercadopago, "SDK", FakeSDK)
    return estado


def _body_pago(pedido_id: int) -> dict:
    return {
        "pedido_id": pedido_id,
        "token": "tok_test_123",
        "payment_method_id": "visa",
        "installments": 1,
        "payer_email": "client_test@test.com",
    }


# ===========================================================================
# TESTS: POST /pagos/crear
# ===========================================================================
class TestCrearPago:
    """POST /api/v1/pagos/crear (CLIENT, pedido propio en PENDIENTE)"""

    def test_pago_aprobado_confirma_pedido(
        self, client: TestClient, client_user, client_headers,
        admin_headers, pedido_factory, mock_mp,
    ):
        """Happy path: 201, mp_status=approved y pedido → CONFIRMADO."""
        pedido = pedido_factory(client_user["id"], estado="PENDIENTE")
        response = client.post(
            CREAR_URL, json=_body_pago(pedido["id"]), headers=client_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["mp_status"] == "approved"
        assert data["idempotency_key"]  # UUID generado por el backend
        assert data["external_reference"]

        # El pedido avanzó a CONFIRMADO con su registro de historial
        detalle = client.get(f"/api/v1/pedidos/{pedido['id']}", headers=admin_headers)
        assert detalle.json()["estado_codigo"] == "CONFIRMADO"
        historial = client.get(
            f"/api/v1/pedidos/{pedido['id']}/historial", headers=admin_headers,
        ).json()
        assert historial[-1]["estado_hacia"] == "CONFIRMADO"

    def test_pago_pendiente_no_confirma_pedido(
        self, client: TestClient, client_user, client_headers,
        admin_headers, pedido_factory, mock_mp,
    ):
        """Si MP devuelve in_process, el pedido sigue PENDIENTE."""
        mock_mp["create"] = "in_process"
        pedido = pedido_factory(client_user["id"], estado="PENDIENTE")
        response = client.post(
            CREAR_URL, json=_body_pago(pedido["id"]), headers=client_headers,
        )
        assert response.status_code == 201
        assert response.json()["mp_status"] == "in_process"
        detalle = client.get(f"/api/v1/pedidos/{pedido['id']}", headers=admin_headers)
        assert detalle.json()["estado_codigo"] == "PENDIENTE"

    def test_pagar_pedido_ajeno_returns_403(
        self, client: TestClient, db_session, client_headers, pedido_factory, mock_mp,
    ):
        from tests.conftest import _create_user
        otro = _create_user(db_session, "otro_pago@test.com", ["CLIENT"])
        pedido = pedido_factory(otro["id"], estado="PENDIENTE")
        response = client.post(
            CREAR_URL, json=_body_pago(pedido["id"]), headers=client_headers,
        )
        assert response.status_code == 403

    def test_pedido_no_pendiente_returns_409(
        self, client: TestClient, client_user, client_headers, pedido_factory, mock_mp,
    ):
        """Solo se paga un pedido en PENDIENTE."""
        pedido = pedido_factory(client_user["id"], estado="CONFIRMADO")
        response = client.post(
            CREAR_URL, json=_body_pago(pedido["id"]), headers=client_headers,
        )
        assert response.status_code == 409

    def test_pedido_inexistente_returns_404(
        self, client: TestClient, client_headers, mock_mp, db_session,
    ):
        response = client.post(
            CREAR_URL, json=_body_pago(99999), headers=client_headers,
        )
        assert response.status_code == 404


# ===========================================================================
# TESTS: POST /pagos/webhook
# ===========================================================================
class TestWebhook:
    """POST /api/v1/pagos/webhook (público, firma validada)"""

    def _crear_pago_pendiente(self, client, client_user, client_headers,
                              pedido_factory, mock_mp) -> dict:
        """Helper: deja un pago in_process registrado y devuelve el pedido."""
        mock_mp["create"] = "in_process"
        pedido = pedido_factory(client_user["id"], estado="PENDIENTE")
        client.post(CREAR_URL, json=_body_pago(pedido["id"]), headers=client_headers)
        return pedido

    def test_webhook_payment_aprobado_confirma_pedido(
        self, client: TestClient, client_user, client_headers,
        admin_headers, pedido_factory, mock_mp,
    ):
        """topic=payment con status approved → pedido CONFIRMADO."""
        pedido = self._crear_pago_pendiente(
            client, client_user, client_headers, pedido_factory, mock_mp,
        )
        # MP "aprueba" el pago: el webhook lo consultará por get()
        mock_mp["payments"][999111]["status"] = "approved"

        response = client.post(WEBHOOK_URL, json={
            "type": "payment", "data": {"id": "999111"},
        })
        assert response.status_code == 200
        detalle = client.get(f"/api/v1/pedidos/{pedido['id']}", headers=admin_headers)
        assert detalle.json()["estado_codigo"] == "CONFIRMADO"

    def test_webhook_topic_distinto_se_ignora(self, client: TestClient, db_session, mock_mp):
        response = client.post(WEBHOOK_URL, json={
            "type": "merchant_order", "data": {"id": "123"},
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_webhook_firma_invalida_returns_401(
        self, client: TestClient, db_session, mock_mp, monkeypatch,
    ):
        """Con secret configurado, una firma incorrecta se rechaza."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "mp_webhook_secret", "secreto-test")
        response = client.post(
            WEBHOOK_URL,
            json={"type": "payment", "data": {"id": "999111"}},
            headers={"x-signature": "ts=1,v1=deadbeef", "x-request-id": "req-1"},
        )
        assert response.status_code == 401

    def test_webhook_firma_valida_se_procesa(
        self, client: TestClient, db_session, mock_mp, monkeypatch,
    ):
        """Firma HMAC correcta → el webhook procesa la notificación."""
        from app.core.config import settings
        secret = "secreto-test"
        monkeypatch.setattr(settings, "mp_webhook_secret", secret)

        ts, data_id, request_id = "1718200000", "999111", "req-1"
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

        response = client.post(
            f"{WEBHOOK_URL}?data.id={data_id}",
            json={"type": "payment", "data": {"id": data_id}},
            headers={"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id},
        )
        # Pasa la firma; como el pago no existe en la BD devuelve not_found
        assert response.status_code == 200
        assert response.json()["status"] in ("not_found", "no_ref", "ok")
