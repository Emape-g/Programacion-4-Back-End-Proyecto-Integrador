# app/modules/producto/repository.py
from typing import Sequence, Optional
from sqlmodel import Session, select, func

from app.core.repository import BaseRepository
from app.modules.producto.models import Producto, ProductoCategoria, ProductoIngrediente


class ProductoRepository(BaseRepository[Producto]):
   

    def __init__(self, session: Session) -> None:
        super().__init__(session, Producto)

    def get_disponibles(self, offset: int = 0, limit: int = 20) -> Sequence[Producto]:
        
        return self.session.exec(
            select(Producto)
            .where(Producto.disponible)  
            .offset(offset)
            .limit(limit)
        ).all()

    def count(self) -> int:
        return self.session.exec(select(func.count(Producto.id))).one()
    
    def get_all_filtered(self, offset: int = 0, limit: int = 20,disponible: Optional[bool] = None,nombre: Optional[str] = None,) -> Sequence[Producto]:
        query = select(Producto)
        if disponible is not None:
            query = query.where(Producto.disponible == disponible)
        if nombre:
            query = query.where(Producto.nombre.ilike(f"%{nombre}%"))
        return self.session.exec(query.offset(offset).limit(limit)).all()


class ProductoCategoriaRepository(BaseRepository[ProductoCategoria]):
    

    def __init__(self, session: Session) -> None:
        super().__init__(session, ProductoCategoria)

    def get_by_producto(self, producto_id: int) -> Sequence[ProductoCategoria]:
        
        return self.session.exec(
            select(ProductoCategoria).where(
                ProductoCategoria.producto_id == producto_id
            )
        ).all()

    def get_vinculo(
        self, producto_id: int, categoria_id: int
    ) -> Optional[ProductoCategoria]:
        
        return self.session.exec(
            select(ProductoCategoria).where(
                ProductoCategoria.producto_id == producto_id,
                ProductoCategoria.categoria_id == categoria_id,
            )
        ).first()


class ProductoIngredienteRepository(BaseRepository[ProductoIngrediente]):
    

    def __init__(self, session: Session) -> None:
        super().__init__(session, ProductoIngrediente)

    def get_by_producto(self, producto_id: int) -> Sequence[ProductoIngrediente]:
        
        return self.session.exec(
            select(ProductoIngrediente).where(
                ProductoIngrediente.producto_id == producto_id
            )
        ).all()

    def get_vinculo(
        self, producto_id: int, ingrediente_id: int
    ) -> Optional[ProductoIngrediente]:
        
        return self.session.exec(
            select(ProductoIngrediente).where(
                ProductoIngrediente.producto_id == producto_id,
                ProductoIngrediente.ingrediente_id == ingrediente_id,
            )
        ).first()
