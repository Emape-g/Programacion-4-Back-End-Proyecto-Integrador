from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.estado_pedido.schemas import (
    EstadoPedidoCreate,
    EstadoPedidoUpdate,
    EstadoPedidoPublic,
)
from app.modules.estado_pedido.service import EstadoPedidoService

router = APIRouter()


def get_estado_pedido_service(
    session: Session = Depends(get_session),
) -> EstadoPedidoService:
    return EstadoPedidoService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=EstadoPedidoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear estado de pedido (admin)",
)
def create_estado(
    data: EstadoPedidoCreate,
    svc: EstadoPedidoService = Depends(get_estado_pedido_service),
) -> EstadoPedidoPublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=List[EstadoPedidoPublic],
    summary="Listar estados de pedido ordenados por FSM",
)
def list_estados(
    svc: EstadoPedidoService = Depends(get_estado_pedido_service),
) -> List[EstadoPedidoPublic]:
    return svc.get_all()


@router.get(
    "/{codigo}",
    response_model=EstadoPedidoPublic,
    summary="Obtener estado por código",
)
def get_estado(
    codigo: str,
    svc: EstadoPedidoService = Depends(get_estado_pedido_service),
) -> EstadoPedidoPublic:
    return svc.get_by_codigo(codigo)


@router.patch(
    "/{codigo}",
    response_model=EstadoPedidoPublic,
    summary="Actualizar estado de pedido (admin)",
)
def update_estado(
    codigo: str,
    data: EstadoPedidoUpdate,
    svc: EstadoPedidoService = Depends(get_estado_pedido_service),
) -> EstadoPedidoPublic:
    return svc.update(codigo, data)
