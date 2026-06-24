"""
tests/integration/test_websocket.py
===================================

Pruebas de los canales WebSocket (spec sección 9):
  - WS /ws/pedidos/{pedido_id}: cliente dueño en tiempo real.
  - WS /ws/admin/pedidos: feed de todos los pedidos (ADMIN/PEDIDOS).

Autenticación por query param ?token= (spec 9.1).
Close codes: 4001 = token faltante/inválido, 4003 = sin permiso.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

pytestmark = pytest.mark.integration


def _expect_close(ws, code: int):
    """El servidor acepta y cierra: el primer receive lanza Disconnect."""
    with pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_text()
    assert exc.value.code == code


# ===========================================================================
# TESTS: autenticación del handshake
# ===========================================================================
class TestAutenticacionWS:
    """Rechazos del handshake en ambos canales."""

    def test_admin_feed_sin_token_cierra_4001(self, client: TestClient, db_session):
        with client.websocket_connect("/ws/admin/pedidos") as ws:
            _expect_close(ws, 4001)

    def test_admin_feed_token_invalido_cierra_4001(self, client: TestClient, db_session):
        with client.websocket_connect("/ws/admin/pedidos?token=basura") as ws:
            _expect_close(ws, 4001)

    def test_admin_feed_client_sin_rol_cierra_4003(
        self, client: TestClient, client_token, db_session
    ):
        """Un CLIENT no puede suscribirse al feed admin."""
        with client.websocket_connect(f"/ws/admin/pedidos?token={client_token}") as ws:
            _expect_close(ws, 4003)

    def test_pedido_ajeno_cierra_4003(
        self, client: TestClient, db_session, client_token, pedido_factory
    ):
        """Un CLIENT no puede suscribirse al pedido de otro usuario."""
        from tests.conftest import _create_user
        otro = _create_user(db_session, "otro_ws@test.com", ["CLIENT"])
        pedido = pedido_factory(otro["id"])
        with client.websocket_connect(
            f"/ws/pedidos/{pedido['id']}?token={client_token}"
        ) as ws:
            _expect_close(ws, 4003)

    def test_pedido_inexistente_cierra_4003(
        self, client: TestClient, client_token, db_session
    ):
        with client.websocket_connect(f"/ws/pedidos/99999?token={client_token}") as ws:
            _expect_close(ws, 4003)


# ===========================================================================
# TESTS: broadcast en tiempo real (CE-12)
# ===========================================================================
class TestBroadcast:
    """El cambio de estado por REST llega a los suscriptos sin recargar."""

    def test_admin_feed_recibe_cambio_de_estado(
        self, client: TestClient, client_user, admin_token, admin_headers, pedido_factory
    ):
        pedido = pedido_factory(client_user["id"], estado="CONFIRMADO")
        with client.websocket_connect(f"/ws/admin/pedidos?token={admin_token}") as ws:
            resp = client.patch(
                f"/api/v1/pedidos/{pedido['id']}/estado",
                json={"nuevo_estado": "EN_PREP"},
                headers=admin_headers,
            )
            assert resp.status_code == 200

            evento = ws.receive_json()
            assert evento["event"] == "estado_cambiado"
            assert evento["pedido_id"] == pedido["id"]
            assert evento["estado_anterior"] == "CONFIRMADO"
            assert evento["estado_nuevo"] == "EN_PREP"

    def test_cliente_dueno_recibe_evento_de_su_pedido(
        self, client: TestClient, client_user, client_token, admin_headers, pedido_factory
    ):
        pedido = pedido_factory(client_user["id"], estado="CONFIRMADO")
        with client.websocket_connect(
            f"/ws/pedidos/{pedido['id']}?token={client_token}"
        ) as ws:
            client.patch(
                f"/api/v1/pedidos/{pedido['id']}/estado",
                json={"nuevo_estado": "EN_PREP"},
                headers=admin_headers,
            )
            evento = ws.receive_json()
            assert evento["pedido_id"] == pedido["id"]
            assert evento["estado_nuevo"] == "EN_PREP"

    def test_cancelacion_emite_pedido_cancelado(
        self, client: TestClient, client_user, client_token, client_headers, pedido_factory
    ):
        """DELETE /pedidos/{id} (cancelar propio) también notifica por WS."""
        pedido = pedido_factory(client_user["id"], estado="PENDIENTE")
        with client.websocket_connect(
            f"/ws/pedidos/{pedido['id']}?token={client_token}"
        ) as ws:
            client.delete(f"/api/v1/pedidos/{pedido['id']}", headers=client_headers)
            evento = ws.receive_json()
            assert evento["event"] == "pedido_cancelado"
            assert evento["estado_nuevo"] == "CANCELADO"
