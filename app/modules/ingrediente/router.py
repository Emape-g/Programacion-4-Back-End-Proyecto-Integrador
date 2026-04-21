# app/modules/ingrediente/router.py
from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.ingrediente.schemas import (
    IngredienteCreate,
    IngredientePublic,
    IngredienteUpdate,
    IngredienteList,
)
from app.modules.ingrediente.service import IngredienteService

router = APIRouter()


def get_ingrediente_service(
    session: Session = Depends(get_session),
) -> IngredienteService:
    """Factory de dependencia: inyecta el servicio con su Session."""
    return IngredienteService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=IngredientePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear ingrediente",
)
def create_ingrediente(
    data: IngredienteCreate,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    """Crea un ingrediente nuevo. El nombre debe ser único."""
    return svc.create(data)


@router.get(
    "/",
    response_model=IngredienteList,
    summary="Listar ingredientes (paginado)",
)
def list_ingredientes(
    offset: Annotated[int, Query(ge=0, description="Registros a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de resultados")] = 20,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredienteList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{ingrediente_id}",
    response_model=IngredientePublic,
    summary="Obtener ingrediente por ID",
)
def get_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.get_by_id(ingrediente_id)


@router.patch(
    "/{ingrediente_id}",
    response_model=IngredientePublic,
    summary="Actualización parcial de ingrediente",
)
def update_ingrediente(
    ingrediente_id: int,
    data: IngredienteUpdate,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> IngredientePublic:
    return svc.update(ingrediente_id, data)


@router.delete(
    "/{ingrediente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar ingrediente",
)
def delete_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_ingrediente_service),
) -> None:
    svc.delete(ingrediente_id)
