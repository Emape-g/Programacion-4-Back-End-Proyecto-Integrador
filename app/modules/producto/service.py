# app/modules/producto/service.py
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.producto.models import Producto, ProductoCategoria, ProductoIngrediente
from app.modules.producto.schemas import (
    ProductoCreate,
    ProductoPublic,
    ProductoUpdate,
    ProductoList,
    ProductoDetalle,
    ProductoCategoriaAdd,
    ProductoCategoriaPublic,
    ProductoIngredienteAdd,
    ProductoIngredientePublic,
)
from app.modules.producto.unit_of_work import ProductoUnitOfWork


class ProductoService:
    """
    Capa de lógica de negocio para Producto.

    Responsabilidades:
    - Validar existencia de Categoria e Ingrediente antes de vincular
    - Evitar vínculos duplicados en las tablas pivot
    - Coordinar múltiples repositorios en una sola transacción via UoW
    - NUNCA acceder directamente a la Session
    """

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

    def _build_detalle(
        self, uow: ProductoUnitOfWork, producto: Producto
    ) -> ProductoDetalle:
        """
        Construye el DTO de detalle leyendo los pivots.
        Debe llamarse DENTRO del bloque `with uow:` para evitar
        que SQLAlchemy expire los atributos tras el commit.
        """
        cats = uow.producto_categorias.get_by_producto(producto.id)
        ings = uow.producto_ingredientes.get_by_producto(producto.id)

        return ProductoDetalle(
            id=producto.id,
            nombre=producto.nombre,
            descripcion=producto.descripcion,
            precio_base=producto.precio_base,
            tiempo_prep_min=producto.tiempo_prep_min,
            disponible=producto.disponible,
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
                    nombre_ingrediente=uow.ingredientes.get_by_id(i.ingrediente_id).nombre,
                    es_removible=i.es_removible,
                    es_opcional=i.es_opcional,
                )
                for i in ings
            ],
        )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: ProductoCreate) -> ProductoDetalle:
        """
        Crea un producto y vincula categorías e ingredientes en una sola transacción.

        Flujo:
        1. Valida todas las categorías e ingredientes referenciados
        2. Persiste el Producto (flush para obtener ID)
        3. Crea los registros pivot ProductoCategoria y ProductoIngrediente
        4. Serializa antes del commit
        """
        with ProductoUnitOfWork(self._session) as uow:
            # Validar FKs antes de insertar
            for cat in data.categorias:
                self._validate_categoria(uow, cat.categoria_id)
            for ing in data.ingredientes:
                self._validate_ingrediente(uow, ing.ingrediente_id)

            # Crear producto (sin las relaciones, solo los campos escalares)
            producto = Producto(
                nombre=data.nombre,
                descripcion=data.descripcion,
                precio_base=data.precio_base,
                tiempo_prep_min=data.tiempo_prep_min,
                disponible=data.disponible,
            )
            uow.productos.add(producto)  # flush interno → genera producto.id

            # Crear vínculos N:M
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
                    es_removible=ing.es_removible,
                    es_opcional=ing.es_opcional,
                )
                uow.producto_ingredientes.add(link_i)

            result = self._build_detalle(uow, producto)
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> ProductoList:
        """Lista paginada de todos los productos."""
        with ProductoUnitOfWork(self._session) as uow:
            items = uow.productos.get_all(offset=offset, limit=limit)
            total = uow.productos.count()
            result = ProductoList(
                data=[ProductoPublic.model_validate(p) for p in items],
                total=total,
            )
        return result

    def get_by_id(self, producto_id: int) -> ProductoDetalle:
        """Retorna el detalle completo de un producto con categorías e ingredientes."""
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            result = self._build_detalle(uow, producto)
        return result

    def update(self, producto_id: int, data: ProductoUpdate) -> ProductoDetalle:
        """Actualización parcial de los campos escalares del producto (PATCH)."""
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(producto, field, value)

            uow.productos.add(producto)
            result = self._build_detalle(uow, producto)
        return result

    def delete(self, producto_id: int) -> None:
        """Elimina el producto (los pivots se eliminan por CASCADE en la DB)."""
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            uow.productos.delete(producto)

    # ── Gestión de relaciones N:M ─────────────────────────────────────────────

    def add_categoria(
        self, producto_id: int, data: ProductoCategoriaAdd
    ) -> ProductoDetalle:
        """Asocia una categoría a un producto. Evita duplicados."""
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

    def remove_categoria(self, producto_id: int, categoria_id: int) -> ProductoDetalle:
        """Desvincula una categoría de un producto."""
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
        """Asocia un ingrediente a un producto. Evita duplicados."""
        with ProductoUnitOfWork(self._session) as uow:
            producto = self._get_or_404(uow, producto_id)
            self._validate_ingrediente(uow, data.ingrediente_id)

            if uow.producto_ingredientes.get_vinculo(producto_id, data.ingrediente_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El producto ya tiene asignado ese ingrediente",
                )

            link = ProductoIngrediente(
                producto_id=producto_id,
                ingrediente_id=data.ingrediente_id,
                es_removible=data.es_removible,
                es_opcional=data.es_opcional,
            )
            uow.producto_ingredientes.add(link)
            result = self._build_detalle(uow, producto)
        return result

    def remove_ingrediente(
        self, producto_id: int, ingrediente_id: int
    ) -> ProductoDetalle:
        """Desvincula un ingrediente de un producto."""
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
