from sqlmodel import Session, select

from app.modules.rol.models import Rol
from app.modules.unidad_medida.models import UnidadMedida

ROLES_SEED: list[tuple[str, str, str]] = [
    ("ADMIN", "Administrador", "Acceso total sin restricciones"),
    ("STOCK", "Stockista", "Actualiza stock y disponibilidad"),
    ("PEDIDOS", "Pedidos", "Avanza estados CONFIRMADO→ENTREGADO"),
    ("CLIENT", "Cliente", "Opera solo sus propios datos"),
]


UNIDADES_MEDIDA_SEED: list[tuple[str, str, str]] = [
    ("kilogramo", "kg", "masa"),
    ("gramo", "g", "masa"),
    ("litro", "L", "volumen"),
    ("mililitro", "mL", "volumen"),
    ("pieza", "u", "unidad"),
    ("docena", "doc", "unidad"),
    ("metro cuadrado", "m²", "area"),
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


def seed_unidades_medida(session: Session) -> None:
    changed = False
    for nombre, simbolo, tipo in UNIDADES_MEDIDA_SEED:
        existente = session.exec(
            select(UnidadMedida).where(UnidadMedida.simbolo == simbolo)
        ).first()
        if not existente:
            session.add(UnidadMedida(nombre=nombre, simbolo=simbolo, tipo=tipo))
            changed = True
    if changed:
        session.commit()
