# app/modules/producto/router.py
from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.producto.schemas import (
    ProductoCreate,
    ProductoPublic,
    ProductoUpdate,
    ProductoList,
    ProductoDetalle,
    ProductoCategoriaAdd,
    ProductoIngredienteAdd,
)
from app.modules.producto.service import ProductoService

router = APIRouter()


def get_producto_service(
    session: Session = Depends(get_session),
) -> ProductoService:
    """Factory de dependencia: inyecta el servicio con su Session."""
    return ProductoService(session)


# ── CRUD principal ────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ProductoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto (con categorías e ingredientes opcionales)",
)
def create_producto(
    data: ProductoCreate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    """
    Crea un producto. Acepta listas de categorías e ingredientes iniciales.
    Todas las FKs se validan antes de persistir.
    """
    return svc.create(data)


@router.get(
    "/",
    response_model=ProductoList,
    summary="Listar productos (paginado)",
)
def list_productos(
    offset: Annotated[int, Query(ge=0, description="Registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de resultados")] = 20,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{producto_id}",
    response_model=ProductoDetalle,
    summary="Obtener producto por ID con categorías e ingredientes",
)
def get_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.get_by_id(producto_id)


@router.patch(
    "/{producto_id}",
    response_model=ProductoDetalle,
    summary="Actualización parcial de producto",
)
def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.update(producto_id, data)


@router.delete(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar producto",
)
def delete_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> None:
    svc.delete(producto_id)


# ── Gestión de relaciones N:M ─────────────────────────────────────────────────

@router.post(
    "/{producto_id}/categorias",
    response_model=ProductoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar categoría a producto",
)
def add_categoria(
    producto_id: int,
    data: ProductoCategoriaAdd,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    """Vincula una categoría existente al producto. Rechaza duplicados (409)."""
    return svc.add_categoria(producto_id, data)


@router.delete(
    "/{producto_id}/categorias/{categoria_id}",
    response_model=ProductoDetalle,
    summary="Desasociar categoría de producto",
)
def remove_categoria(
    producto_id: int,
    categoria_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.remove_categoria(producto_id, categoria_id)


@router.post(
    "/{producto_id}/ingredientes",
    response_model=ProductoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar ingrediente a producto",
)
def add_ingrediente(
    producto_id: int,
    data: ProductoIngredienteAdd,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    """Vincula un ingrediente existente al producto. Rechaza duplicados (409)."""
    return svc.add_ingrediente(producto_id, data)


@router.delete(
    "/{producto_id}/ingredientes/{ingrediente_id}",
    response_model=ProductoDetalle,
    summary="Desasociar ingrediente de producto",
)
def remove_ingrediente(
    producto_id: int,
    ingrediente_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.remove_ingrediente(producto_id, ingrediente_id)
