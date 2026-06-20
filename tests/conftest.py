"""
tests/conftest.py
=================

Fixtures compartidos por toda la suite de tests.

Convención (basada en el ejemplo api_middlewares_testing de la cátedra):
  - `engine`: scope=session, un solo motor SQLite in-memory por suite.
  - `db_session`: scope=function, tablas limpias por test (create/drop).
  - `client`: scope=function, TestClient con dependency_overrides.
  - Fixtures de datos: factories de productos/pedidos y headers por rol.

Adaptaciones para NUESTRO proyecto:
  - El JWT viaja en cookies (no en header Authorization), por eso los
    fixtures *_headers arman el header Cookie a mano.
  - El rate limiter de auth es global y en memoria: se resetea entre
    tests con un fixture autouse.
  - Las factories devuelven dicts (no instancias del ORM) porque el
    UnitOfWork cierra la sesión compartida al procesar cada request y
    las instancias quedarían detached (DetachedInstanceError).

Estrategia de base de datos: SQLite in-memory con StaticPool para
velocidad y para que cualquiera corra los tests sin levantar Postgres.
"""

from contextlib import asynccontextmanager
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import create_access_token
from app.core.database import get_session
from app.core.security import hash_password

# ⚠️ Importar TODOS los modelos antes de create_all para que
# SQLModel.metadata los conozca (mismo patrón que main.py).
from app.modules.categoria.models import Categoria  # noqa: F401
from app.modules.detalle_pedido.models import DetallePedido
from app.modules.estado_pedido.models import EstadoPedido
from app.modules.forma_de_pago.models import FormaDePago
from app.modules.ingrediente.models import Ingrediente  # noqa: F401
from app.modules.pedido.models import HistorialEstadoPedido, Pago, Pedido  # noqa: F401
from app.modules.producto.models import Producto
from app.modules.rol.models import Rol
from app.modules.unidad_medida.models import UnidadMedida
from app.modules.usuario.models import (  # noqa: F401
    DireccionEntrega,
    RefreshToken,
    Usuario,
    UsuarioRol,
)


# ===========================================================================
# 1. ENGINE DE TEST (scope=session — uno por toda la suite)
# ===========================================================================
@pytest.fixture(scope="session")
def engine():
    """SQLite in-memory compartido. StaticPool = una única conexión."""
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield eng
    eng.dispose()


# ===========================================================================
# 2. SESSION DE TEST (scope=function — tablas limpias por test)
# ===========================================================================
@pytest.fixture
def db_session(engine):
    """
    Crea TODAS las tablas, siembra los catálogos base y entrega una
    Session limpia. Al terminar el test, dropea todo: aislamiento total.
    """
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_base(session)
        yield session
        session.rollback()
    SQLModel.metadata.drop_all(engine)


# ===========================================================================
# 3. TESTCLIENT (scope=function — overridea get_session, sin lifespan)
# ===========================================================================
@pytest.fixture
def client(db_session):
    """
    TestClient con la dependency get_session apuntando a la BD de test.
    Se desactiva el lifespan para no ejecutar create_db_and_tables/seed
    contra PostgreSQL real.
    """
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


# ===========================================================================
# 4. RATE LIMITER (autouse — estado limpio entre tests)
# ===========================================================================
@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    """El limiter es un singleton en memoria: sin esto, los intentos
    fallidos de un test bloquearían el login de los siguientes."""
    from app.core.rate_limit import auth_rate_limiter
    auth_rate_limiter._attempts.clear()
    yield
    auth_rate_limiter._attempts.clear()


# ===========================================================================
# 5. SEED BASE — catálogos mínimos (roles, estados, formas de pago, UM)
# ===========================================================================
def _seed_base(session: Session) -> None:
    if not session.get(Rol, "ADMIN"):
        session.add(Rol(codigo="ADMIN", nombre="Administrador", descripcion="Acceso total"))
        session.add(Rol(codigo="CLIENT", nombre="Cliente", descripcion="Cliente"))
        session.add(Rol(codigo="STOCK", nombre="Stockista", descripcion="Stock"))
        session.add(Rol(codigo="PEDIDOS", nombre="Pedidos", descripcion="Pedidos"))

    if not session.get(EstadoPedido, "PENDIENTE"):
        session.add(EstadoPedido(codigo="PENDIENTE", descripcion="Pendiente", orden=1, es_terminal=False))
        session.add(EstadoPedido(codigo="CONFIRMADO", descripcion="Confirmado", orden=2, es_terminal=False))
        session.add(EstadoPedido(codigo="EN_PREP", descripcion="En prep", orden=3, es_terminal=False))
        session.add(EstadoPedido(codigo="ENTREGADO", descripcion="Entregado", orden=4, es_terminal=True))
        session.add(EstadoPedido(codigo="CANCELADO", descripcion="Cancelado", orden=5, es_terminal=True))

    if not session.get(FormaDePago, "MERCADOPAGO"):
        session.add(FormaDePago(codigo="MERCADOPAGO", descripcion="MercadoPago", habilitado=True))
        session.add(FormaDePago(codigo="EFECTIVO", descripcion="Efectivo", habilitado=True))
        session.add(FormaDePago(codigo="TRANSFERENCIA", descripcion="Transferencia", habilitado=True))

    if not session.get(UnidadMedida, 1):
        session.add(UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="peso"))

    session.commit()


