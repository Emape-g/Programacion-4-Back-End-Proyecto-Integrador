# app/modules/categoria/repository.py
from typing import Sequence, Optional, List
from sqlmodel import Session, select, func

from app.core.repository import BaseRepository
from app.modules.categoria.models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    

    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    def get_by_nombre(self, nombre: str) -> Optional[Categoria]:
        
        return self.session.exec(
            select(Categoria).where(Categoria.nombre == nombre)
        ).first()

    def get_all_paginated(
        self, offset: int = 0, limit: int = 20
    ) -> Sequence[Categoria]:
       
        return self.session.exec(
            select(Categoria)
            .order_by(Categoria.nombre)
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self) -> int:
        
        return self.session.exec(select(func.count(Categoria.id))).one()
