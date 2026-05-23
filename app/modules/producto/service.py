# app/modules/producto/service.py
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.producto.models import (
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
)
from app.modules.producto.schemas import (
    ProductoCategoriaAdd,
    ProductoCategoriaPublic,
    ProductoCreate,
    ProductoDetalle,
    ProductoIngredienteAdd,
    ProductoIngredientePublic,
    ProductoList,
    ProductoPublic,
    ProductoUpdate,
)
from app.modules.producto.unit_of_work import ProductoUnitOfWork


class ProductoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:
        p = uow.productos.get_by_id(producto_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con id={producto_id} no encontrado",
            )
        return p

    def _validate_categoria(self, uow: ProductoUnitOfWork, categoria_id: int) -> None:
        if not uow.categorias.get_by_id(categoria_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con id={categoria_id} no encontrada",
            )

    def _validate_ingrediente(
        self, uow: ProductoUnitOfWork, ingrediente_id: int
    ) -> None:
        if not uow.ingredientes.get_by_id(ingrediente_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente con id={ingrediente_id} no encontrado",
            )

    def _validate_unidad(
        self, uow: ProductoUnitOfWork, unidad_id: Optional[int]
    ) -> None:
        if unidad_id is None:
            return
        if not uow.unidades.get_by_id(unidad_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unidad de medida con id={unidad_id} no encontrada",
            )

    def _build_detalle(
        self, uow: ProductoUnitOfWork, producto: Producto
    ) -> ProductoDetalle:
        cats = uow.producto_categorias.get_by_producto(producto.id)
        ings = uow.producto_ingredientes.get_by_producto(producto.id)

        unidad_venta = (
            uow.unidades.get_by_id(producto.unidad_venta_id)
            if producto.unidad_venta_id
            else None
        )

        return ProductoDetalle(
            id=producto.id,
            nombre=producto.nombre,
            descripcion=producto.descripcion,
            precio_base=producto.precio_base,
            unidad_venta_id=producto.unidad_venta_id,
            unidad_venta_simbolo=unidad_venta.simbolo if unidad_venta else None,
            imagenes_url=producto.imagenes_url or [],
            stock_cantidad=producto.stock_cantidad,
            disponible=producto.disponible,
            created_at=producto.created_at,
            updated_at=producto.updated_at,
            categorias=[
                ProductoCategoriaPublic(
                    categoria_id=c.categoria_id,
                    nombre_categoria=uow.categorias.get_by_id(c.categoria_id).nombre,
                    es_principal=c.es_principal,
                )
                for c in cats
            ],
            ingredientes=[
                ProductoIngredientePublic(
                    ingrediente_id=i.ingrediente_id,
                    nombre_ingrediente=uow.ingredientes.get_by_id(
                        i.ingrediente_id
                    ).nombre,
                    cantidad=i.cantidad,
                    unidad_medida_id=i.unidad_medida_id,
                    unidad_simbolo=uow.unidades.get_by_id(
                        i.unidad_medida_id
                    ).simbolo,
                    es_removible=i.es_removible,
                )
                for i in ings
            ],
        )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: ProductoCreate) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            # Validar FKs antes de insertar
            self._validate_unidad(uow, data.unidad_venta_id)
            for cat in data.categorias:
                self._validate_categoria(uow, cat.categoria_id)
            for ing in data.ingredientes:
                self._validate_ingrediente(uow, ing.ingrediente_id)
                self._validate_unidad(uow, ing.unidad_medida_id)

            producto = Producto(
                nombre=data.nombre,
                descripcion=data.descripcion,
                precio_base=data.precio_base,
                unidad_venta_id=data.unidad_venta_id,
                imagenes_url=data.imagenes_url,
                stock_cantidad=data.stock_cantidad,
                disponible=data.disponible,
            )
            uow.productos.add(producto)  # flush → genera producto.id

            for cat in data.categorias:
                link = ProductoCategoria(
                    producto_id=producto.id,
                    categoria_id=cat.categoria_id,
                    es_principal=cat.es_principal,
                )
                uow.producto_categorias.add(link)

            for ing in data.ingredientes:
                link_i = ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=ing.ingrediente_id,
                    cantidad=ing.cantidad,
                    unidad_medida_id=ing.unidad_medida_id,
                    es_removible=ing.es_removible,
                )
                uow.producto_ingredientes.add(link_i)

            result = self._build_detalle(uow, producto)
        return result

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        disponible: Optional[bool] = None,
        nombre: Optional[str] = None,
    ) -> ProductoList:
        with ProductoUnitOfWork(self._session) as uow:
            items = uow.productos.get_all_filtered(
                offset=offset, limit=limit, disponible=disponible, nombre=nombre
            )
            total = uow.productos.count()
            result = ProductoList(
                data=[ProductoPublic.model_validate(p) for p in items],
                total=total,
            )
        return result

    def get_by_id(self, producto_id: int) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            result = self._build_detalle(uow, producto)
        return result

    def update(self, producto_id: int, data: ProductoUpdate) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            if data.unidad_venta_id is not None:
                self._validate_unidad(uow, data.unidad_venta_id)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(producto, field, value)

            producto.updated_at = datetime.now(timezone.utc)
            uow.productos.add(producto)
            result = self._build_detalle(uow, producto)
        return result

    def delete(self, producto_id: int) -> None:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            uow.productos.soft_delete(producto)

    # ── Gestión de relaciones N:M ─────────────────────────────────────────────

    def add_categoria(
        self, producto_id: int, data: ProductoCategoriaAdd
    ) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            self._validate_categoria(uow, data.categoria_id)

            if uow.producto_categorias.get_vinculo(producto_id, data.categoria_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El producto ya tiene asignada esa categoría",
                )

            link = ProductoCategoria(
                producto_id=producto_id,
                categoria_id=data.categoria_id,
                es_principal=data.es_principal,
            )
            uow.producto_categorias.add(link)
            result = self._build_detalle(uow, producto)
        return result

    def remove_categoria(
        self, producto_id: int, categoria_id: int
    ) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            link = uow.producto_categorias.get_vinculo(producto_id, categoria_id)
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="El producto no tiene asignada esa categoría",
                )
            uow.producto_categorias.delete(link)
            result = self._build_detalle(uow, producto)
        return result

    def add_ingrediente(
        self, producto_id: int, data: ProductoIngredienteAdd
    ) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            self._validate_ingrediente(uow, data.ingrediente_id)
            self._validate_unidad(uow, data.unidad_medida_id)

            if uow.producto_ingredientes.get_vinculo(
                producto_id, data.ingrediente_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El producto ya tiene asignado ese ingrediente",
                )

            link = ProductoIngrediente(
                producto_id=producto_id,
                ingrediente_id=data.ingrediente_id,
                cantidad=data.cantidad,
                unidad_medida_id=data.unidad_medida_id,
                es_removible=data.es_removible,
            )
            uow.producto_ingredientes.add(link)
            result = self._build_detalle(uow, producto)
        return result

    def remove_ingrediente(
        self, producto_id: int, ingrediente_id: int
    ) -> ProductoDetalle:
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            link = uow.producto_ingredientes.get_vinculo(producto_id, ingrediente_id)
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="El producto no tiene asignado ese ingrediente",
                )
            uow.producto_ingredientes.delete(link)
            result = self._build_detalle(uow, producto)
        return result
