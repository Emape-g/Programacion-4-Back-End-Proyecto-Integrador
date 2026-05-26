from sqlmodel import Session, select

from app.core.security import hash_password
from app.modules.estado_pedido.models import EstadoPedido
from app.modules.forma_de_pago.models import FormaDePago
from app.modules.rol.models import Rol
from app.modules.unidad_medida.models import UnidadMedida
from app.modules.usuario.models import Usuario, UsuarioRol

ROLES_SEED: list[tuple[str, str, str]] = [
    ("ADMIN", "Administrador", "Acceso total sin restricciones"),
    ("STOCK", "Stockista", "Actualiza stock y disponibilidad"),
    ("PEDIDOS", "Pedidos", "Avanza estados CONFIRMADO→ENTREGADO"),
    ("CLIENT", "Cliente", "Opera solo sus propios datos"),
]


UNIDADES_MEDIDA_SEED: list[tuple[str, str, str, float]] = [
    ("kilogramo", "kg", "masa", 1000),
    ("gramo", "g", "masa", 1),
    ("litro", "L", "volumen", 1000),
    ("mililitro", "mL", "volumen", 1),
    ("pieza", "u", "unidad", 1),
    ("docena", "doc", "unidad", 12),
    ("metro cuadrado", "m²", "area", 1),
]


def seed_roles(session: Session) -> None:
    changed = False
    for codigo, nombre, descripcion in ROLES_SEED:
        if not session.get(Rol, codigo):
            session.add(
                Rol(codigo=codigo, nombre=nombre, descripcion=descripcion)
            )
            changed = True
    if changed:
        session.commit()


ADMIN_SEED = {
    "email": "admin@example.com",
    "nombre": "Admin",
    "apellido": "Sistema",
    "password": "admin123",
}


def seed_admin_usuario(session: Session) -> None:
    existente = session.exec(
        select(Usuario).where(Usuario.email == ADMIN_SEED["email"])
    ).first()
    if existente:
        return

    usuario = Usuario(
        email=ADMIN_SEED["email"],
        nombre=ADMIN_SEED["nombre"],
        apellido=ADMIN_SEED["apellido"],
        password_hash=hash_password(ADMIN_SEED["password"]),
    )
    session.add(usuario)
    session.flush()

    session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo="ADMIN"))
    session.commit()


def seed_unidades_medida(session: Session) -> None:
    changed = False
    for nombre, simbolo, tipo, factor_base in UNIDADES_MEDIDA_SEED:
        existente = session.exec(
            select(UnidadMedida).where(UnidadMedida.simbolo == simbolo)
        ).first()
        if existente:
            if float(existente.factor_base) != factor_base:
                existente.factor_base = factor_base
                session.add(existente)
                changed = True
        else:
            session.add(UnidadMedida(
                nombre=nombre, simbolo=simbolo, tipo=tipo, factor_base=factor_base
            ))
            changed = True
    if changed:
        session.commit()


FORMAS_PAGO_SEED: list[tuple[str, str, bool]] = [
    ("MERCADOPAGO",   "Mercado Pago — Checkout API · CardPayment SDK", True),
    ("EFECTIVO",      "Efectivo — retiro en local (direccion_id=NULL)", True),
    ("TRANSFERENCIA", "Transferencia bancaria",                         True),
]


def seed_formas_pago(session: Session) -> None:
    changed = False
    for codigo, descripcion, habilitado in FORMAS_PAGO_SEED:
        if not session.get(FormaDePago, codigo):
            session.add(
                FormaDePago(
                    codigo=codigo,
                    descripcion=descripcion,
                    habilitado=habilitado,
                )
            )
            changed = True
    if changed:
        session.commit()


# (codigo, descripcion, orden, es_terminal) — FSM del Dominio 3
ESTADOS_PEDIDO_SEED: list[tuple[str, str, int, bool]] = [
    ("PENDIENTE",  "Pendiente de confirmación",  1, False),
    ("CONFIRMADO", "Confirmado por el local",    2, False),
    ("EN_PREP",    "En preparación",             3, False),
    ("EN_CAMINO",  "En camino al cliente",       4, False),
    ("ENTREGADO",  "Entregado al cliente",       5, True),
    ("CANCELADO",  "Cancelado",                  6, True),
]


def seed_estados_pedido(session: Session) -> None:
    changed = False
    for codigo, descripcion, orden, es_terminal in ESTADOS_PEDIDO_SEED:
        if not session.get(EstadoPedido, codigo):
            session.add(
                EstadoPedido(
                    codigo=codigo,
                    descripcion=descripcion,
                    orden=orden,
                    es_terminal=es_terminal,
                )
            )
            changed = True
    if changed:
        session.commit()
