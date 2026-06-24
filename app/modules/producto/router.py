from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.auth import require_admin, require_role
from app.core.database import get_session
from app.modules.producto.schemas import (
    DisponibilidadUpdate,
    ImagenProductoUpdate,
    ProductoCategoriaAdd,
    ProductoCreate,
    ProductoDetalle,
    ProductoIngredienteAdd,
    ProductoIngredientePublic,
    ProductoList,
    ProductoPublic,
    ProductoUpdate,
)
from app.modules.producto.service import ProductoService

router = APIRouter()


def get_producto_service(
    session: Session = Depends(get_session),
) -> ProductoService:
    return ProductoService(session)


@router.post(
    "/",
    response_model=ProductoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto",
    dependencies=[Depends(require_admin)],
)
def create_producto(
    data: ProductoCreate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.create(data)


@router.get(
    "/",
    response_model=ProductoList,
    summary="Listar productos (público, filtrable)",
)
def list_productos(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    disponible: Annotated[Optional[bool], Query()] = None,
    nombre: Annotated[Optional[str], Query(min_length=1)] = None,
    categoria: Annotated[Optional[int], Query()] = None,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoList:
    return svc.get_all(
        offset=offset, limit=limit,
        disponible=disponible, nombre=nombre,
        categoria_id=categoria,
    )


@router.get(
    "/{producto_id}",
    response_model=ProductoDetalle,
    summary="Detalle con ingredientes, categorías, unidades y stock",
)
def get_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.get_by_id(producto_id)


@router.put(
    "/{producto_id}",
    response_model=ProductoDetalle,
    summary="Actualizar producto",
    dependencies=[Depends(require_admin)],
)
def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.update(producto_id, data)


@router.patch(
    "/{producto_id}/disponibilidad",
    response_model=ProductoDetalle,
    summary="Cambiar disponible (true/false)",
    dependencies=[Depends(require_role("ADMIN", "STOCK"))],
)
def toggle_disponibilidad(
    producto_id: int,
    data: DisponibilidadUpdate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.update(producto_id, ProductoUpdate(disponible=data.disponible))


@router.patch(
    "/{producto_id}/stock",
    response_model=ProductoDetalle,
    summary="Actualizar stock_cantidad (ADMIN/STOCK)",
    dependencies=[Depends(require_role("ADMIN", "STOCK"))],
)
def update_stock(
    producto_id: int,
    data: dict,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    stock = data.get("stock_cantidad")
    if stock is None or not isinstance(stock, int) or stock < 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="stock_cantidad debe ser un entero >= 0")
    return svc.update(producto_id, ProductoUpdate(stock_cantidad=stock))


@router.patch(
    "/{producto_id}/imagenes",
    response_model=ProductoDetalle,
    summary="Actualizar lista imagenes_url[] del producto",
    dependencies=[Depends(require_admin)],
)
def update_imagenes(
    producto_id: int,
    data: ImagenProductoUpdate,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.update(producto_id, ProductoUpdate(imagenes_url=data.imagenes_url))


@router.delete(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete producto",
    dependencies=[Depends(require_admin)],
)
def delete_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> None:
    svc.delete(producto_id)


@router.get(
    "/{producto_id}/ingredientes",
    response_model=List[ProductoIngredientePublic],
    summary="Listar ingredientes del producto (público)",
)
def list_ingredientes(
    producto_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> List[ProductoIngredientePublic]:
    detalle = svc.get_by_id(producto_id)
    return detalle.ingredientes


@router.post(
    "/{producto_id}/ingredientes",
    response_model=ProductoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar ingrediente con cantidad y unidad",
    dependencies=[Depends(require_admin)],
)
def add_ingrediente(
    producto_id: int,
    data: ProductoIngredienteAdd,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.add_ingrediente(producto_id, data)


@router.delete(
    "/{producto_id}/ingredientes/{ingrediente_id}",
    response_model=ProductoDetalle,
    summary="Desasociar ingrediente de producto",
    dependencies=[Depends(require_admin)],
)
def remove_ingrediente(
    producto_id: int,
    ingrediente_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.remove_ingrediente(producto_id, ingrediente_id)


@router.post(
    "/{producto_id}/categorias",
    response_model=ProductoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Asociar categoría a producto",
    dependencies=[Depends(require_admin)],
)
def add_categoria(
    producto_id: int,
    data: ProductoCategoriaAdd,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.add_categoria(producto_id, data)


@router.delete(
    "/{producto_id}/categorias/{categoria_id}",
    response_model=ProductoDetalle,
    summary="Desasociar categoría de producto",
    dependencies=[Depends(require_admin)],
)
def remove_categoria(
    producto_id: int,
    categoria_id: int,
    svc: ProductoService = Depends(get_producto_service),
) -> ProductoDetalle:
    return svc.remove_categoria(producto_id, categoria_id)
