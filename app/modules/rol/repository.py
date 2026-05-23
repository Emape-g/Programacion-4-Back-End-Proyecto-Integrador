from typing import Optional, Sequence

from sqlmodel import Session, func, select

from app.core.repository import BaseRepository
from app.modules.rol.models import Rol


class RolRepository(BaseRepository[Rol]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Rol)

    def get_by_codigo(self, codigo: str) -> Optional[Rol]:
        return self.session.get(Rol, codigo)

    def get_by_nombre(self, nombre: str) -> Optional[Rol]:
        return self.session.exec(select(Rol).where(Rol.nombre == nombre)).first()

    def get_all_paginated(self, offset: int = 0, limit: int = 20) -> Sequence[Rol]:
        return self.session.exec(
            select(Rol).order_by(Rol.codigo).offset(offset).limit(limit)
        ).all()

    def count(self) -> int:
        return self.session.exec(select(func.count(Rol.codigo))).one()
