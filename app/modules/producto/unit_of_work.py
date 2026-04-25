# app/modules/producto/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.producto.repository import (
    ProductoRepository,
    ProductoCategoriaRepository,
    ProductoIngredienteRepository,
)
from app.modules.categoria.repository import CategoriaRepository
from app.modules.ingrediente.repository import IngredienteRepository


class ProductoUnitOfWork(UnitOfWork):
    

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.producto_categorias = ProductoCategoriaRepository(session)
        self.producto_ingredientes = ProductoIngredienteRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)
