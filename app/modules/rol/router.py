from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.auth import require_role
from app.core.database import get_session
from app.modules.rol.schemas import RolCreate, RolList, RolPublic, RolUpdate
from app.modules.rol.service import RolService

router = APIRouter()


def get_rol_service(session: Session = Depends(get_session)) -> RolService:
    return RolService(session)


@router.post(
    "/",
    response_model=RolPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear rol",
    dependencies=[Depends(require_role("ADMIN"))],
)
def create_rol(
    data: RolCreate,
    svc: RolService = Depends(get_rol_service),
) -> RolPublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=RolList,
    summary="Listar roles (paginado)",
)
def list_roles(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: RolService = Depends(get_rol_service),
) -> RolList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{codigo}",
    response_model=RolPublic,
    summary="Obtener rol por codigo",
)
def get_rol(codigo: str, svc: RolService = Depends(get_rol_service)) -> RolPublic:
    return svc.get_by_codigo(codigo)


@router.patch(
    "/{codigo}",
    response_model=RolPublic,
    summary="Actualizar rol",
    dependencies=[Depends(require_role("ADMIN"))],
)
def update_rol(
    codigo: str,
    data: RolUpdate,
    svc: RolService = Depends(get_rol_service),
) -> RolPublic:
    return svc.update(codigo, data)


@router.delete(
    "/{codigo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar rol",
    dependencies=[Depends(require_role("ADMIN"))],
)
def delete_rol(codigo: str, svc: RolService = Depends(get_rol_service)) -> None:
    svc.delete(codigo)
