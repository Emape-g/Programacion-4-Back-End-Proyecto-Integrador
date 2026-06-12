import pytest
from decimal import Decimal
from tests.conftest import _create_user, _seed_base


def test_crear_pedido_ok(client, client_headers, producto_factory, db_session):
    prod = producto_factory("Pizza", Decimal("200.00"), 10)

    _create_user(db_session, "client_test@test.com", ["CLIENT"])

    resp = client.post("/api/v1/pedidos/", json={
        "items": [{"producto_id": prod.id, "cantidad": 2}],
        "forma_pago_codigo": "EFECTIVO",
    }, headers=client_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado_codigo"] == "PENDIENTE"
    assert Decimal(data["subtotal"]) == Decimal("400.00")


def test_stock_insuficiente(client, client_headers, producto_factory, db_session):
    prod = producto_factory("Empanada", Decimal("50.00"), 2)

    resp = client.post("/api/v1/pedidos/", json={
        "items": [{"producto_id": prod.id, "cantidad": 100}],
        "forma_pago_codigo": "EFECTIVO",
    }, headers=client_headers)
    assert resp.status_code == 400


def test_avanzar_estado_valido(client, admin_headers, pedidos_headers, producto_factory, db_session):
    from tests.conftest import _create_user
    user = _create_user(db_session, "client_avanzar@test.com", ["CLIENT"])
    prod = producto_factory("Milanesa", Decimal("300.00"), 20)

    from app.modules.pedido.models import Pedido
    from app.modules.detalle_pedido.models import DetallePedido
    from app.modules.pedido.models import HistorialEstadoPedido

    _seed_base(db_session)
    pedido = Pedido(
        usuario_id=user.id,
        estado_codigo="CONFIRMADO",
        forma_pago_codigo="EFECTIVO",
        subtotal=Decimal("300.00"),
        total=Decimal("350.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    db_session.refresh(pedido)
    db_session.add(DetallePedido(
        pedido_id=pedido.id, producto_id=prod.id, cantidad=1,
        nombre_snapshot="Milanesa", precio_snapshot=Decimal("300.00"),
        subtotal_snap=Decimal("300.00"),
    ))
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id, estado_desde=None, estado_hacia="CONFIRMADO",
    ))
    db_session.commit()

    resp = client.patch(
        f"/api/v1/pedidos/{pedido.id}/estado",
        json={"nuevo_estado": "EN_PREP"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["estado_codigo"] == "EN_PREP"


def test_avanzar_estado_invalido(client, admin_headers, producto_factory, db_session):
    from tests.conftest import _create_user
    user = _create_user(db_session, "client_inv@test.com", ["CLIENT"])
    prod = producto_factory("Lomo", Decimal("500.00"), 10)

    from app.modules.pedido.models import Pedido
    from app.modules.detalle_pedido.models import DetallePedido
    from app.modules.pedido.models import HistorialEstadoPedido

    pedido = Pedido(
        usuario_id=user.id,
        estado_codigo="ENTREGADO",
        forma_pago_codigo="EFECTIVO",
        subtotal=Decimal("500.00"),
        total=Decimal("550.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    db_session.refresh(pedido)
    db_session.add(DetallePedido(
        pedido_id=pedido.id, producto_id=prod.id, cantidad=1,
        nombre_snapshot="Lomo", precio_snapshot=Decimal("500.00"),
        subtotal_snap=Decimal("500.00"),
    ))
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id, estado_desde=None, estado_hacia="ENTREGADO",
    ))
    db_session.commit()

    resp = client.patch(
        f"/api/v1/pedidos/{pedido.id}/estado",
        json={"nuevo_estado": "EN_PREP"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_cancelar_propio(client, client_headers, producto_factory, db_session):
    from tests.conftest import _create_user
    from sqlmodel import select
    from app.modules.usuario.models import Usuario

    user = db_session.exec(select(Usuario).where(Usuario.email == "client_test@test.com")).first()
    if not user:
        user = _create_user(db_session, "client_test@test.com", ["CLIENT"])

    prod = producto_factory("Ensalada", Decimal("150.00"), 30)

    from app.modules.pedido.models import Pedido
    from app.modules.detalle_pedido.models import DetallePedido
    from app.modules.pedido.models import HistorialEstadoPedido

    pedido = Pedido(
        usuario_id=user.id,
        estado_codigo="PENDIENTE",
        forma_pago_codigo="EFECTIVO",
        subtotal=Decimal("150.00"),
        total=Decimal("200.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    db_session.refresh(pedido)
    db_session.add(DetallePedido(
        pedido_id=pedido.id, producto_id=prod.id, cantidad=1,
        nombre_snapshot="Ensalada", precio_snapshot=Decimal("150.00"),
        subtotal_snap=Decimal("150.00"),
    ))
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id, estado_desde=None, estado_hacia="PENDIENTE",
    ))
    db_session.commit()

    resp = client.delete(f"/api/v1/pedidos/{pedido.id}", headers=client_headers)
    assert resp.status_code == 200
    assert resp.json()["estado_codigo"] == "CANCELADO"


def test_historial_append_only(client, admin_headers, producto_factory, db_session):
    from tests.conftest import _create_user
    user = _create_user(db_session, "client_hist@test.com", ["CLIENT"])
    prod = producto_factory("Papas", Decimal("80.00"), 50)

    from app.modules.pedido.models import Pedido
    from app.modules.detalle_pedido.models import DetallePedido
    from app.modules.pedido.models import HistorialEstadoPedido

    pedido = Pedido(
        usuario_id=user.id,
        estado_codigo="CONFIRMADO",
        forma_pago_codigo="EFECTIVO",
        subtotal=Decimal("80.00"),
        total=Decimal("130.00"),
    )
    db_session.add(pedido)
    db_session.flush()
    db_session.refresh(pedido)
    db_session.add(DetallePedido(
        pedido_id=pedido.id, producto_id=prod.id, cantidad=1,
        nombre_snapshot="Papas", precio_snapshot=Decimal("80.00"),
        subtotal_snap=Decimal("80.00"),
    ))
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id, estado_desde=None, estado_hacia="PENDIENTE",
    ))
    db_session.add(HistorialEstadoPedido(
        pedido_id=pedido.id, estado_desde="PENDIENTE", estado_hacia="CONFIRMADO",
    ))
    db_session.commit()

    client.patch(
        f"/api/v1/pedidos/{pedido.id}/estado",
        json={"nuevo_estado": "EN_PREP"},
        headers=admin_headers,
    )

    resp = client.get(f"/api/v1/pedidos/{pedido.id}/historial", headers=admin_headers)
    assert resp.status_code == 200
    historial = resp.json()
    assert len(historial) >= 3
