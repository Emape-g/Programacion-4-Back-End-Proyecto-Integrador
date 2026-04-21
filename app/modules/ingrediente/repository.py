# app/modules/ingrediente/repository.py
from typing import Sequence, Optional
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    """Repositorio concreto para Ingrediente."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_nombre(self, nombre: str) -> Optional[Ingrediente]:
        """Busca un ingrediente por nombre exacto."""
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.nombre == nombre)
        ).first()

    def get_alergenos(self) -> Sequence[Ingrediente]:
        """Retorna sólo los ingredientes marcados como alérgenos."""
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.es_alergeno == True)
        ).all()

    def count(self) -> int:
        return len(self.session.exec(select(Ingrediente)).all())
