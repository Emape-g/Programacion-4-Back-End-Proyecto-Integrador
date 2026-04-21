# app/modules/categoria/repository.py
from typing import Sequence, Optional
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.categoria.models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    """
    Repositorio concreto para Categoria.
    Extiende BaseRepository con queries específicas del dominio.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    def get_by_nombre(self, nombre: str) -> Optional[Categoria]:
        """Busca una categoría por nombre exacto (case-sensitive)."""
        return self.session.exec(
            select(Categoria).where(Categoria.nombre == nombre)
        ).first()

    def get_all_paginated(
        self, offset: int = 0, limit: int = 20
    ) -> Sequence[Categoria]:
        """Lista categorías ordenadas por orden_display."""
        return self.session.exec(
            select(Categoria)
            .order_by(Categoria.orden_display)
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self) -> int:
        """Cuenta el total de categorías."""
        return len(self.session.exec(select(Categoria)).all())