# ===========================================================================
# 6. HELPERS DE USUARIOS Y LOGIN
# ===========================================================================
def _create_user(session: Session, email: str, roles: list[str]) -> dict:
    """Crea (o recupera) un usuario con roles. Devuelve dict plano."""
    user = session.exec(select(Usuario).where(Usuario.email == email)).first()
    if not user:
        user = Usuario(
            email=email,
            nombre="Test",
            apellido="User",
            password_hash=hash_password("Test1234!"),
        )
        session.add(user)
        session.flush()
        for rol in roles:
            session.add(UsuarioRol(usuario_id=user.id, rol_codigo=rol))
        session.commit()
    return {"id": user.id, "email": user.email, "roles": roles}


def _login_cookie_header(client: TestClient, email: str) -> dict:
    """Loguea al usuario y devuelve el header Cookie con el access_token."""
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Test1234!"})
    assert resp.status_code == 200, f"login de {email} falló: {resp.text}"
    return {"Cookie": f"access_token={resp.cookies.get('access_token', '')}"}


# ===========================================================================
# 7. FIXTURES DE AUTENTICACIÓN POR ROL (cookies, como usa la app)
# ===========================================================================
@pytest.fixture
def admin_user(db_session) -> dict:
    return _create_user(db_session, "admin_test@test.com", ["ADMIN"])


@pytest.fixture
def client_user(db_session) -> dict:
    return _create_user(db_session, "client_test@test.com", ["CLIENT"])


@pytest.fixture
def admin_headers(client, admin_user) -> dict:
    return _login_cookie_header(client, admin_user["email"])


@pytest.fixture
def client_headers(client, client_user) -> dict:
    return _login_cookie_header(client, client_user["email"])


@pytest.fixture
def pedidos_headers(client, db_session) -> dict:
    _create_user(db_session, "pedidos_test@test.com", ["PEDIDOS"])
    return _login_cookie_header(client, "pedidos_test@test.com")


# Tokens "crudos" para los WebSocket (?token=<jwt> según spec 9.1)
@pytest.fixture
def admin_token(admin_user) -> str:
    return create_access_token(
        sub=admin_user["email"], uid=admin_user["id"], roles=["ADMIN"],
    )


@pytest.fixture
def client_token(client_user) -> str:
    return create_access_token(
        sub=client_user["email"], uid=client_user["id"], roles=["CLIENT"],
    )


# ===========================================================================
# 8. FACTORIES DE DATOS (devuelven dicts — ver docstring del módulo)
# ===========================================================================
@pytest.fixture
def producto_factory(db_session):
    def _factory(
        nombre: str = "Hamburguesa",
        precio: Decimal = Decimal("100.00"),
        stock: int = 50,
    ) -> dict:
        prod = Producto(
            nombre=nombre,
            precio_base=precio,
            stock_cantidad=stock,
            disponible=True,
            imagenes_url=[],
        )
        db_session.add(prod)
        db_session.commit()
        return {"id": prod.id, "nombre": nombre, "precio_base": precio, "stock": stock}
    return _factory


@pytest.fixture
def pedido_factory(db_session, producto_factory):
    """
    Crea un Pedido con un DetallePedido y su historial inicial.
    `estado` define el estado actual; el historial registra la cadena
    de transiciones hasta llegar a él (RN-02: el primero arranca en None).
    """
    def _factory(
        usuario_id: int,
        estado: str = "PENDIENTE",
        precio: Decimal = Decimal("100.00"),
        producto_id: int | None = None,
    ) -> dict:
        if producto_id is None:
            producto_id = producto_factory(f"Prod-{estado}", precio, 50)["id"]

        pedido = Pedido(
            usuario_id=usuario_id,
            estado_codigo=estado,
            forma_pago_codigo="EFECTIVO",
            subtotal=precio,
            total=precio + Decimal("50.00"),
        )
        db_session.add(pedido)
        db_session.flush()

        db_session.add(DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto_id,
            cantidad=1,
            nombre_snapshot=f"Prod-{estado}",
            precio_snapshot=precio,
            subtotal_snap=precio,
        ))

        # Cadena de historial coherente con el estado actual (RN-02).
        cadena = {"PENDIENTE": ["PENDIENTE"],
                  "CONFIRMADO": ["PENDIENTE", "CONFIRMADO"],
                  "EN_PREP": ["PENDIENTE", "CONFIRMADO", "EN_PREP"],
                  "ENTREGADO": ["PENDIENTE", "CONFIRMADO", "EN_PREP", "ENTREGADO"],
                  "CANCELADO": ["PENDIENTE", "CANCELADO"]}[estado]
        desde = None
        for hacia in cadena:
            db_session.add(HistorialEstadoPedido(
                pedido_id=pedido.id, estado_desde=desde, estado_hacia=hacia,
                motivo="test" if hacia == "CANCELADO" else None,
            ))
            desde = hacia

        db_session.commit()
        return {"id": pedido.id, "usuario_id": usuario_id,
                "estado": estado, "producto_id": producto_id,
                "total": precio + Decimal("50.00")}
    return _factory
