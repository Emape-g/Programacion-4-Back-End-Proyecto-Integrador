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
    """
    UoW específico del módulo Producto.

    Expone cinco repositorios que comparten la misma sesión (misma transacción):
      - productos:             operaciones sobre Producto
      - producto_categorias:   pivot N:M producto ↔ categoría
      - producto_ingredientes: pivot N:M producto ↔ ingrediente
      - categorias:            para validar existencia de Categoria
      - ingredientes:          para validar existencia de Ingrediente

    Uso típico:
        with ProductoUnitOfWork(session) as uow:
            producto = Producto(...)
            uow.productos.add(producto)
            link = ProductoCategoria(producto_id=producto.id, categoria_id=1)
            uow.producto_categorias.add(link)
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.producto_categorias = ProductoCategoriaRepository(session)
        self.producto_ingredientes = ProductoIngredienteRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)
