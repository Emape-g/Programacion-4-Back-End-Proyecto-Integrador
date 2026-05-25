from typing import Sequence, Optional, Literal
from sqlmodel import  select, func, asc, desc

from app.core.repository import BaseRepository
from app.modules.forma_de_pago.models import FormaDePago



class FormaDePagoRepository(BaseRepository[FormaDePago]) :

    def __init__(self, session):
        super().__init__(session, FormaDePago)
    
    def get_habilitadas(self) -> Sequence[FormaDePago]:
        return self.session.exec(
            select(FormaDePago).where(FormaDePago.habilitado == True)
        ).all()
    
    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        nombre: Optional[str] = None,
        orden: Literal["asc", "desc"] = "desc",
    ) -> Sequence[FormaDePago]:
        query = select(FormaDePago)
        order_fn = asc if orden == "asc" else desc
        query = query.order_by(order_fn(FormaDePago.codigo))
        return self.session.exec(query.offset(offset).limit(limit)).all()
    
    def count(self, nombre: Optional[str] = None) -> int:
        query = select(func.count(FormaDePago.codigo))
        return self.session.exec(query).one()