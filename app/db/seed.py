from sqlmodel import Session

from app.modules.rol.models import Rol

ROLES_SEED: list[tuple[str, str, str]] = [
    ("ADMIN", "Administrador", "Acceso total sin restricciones"),
    ("STOCK", "Stockista", "Actualiza stock y disponibilidad"),
    ("PEDIDOS", "Pedidos", "Avanza estados CONFIRMADO→ENTREGADO"),
    ("CLIENT", "Cliente", "Opera solo sus propios datos"),
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
