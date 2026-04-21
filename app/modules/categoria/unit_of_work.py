# app/modules/categoria/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.categoria.repository import CategoriaRepository


class CategoriaUnitOfWork(UnitOfWork):
    """
    UoW específico del módulo Categoria.
    Expone el repositorio necesario para el servicio.

    Uso típico:
        with CategoriaUnitOfWork(session) as uow:
            cat = Categoria(...)
            uow.categorias.add(cat)
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.categorias = CategoriaRepository(session)
