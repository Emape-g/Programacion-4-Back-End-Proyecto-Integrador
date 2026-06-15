"""
tests/integration/test_pedidos.py
=================================

Pruebas de integración del módulo Pedidos. Cubre:
  - POST /pedidos: happy path, stock insuficiente, validaciones, auth.
  - GET /pedidos/{id}: propietario, ajeno (403), ADMIN.
  - PATCH /pedidos/{id}/estado: FSM válida/inválida (RN-01), motivo
    obligatorio al cancelar (RN-05), RBAC.
  - DELETE /pedidos/{id}: cancelar propio, pedido ajeno.
  - GET /pedidos/{id}/historial: append-only (RN-03), permisos.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

PEDIDOS_URL = "/api/v1/pedidos"


# ===========================================================================
# TESTS: POST /pedidos
# ===========================================================================
class TestCrearPedido:
    """POST /api/v1/pedidos"""

    def test_crear_pedido_returns_201_en_pendiente(
        self, client: TestClient, client_headers, producto_factory
    ):
        """Happy path: 201, estado inicial PENDIENTE, subtotal correcto."""
        prod = producto_factory("Pizza", Decimal("200.00"), 10)
        response = client.post(f"{PEDIDOS_URL}/", json={
            "items": [{"producto_id": prod["id"], "cantidad": 2}],
            "forma_pago_codigo": "EFECTIVO",
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "PENDIENTE"
        assert Decimal(data["subtotal"]) == Decimal("400.00")
        # total = subtotal - descuento + costo_envio (spec 3.3)
        assert Decimal(data["total"]) == Decimal("450.00")

    def test_stock_insuficiente_returns_400(
        self, client: TestClient, client_headers, producto_factory
    ):
        """Pedir más unidades que el stock disponible → 400."""
        prod = producto_factory("Empanada", Decimal("50.00"), 2)
        response = client.post(f"{PEDIDOS_URL}/", json={
            "items": [{"producto_id": prod["id"], "cantidad": 100}],
            "forma_pago_codigo": "EFECTIVO",
        }, headers=client_headers)
        assert response.status_code == 400

    def test_sin_items_returns_422(self, client: TestClient, client_headers):
        """CrearPedidoRequest exige mínimo 1 item (spec 6.2)."""
        response = client.post(f"{PEDIDOS_URL}/", json={
            "items": [], "forma_pago_codigo": "EFECTIVO",
        }, headers=client_headers)
        assert response.status_code == 422

    def test_sin_auth_returns_401(self, client: TestClient, db_session):
        """Crear pedido requiere usuario autenticado."""
        response = client.post(f"{PEDIDOS_URL}/", json={
            "items": [{"producto_id": 1, "cantidad": 1}],
            "forma_pago_codigo": "EFECTIVO",
        })
        assert response.status_code == 401


# ===========================================================================
# TESTS: GET /pedidos/{id} — propietario o ADMIN (spec 5.3)
# ===========================================================================
class TestGetPedido:
    """GET /api/v1/pedidos/{id}"""

    def test_propietario_ve_su_pedido(
        self, client: TestClient, client_user, client_headers, pedido_factory
    ):
        pedido = pedido_factory(client_user["id"])
        response = client.get(f"{PEDIDOS_URL}/{pedido['id']}", headers=client_headers)
        assert response.status_code == 200
        assert response.json()["id"] == pedido["id"]

    def test_client_ajeno_returns_403(
        self, client: TestClient, db_session, client_headers, pedido_factory
    ):
        """Un CLIENT no puede ver pedidos de otro usuario."""
        from tests.conftest import _create_user
        otro = _create_user(db_session, "otro@test.com", ["CLIENT"])
        pedido = pedido_factory(otro["id"])
        response = client.get(f"{PEDIDOS_URL}/{pedido['id']}", headers=client_headers)
        assert response.status_code == 403

    def test_admin_ve_cualquier_pedido(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        pedido = pedido_factory(client_user["id"])
        response = client.get(f"{PEDIDOS_URL}/{pedido['id']}", headers=admin_headers)
        assert response.status_code == 200


# ===========================================================================
# TESTS: PATCH /pedidos/{id}/estado — máquina de estados (spec 3.4)
# ===========================================================================
class TestAvanzarEstado:
    """PATCH /api/v1/pedidos/{id}/estado"""

    def test_transicion_valida_returns_200(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        """CONFIRMADO → EN_PREP es válida; actualiza estado e historial."""
        pedido = pedido_factory(client_user["id"], estado="CONFIRMADO")
        response = client.patch(
            f"{PEDIDOS_URL}/{pedido['id']}/estado",
            json={"nuevo_estado": "EN_PREP"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_codigo"] == "EN_PREP"

    def test_transicion_desde_terminal_returns_422(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        """RN-01: un estado terminal (ENTREGADO) no admite transiciones."""
        pedido = pedido_factory(client_user["id"], estado="ENTREGADO")
        response = client.patch(
            f"{PEDIDOS_URL}/{pedido['id']}/estado",
            json={"nuevo_estado": "EN_PREP"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_cancelar_sin_motivo_returns_422(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        """RN-05: motivo obligatorio si nuevo_estado = CANCELADO."""
        pedido = pedido_factory(client_user["id"], estado="PENDIENTE")
        response = client.patch(
            f"{PEDIDOS_URL}/{pedido['id']}/estado",
            json={"nuevo_estado": "CANCELADO"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_client_sin_rol_returns_403(
        self, client: TestClient, client_user, client_headers, pedido_factory
    ):
        """Avanzar estado es solo ADMIN/PEDIDOS (spec 4.2)."""
        pedido = pedido_factory(client_user["id"], estado="CONFIRMADO")
        response = client.patch(
            f"{PEDIDOS_URL}/{pedido['id']}/estado",
            json={"nuevo_estado": "EN_PREP"},
            headers=client_headers,
        )
        assert response.status_code == 403


# ===========================================================================
# TESTS: DELETE /pedidos/{id} — cancelar propio
# ===========================================================================
class TestCancelarPropio:
    """DELETE /api/v1/pedidos/{id}"""

    def test_cancelar_propio_pendiente_returns_200(
        self, client: TestClient, client_user, client_headers, pedido_factory
    ):
        pedido = pedido_factory(client_user["id"], estado="PENDIENTE")
        response = client.delete(f"{PEDIDOS_URL}/{pedido['id']}", headers=client_headers)
        assert response.status_code == 200
        assert response.json()["estado_codigo"] == "CANCELADO"

    def test_cancelar_pedido_ajeno_returns_403(
        self, client: TestClient, db_session, client_headers, pedido_factory
    ):
        from tests.conftest import _create_user
        otro = _create_user(db_session, "otro2@test.com", ["CLIENT"])
        pedido = pedido_factory(otro["id"], estado="PENDIENTE")
        response = client.delete(f"{PEDIDOS_URL}/{pedido['id']}", headers=client_headers)
        assert response.status_code == 403


# ===========================================================================
# TESTS: GET /pedidos/{id}/historial — audit trail append-only (RN-03)
# ===========================================================================
class TestHistorial:
    """GET /api/v1/pedidos/{id}/historial"""

    def test_historial_crece_con_cada_transicion(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        """Tras avanzar el estado, el historial tiene un registro más."""
        pedido = pedido_factory(client_user["id"], estado="CONFIRMADO")

        client.patch(
            f"{PEDIDOS_URL}/{pedido['id']}/estado",
            json={"nuevo_estado": "EN_PREP"},
            headers=admin_headers,
        )

        response = client.get(f"{PEDIDOS_URL}/{pedido['id']}/historial", headers=admin_headers)
        assert response.status_code == 200
        historial = response.json()
        # factory: None→PENDIENTE→CONFIRMADO (2) + transición nueva (1) = 3
        assert len(historial) == 3
        # RN-02: el primer registro siempre arranca con estado_desde = NULL
        assert historial[0]["estado_desde"] is None

    def test_historial_de_pedido_ajeno_returns_403(
        self, client: TestClient, db_session, client_headers, pedido_factory
    ):
        from tests.conftest import _create_user
        otro = _create_user(db_session, "otro3@test.com", ["CLIENT"])
        pedido = pedido_factory(otro["id"])
        response = client.get(f"{PEDIDOS_URL}/{pedido['id']}/historial", headers=client_headers)
        assert response.status_code == 403
