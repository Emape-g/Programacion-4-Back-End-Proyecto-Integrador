"""
tests/integration/test_estadisticas.py
======================================

Pruebas de integración del módulo Estadísticas (solo ADMIN). Cubre:
  - GET /estadisticas/resumen: schema de KPIs.
  - GET /estadisticas/pedidos-por-estado: agrupación.
  - GET /estadisticas/productos-top.
  - EST-01: pedidos CANCELADOS nunca suman en los ingresos.
  - RBAC: CLIENT → 403.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

EST_URL = "/api/v1/estadisticas"


# ===========================================================================
# TESTS: GET /estadisticas/resumen
# ===========================================================================
class TestResumen:
    """GET /api/v1/estadisticas/resumen"""

    def test_resumen_devuelve_kpis(self, client: TestClient, admin_headers):
        response = client.get(f"{EST_URL}/resumen", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ventas_hoy" in data
        assert "ticket_promedio" in data
        assert "pedidos_activos" in data
        assert "ventas_mes" in data

    def test_cancelado_no_suma_en_ingresos(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        """EST-01: con un único pedido CANCELADO, las ventas dan 0."""
        pedido_factory(client_user["id"], estado="CANCELADO", precio=Decimal("1000.00"))
        response = client.get(f"{EST_URL}/resumen", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["ventas_hoy"])) == Decimal("0.00")
        assert Decimal(str(data["ventas_mes"])) == Decimal("0.00")

    def test_confirmado_si_suma(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        """Control: un pedido CONFIRMADO sí aparece en ventas."""
        pedido_factory(client_user["id"], estado="CONFIRMADO", precio=Decimal("100.00"))
        response = client.get(f"{EST_URL}/resumen", headers=admin_headers)
        data = response.json()
        # total del pedido = 100 + 50 de envío
        assert Decimal(str(data["ventas_hoy"])) == Decimal("150.00")


# ===========================================================================
# TESTS: GET /estadisticas/pedidos-por-estado
# ===========================================================================
class TestPedidosPorEstado:
    """GET /api/v1/estadisticas/pedidos-por-estado"""

    def test_agrupa_por_estado(
        self, client: TestClient, client_user, admin_headers, pedido_factory
    ):
        for estado in ["PENDIENTE", "CONFIRMADO", "CANCELADO"]:
            pedido_factory(client_user["id"], estado=estado)
        response = client.get(f"{EST_URL}/pedidos-por-estado", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        estados = {item["estado_codigo"] for item in data}
        assert {"PENDIENTE", "CONFIRMADO", "CANCELADO"} <= estados


# ===========================================================================
# TESTS: GET /estadisticas/productos-top
# ===========================================================================
class TestProductosTop:
    """GET /api/v1/estadisticas/productos-top"""

    def test_returns_200(self, client: TestClient, admin_headers):
        response = client.get(f"{EST_URL}/productos-top", headers=admin_headers)
        assert response.status_code == 200


# ===========================================================================
# TESTS: RBAC — estadísticas es exclusivo de ADMIN (spec sección 11)
# ===========================================================================
class TestPermisos:
    """Un CLIENT no accede a las estadísticas."""

    def test_client_returns_403(self, client: TestClient, client_headers):
        response = client.get(f"{EST_URL}/resumen", headers=client_headers)
        assert response.status_code == 403
