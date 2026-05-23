from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.auth import require_role
from app.core.database import get_session
from app.modules.unidad_medida.schemas import (
    UnidadMedidaCreate,
    UnidadMedidaList,
    UnidadMedidaPublic,
    UnidadMedidaUpdate,
)
from app.modules.unidad_medida.service import UnidadMedidaService

router = APIRouter()


def get_unidad_service(
    session: Session = Depends(get_session),
) -> UnidadMedidaService:
    return UnidadMedidaService(session)


@router.post(
    "/",
    response_model=UnidadMedidaPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear unidad de medida",
    dependencies=[Depends(require_role("ADMIN"))],
)
def create_unidad(
    data: UnidadMedidaCreate,
    svc: UnidadMedidaService = Depends(get_unidad_service),
) -> UnidadMedidaPublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=UnidadMedidaList,
    summary="Listar unidades de medida (paginado, filtrable por tipo)",
)
def list_unidades(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    tipo: Annotated[Optional[str], Query(description="masa | volumen | unidad | area")] = None,
    svc: UnidadMedidaService = Depends(get_unidad_service),
) -> UnidadMedidaList:
    return svc.get_all(offset=offset, limit=limit, tipo=tipo)


@router.get(
    "/{unidad_id}",
    response_model=UnidadMedidaPublic,
    summary="Obtener unidad por id",
)
def get_unidad(
    unidad_id: int,
    svc: UnidadMedidaService = Depends(get_unidad_service),
) -> UnidadMedidaPublic:
    return svc.get_by_id(unidad_id)


@router.patch(
    "/{unidad_id}",
    response_model=UnidadMedidaPublic,
    summary="Actualizar unidad",
    dependencies=[Depends(require_role("ADMIN"))],
)
def update_unidad(
    unidad_id: int,
    data: UnidadMedidaUpdate,
    svc: UnidadMedidaService = Depends(get_unidad_service),
) -> UnidadMedidaPublic:
    return svc.update(unidad_id, data)


@router.delete(
    "/{unidad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar unidad",
    dependencies=[Depends(require_role("ADMIN"))],
)
def delete_unidad(
    unidad_id: int,
    svc: UnidadMedidaService = Depends(get_unidad_service),
) -> None:
    svc.delete(unidad_id)
