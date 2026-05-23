# app/modules/producto/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.categoria.repository import CategoriaRepository
from app.modules.ingrediente.repository import IngredienteRepository
from app.modules.producto.repository import (
    ProductoCategoriaRepository,
    ProductoIngredienteRepository,
    ProductoRepository,
)
from app.modules.unidad_medida.repository import UnidadMedidaRepository


class ProductoUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.producto_categorias = ProductoCategoriaRepository(session)
        self.producto_ingredientes = ProductoIngredienteRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)
        self.unidades = UnidadMedidaRepository(session)
