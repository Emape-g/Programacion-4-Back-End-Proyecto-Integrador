# app/modules/ingrediente/repository.py
from typing import Sequence, Optional
from sqlmodel import Session, select, func

from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_nombre(self, nombre: str) -> Optional[Ingrediente]:
        
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.nombre == nombre)
        ).first()

    def get_alergenos(self) -> Sequence[Ingrediente]:
        return self.session.exec(
            
            select(Ingrediente).where(Ingrediente.es_alergeno)
        ).all()

    def count(self) -> int:
        return self.session.exec(select(func.count(Ingrediente.id))).one()
