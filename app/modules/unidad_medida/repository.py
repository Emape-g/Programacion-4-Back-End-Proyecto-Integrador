from typing import Optional, Sequence

from sqlmodel import Session, func, select

from app.core.repository import BaseRepository
from app.modules.unidad_medida.models import UnidadMedida


class UnidadMedidaRepository(BaseRepository[UnidadMedida]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, UnidadMedida)

    def get_by_nombre(self, nombre: str) -> Optional[UnidadMedida]:
        return self.session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == nombre)
        ).first()

    def get_by_simbolo(self, simbolo: str) -> Optional[UnidadMedida]:
        return self.session.exec(
            select(UnidadMedida).where(UnidadMedida.simbolo == simbolo)
        ).first()

    def list_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        tipo: Optional[str] = None,
    ) -> Sequence[UnidadMedida]:
        stmt = select(UnidadMedida)
        if tipo:
            stmt = stmt.where(UnidadMedida.tipo == tipo)
        return self.session.exec(
            stmt.order_by(UnidadMedida.tipo, UnidadMedida.nombre)
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self, tipo: Optional[str] = None) -> int:
        stmt = select(func.count(UnidadMedida.id))
        if tipo:
            stmt = stmt.where(UnidadMedida.tipo == tipo)
        return self.session.exec(stmt).one()
