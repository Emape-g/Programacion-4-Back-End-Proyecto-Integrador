# app/modules/producto/repository.py
from typing import Sequence, Optional
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoCategoria, ProductoIngrediente


class ProductoRepository(BaseRepository[Producto]):
    """Repositorio concreto para Producto."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    def get_disponibles(self, offset: int = 0, limit: int = 20) -> Sequence[Producto]:
        """Retorna solo los productos disponibles."""
        return self.session.exec(
            select(Producto)
            .where(Producto.disponible == True)
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self) -> int:
        return len(self.session.exec(select(Producto)).all())


class ProductoCategoriaRepository(BaseRepository[ProductoCategoria]):
    """Repositorio para la tabla pivot ProductoCategoria."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ProductoCategoria)

    def get_by_producto(self, producto_id: int) -> Sequence[ProductoCategoria]:
        """Trae todos los vínculos de un producto con sus categorías."""
        return self.session.exec(
            select(ProductoCategoria).where(
                ProductoCategoria.producto_id == producto_id
            )
        ).all()

    def get_vinculo(
        self, producto_id: int, categoria_id: int
    ) -> Optional[ProductoCategoria]:
        """Busca un vínculo específico producto-categoría."""
        return self.session.exec(
            select(ProductoCategoria).where(
                ProductoCategoria.producto_id == producto_id,
                ProductoCategoria.categoria_id == categoria_id,
            )
        ).first()


class ProductoIngredienteRepository(BaseRepository[ProductoIngrediente]):
    """Repositorio para la tabla pivot ProductoIngrediente."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ProductoIngrediente)

    def get_by_producto(self, producto_id: int) -> Sequence[ProductoIngrediente]:
        """Trae todos los vínculos de un producto con sus ingredientes."""
        return self.session.exec(
            select(ProductoIngrediente).where(
                ProductoIngrediente.producto_id == producto_id
            )
        ).all()

    def get_vinculo(
        self, producto_id: int, ingrediente_id: int
    ) -> Optional[ProductoIngrediente]:
        """Busca un vínculo específico producto-ingrediente."""
        return self.session.exec(
            select(ProductoIngrediente).where(
                ProductoIngrediente.producto_id == producto_id,
                ProductoIngrediente.ingrediente_id == ingrediente_id,
            )
        ).first()
