from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.pedido.schemas import (
    PedidoCreate,
    PedidoDetalle,
    PedidoList,
    CambiarEstadoRequest,
)
from app.modules.pedido.service import PedidoService

router = APIRouter()


def get_pedido_service(
    session: Session = Depends(get_session),
) -> PedidoService:
    return PedidoService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PedidoDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido con sus ítems",
)
def create_pedido(
    data: PedidoCreate,
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoDetalle:
    """
    Crea la cabecera del pedido y todos sus detalles en una sola transacción.
    El servidor calcula subtotal, costo de envío y total. Estado inicial: PENDIENTE.
    """
    return svc.create(data)


@router.get(
    "/",
    response_model=PedidoList,
    summary="Listar pedidos (paginado)",
)
def list_pedidos(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/{pedido_id}",
    response_model=PedidoDetalle,
    summary="Obtener pedido por ID con sus ítems",
)
def get_pedido(
    pedido_id: int,
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoDetalle:
    return svc.get_by_id(pedido_id)


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoDetalle,
    summary="Cambiar estado del pedido (FSM)",
)
def cambiar_estado(
    pedido_id: int,
    data: CambiarEstadoRequest,
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoDetalle:
    """
    Avanza el estado según el FSM. Transiciones válidas:
    PENDIENTE → CONFIRMADO | CANCELADO
    CONFIRMADO → EN_PREP | CANCELADO
    EN_PREP → EN_CAMINO | CANCELADO
    EN_CAMINO → ENTREGADO
    El campo 'motivo' es obligatorio al cancelar.
    """
    return svc.cambiar_estado(pedido_id, data)


@router.delete(
    "/{pedido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar pedido (soft delete)",
)
def delete_pedido(
    pedido_id: int,
    svc: PedidoService = Depends(get_pedido_service),
) -> None:
    svc.delete(pedido_id)
