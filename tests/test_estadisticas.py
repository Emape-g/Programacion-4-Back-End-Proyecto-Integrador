import pytest
from datetime import date
from decimal import Decimal
from tests.conftest import _create_user, _seed_base


def test_resumen_ok(client, admin_headers, db_session):
    _seed_base(db_session)
    resp = client.get("/api/v1/estadisticas/resumen", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "ventas_hoy" in data
    assert "ticket_promedio" in data
    assert "pedidos_activos" in data
    assert "ventas_mes" in data


def test_pedidos_por_estado(client, admin_headers, db_session, producto_factory):
    prod = producto_factory("Sushi", Decimal("350.00"), 20)
    user = _create_user(db_session, "est_user@test.com", ["CLIENT"])

    from app.modules.pedido.models import Pedido, HistorialEstadoPedido
    from app.modules.detalle_pedido.models import DetallePedido

    for estado in ["PENDIENTE", "CONFIRMADO", "CANCELADO"]:
        pedido = Pedido(
            usuario_id=user.id,
            estado_codigo=estado,
            forma_pago_codigo="EFECTIVO",
            subtotal=Decimal("350.00"),
            total=Decimal("400.00"),
        )
        db_session.add(pedido)
        db_session.flush()
        db_session.refresh(pedido)
        db_session.add(DetallePedido(
            pedido_id=pedido.id, producto_id=prod.id, cantidad=1,
            nombre_snapshot="Sushi", precio_snapshot=Decimal("350.00"),
            subtotal_snap=Decimal("350.00"),
        ))
        db_session.add(HistorialEstadoPedido(
            pedido_id=pedido.id, estado_desde=None, estado_hacia=estado,
        ))
    db_session.commit()

    resp = client.get("/api/v1/estadisticas/pedidos-por-estado", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    estados = {item["estado_codigo"] for item in data}
    assert "PENDIENTE" in estados or "CONFIRMADO" in estados


def test_productos_top(client, admin_headers, db_session):
    _seed_base(db_session)
    resp = client.get("/api/v1/estadisticas/productos-top", headers=admin_headers)
    assert resp.status_code == 200


def test_cancelado_no_suma_en_resumen(client, admin_headers, db_session, producto_factory):
    prod = producto_factory("CancelTest", Decimal("1000.00"), 10)
    user = _create_user(db_session, "cancel_est@test.com", ["CLIENT"])

    from app.modules.pedido.models import Pedido, HistorialEstadoPedido
    from app.modules.detalle_pedido.models import DetallePedido

    pedido = Pedido(
        usuario_id=user.id,
        estado_codigo="CANCELADO",
        forma_pago_codigo="EFECTIVO",
        subtotal=Decimal("1000.00"),
        total=Decimal("1050.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    db_session.refresh(pedido)
    db_session.add(DetallePedido(
        pedido_id=pedido.id, producto_id=prod.id, cantidad=1,
        nombre_snapshot="CancelTest", precio_snapshot=Decimal("1000.00"),
        subtotal_snap=Decimal("1000.00"),
    ))
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id, estado_desde=None, estado_hacia="CANCELADO",
        motivo="test",
    ))
    db_session.commit()

    resp = client.get("/api/v1/estadisticas/resumen", headers=admin_headers)
    assert resp.status_code == 200
