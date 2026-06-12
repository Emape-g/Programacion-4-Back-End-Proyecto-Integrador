import pytest
from contextlib import asynccontextmanager
from decimal import Decimal
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.core.security import hash_password
from app.modules.categoria.models import Categoria
from app.modules.detalle_pedido.models import DetallePedido
from app.modules.estado_pedido.models import EstadoPedido
from app.modules.forma_de_pago.models import FormaDePago
from app.modules.ingrediente.models import Ingrediente
from app.modules.pedido.models import HistorialEstadoPedido, Pago, Pedido
from app.modules.producto.models import Producto, ProductoCategoria, ProductoIngrediente
from app.modules.rol.models import Rol
from app.modules.unidad_medida.models import UnidadMedida
from app.modules.usuario.models import DireccionEntrega, RefreshToken, Usuario, UsuarioRol


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    from app.core.rate_limit import auth_rate_limiter
    auth_rate_limiter._attempts.clear()
    yield
    auth_rate_limiter._attempts.clear()


@pytest.fixture
def db_session(engine):
    with Session(engine) as session:
        _seed_base(session)
        yield session
        session.rollback()


@pytest.fixture
def client(db_session):
    def _override():
        yield db_session

    from main import app

    @asynccontextmanager
    async def _no_lifespan(app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _no_lifespan

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


def _seed_base(session: Session) -> None:
    if not session.get(Rol, "ADMIN"):
        session.add(Rol(codigo="ADMIN", nombre="Administrador", descripcion="Acceso total"))
        session.add(Rol(codigo="CLIENT", nombre="Cliente", descripcion="Cliente"))
        session.add(Rol(codigo="STOCK", nombre="Stockista", descripcion="Stock"))
        session.add(Rol(codigo="PEDIDOS", nombre="Pedidos", descripcion="Pedidos"))
        session.flush()

    if not session.get(EstadoPedido, "PENDIENTE"):
        session.add(EstadoPedido(codigo="PENDIENTE", descripcion="Pendiente", orden=1, es_terminal=False))
        session.add(EstadoPedido(codigo="CONFIRMADO", descripcion="Confirmado", orden=2, es_terminal=False))
        session.add(EstadoPedido(codigo="EN_PREP", descripcion="En prep", orden=3, es_terminal=False))
        session.add(EstadoPedido(codigo="ENTREGADO", descripcion="Entregado", orden=4, es_terminal=True))
        session.add(EstadoPedido(codigo="CANCELADO", descripcion="Cancelado", orden=5, es_terminal=True))
        session.flush()

    if not session.get(FormaDePago, "MERCADOPAGO"):
        session.add(FormaDePago(codigo="MERCADOPAGO", descripcion="MercadoPago", habilitado=True))
        session.add(FormaDePago(codigo="EFECTIVO", descripcion="Efectivo", habilitado=True))
        session.add(FormaDePago(codigo="TRANSFERENCIA", descripcion="Transferencia", habilitado=True))
        session.flush()

    existing_um = session.get(UnidadMedida, 1)
    if not existing_um:
        session.add(UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="peso"))
        session.flush()

    session.commit()


def _create_user(session: Session, email: str, roles: list[str]) -> Usuario:
    _seed_base(session)
    user = session.exec(
        __import__("sqlmodel", fromlist=["select"]).select(Usuario).where(Usuario.email == email)
    ).first()
    if user:
        return user

    user = Usuario(
        email=email,
        nombre="Test",
        apellido="User",
        password_hash=hash_password("Test1234!"),
    )
    session.add(user)
    session.flush()
    session.refresh(user)

    for rol in roles:
        session.add(UsuarioRol(usuario_id=user.id, rol_codigo=rol))
    session.flush()
    session.commit()
    return user


def _login_user(client: TestClient, email: str, password: str = "Test1234!") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.cookies


@pytest.fixture
def admin_headers(client, db_session):
    user = _create_user(db_session, "admin_test@test.com", ["ADMIN"])
    cookies = _login_user(client, "admin_test@test.com")
    return {"Cookie": f"access_token={cookies.get('access_token', '')}"}


@pytest.fixture
def client_headers(client, db_session):
    user = _create_user(db_session, "client_test@test.com", ["CLIENT"])
    cookies = _login_user(client, "client_test@test.com")
    return {"Cookie": f"access_token={cookies.get('access_token', '')}"}


@pytest.fixture
def pedidos_headers(client, db_session):
    user = _create_user(db_session, "pedidos_test@test.com", ["PEDIDOS"])
    cookies = _login_user(client, "pedidos_test@test.com")
    return {"Cookie": f"access_token={cookies.get('access_token', '')}"}


@pytest.fixture
def producto_factory(db_session):
    def _factory(nombre: str = "Hamburguesa", precio: Decimal = Decimal("100.00"), stock: int = 50):
        _seed_base(db_session)
        prod = Producto(
            nombre=nombre,
            precio_base=precio,
            stock_cantidad=stock,
            disponible=True,
            imagenes_url=[],
        )
        db_session.add(prod)
        db_session.flush()
        db_session.refresh(prod)
        db_session.commit()
        return prod
    return _factory


@pytest.fixture
def pedido_factory(db_session):
    def _factory(usuario_id: int, producto_id: int):
        _seed_base(db_session)
        prod = db_session.get(Producto, producto_id)
        pedido = Pedido(
            usuario_id=usuario_id,
            estado_codigo="PENDIENTE",
            forma_pago_codigo="EFECTIVO",
            subtotal=prod.precio_base,
            total=prod.precio_base + Decimal("50.00"),
        )
        db_session.add(pedido)
        db_session.flush()
        db_session.refresh(pedido)

        detalle = DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto_id,
            cantidad=1,
            nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_base,
            subtotal_snap=prod.precio_base,
        )
        db_session.add(detalle)

        historial = HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_desde=None,
            estado_hacia="PENDIENTE",
            usuario_id=usuario_id,
        )
        db_session.add(historial)
        db_session.flush()
        db_session.commit()
        return pedido
    return _factory
