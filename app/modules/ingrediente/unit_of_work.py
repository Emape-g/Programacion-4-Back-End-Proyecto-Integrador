# app/modules/ingrediente/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.ingrediente.repository import IngredienteRepository
from app.modules.unidad_medida.repository import UnidadMedidaRepository


class IngredienteUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.ingredientes = IngredienteRepository(session)
        self.unidades = UnidadMedidaRepository(session)
