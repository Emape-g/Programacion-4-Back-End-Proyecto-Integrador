# app/modules/ingrediente/repository.py
from datetime import datetime, timezone
from typing import Literal, Sequence, Optional
from sqlmodel import Session, select, func, asc, desc

from app.core.repository import BaseRepository
from app.modules.ingrediente.models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_id(self, record_id: int) -> Optional[Ingrediente]:
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.id == record_id)
        ).first()

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        nombre: Optional[str] = None,
        orden: Literal["asc", "desc"] = "desc",
    ) -> Sequence[Ingrediente]:
        query = select(Ingrediente)
        if nombre:
            query = query.where(Ingrediente.nombre.ilike(f"%{nombre}%"))
        order_fn = asc if orden == "asc" else desc
        query = query.order_by(order_fn(Ingrediente.created_at))
        return self.session.exec(query.offset(offset).limit(limit)).all()

    def get_by_nombre(self, nombre: str) -> Optional[Ingrediente]:
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.nombre == nombre)
        ).first()

    def get_alergenos(self) -> Sequence[Ingrediente]:
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.es_alergeno)
        ).all()

    def count(self, nombre: Optional[str] = None) -> int:
        query = select(func.count(Ingrediente.id))
        if nombre:
            query = query.where(Ingrediente.nombre.ilike(f"%{nombre}%"))
        return self.session.exec(query).one()

    def soft_delete(self, instance: Ingrediente) -> Ingrediente:
        instance.delete_at = datetime.now(timezone.utc)
        self.session.add(instance)
        self.session.flush()
        return instance

    def activate(self, instance: Ingrediente) -> Ingrediente:
        instance.delete_at = None
        self.session.add(instance)
        self.session.flush()
        return instance
