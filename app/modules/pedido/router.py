from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.auth import get_current_user, require_role
from app.core.database import get_session
from app.modules.pedido.schemas import (
    AvanzarEstadoRequest,
    CrearPedidoRequest,
    HistorialRead,
    PedidoDetail,
    PedidoList,
    PedidoRead,
)
from app.modules.pedido.service import PedidoService

router = APIRouter()


def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


@router.post(
    "/",
    response_model=PedidoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido desde carrito",
)
async def create_pedido(
    data: CrearPedidoRequest,
    payload: dict = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    usuario_id = int(payload["uid"])
    return await svc.create(data, usuario_id)


@router.get(
    "/",
    response_model=PedidoList,
    summary="Listar pedidos propios (CLIENT) o todos (ADMIN/PEDIDOS)",
)
def list_pedidos(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    estado: Annotated[str | None, Query()] = None,
    payload: dict = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoList:
    roles = set(payload.get("roles") or [])
    offset = (page - 1) * size

    if roles.intersection({"ADMIN", "PEDIDOS"}):
        return svc.get_all(offset=offset, limit=size, estado=estado)
    else:
        return svc.get_all(
            offset=offset, limit=size,
            usuario_id=int(payload["uid"]), estado=estado,
        )


@router.get(
    "/{pedido_id}",
    response_model=PedidoDetail,
    summary="Detalle completo con líneas, trazabilidad y pago",
)
def get_pedido(
    pedido_id: int,
    payload: dict = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoDetail:
    detail = svc.get_by_id(pedido_id)
    roles = set(payload.get("roles") or [])
    if not roles.intersection({"ADMIN", "PEDIDOS"}):
        usuario_id = int(payload["uid"])
        if detail.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes ver tus propios pedidos",
            )
    return detail


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoRead,
    summary="Avanzar estado (FSM). ADMIN/PEDIDOS.",
)
async def avanzar_estado(
    pedido_id: int,
    data: AvanzarEstadoRequest,
    payload: dict = Depends(require_role("ADMIN", "PEDIDOS")),
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    usuario_id = int(payload["uid"])
    return await svc.avanzar_estado(pedido_id, data, usuario_id)


@router.get(
    "/{pedido_id}/historial",
    response_model=List[HistorialRead],
    summary="Historial completo del pedido, ORDER BY created_at ASC",
)
def get_historial(
    pedido_id: int,
    payload: dict = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
) -> List[HistorialRead]:
    roles = set(payload.get("roles") or [])
    if not roles.intersection({"ADMIN", "PEDIDOS"}):
        detail = svc.get_by_id(pedido_id)
        if detail.usuario_id != int(payload["uid"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes ver el historial de tus propios pedidos",
            )
    return svc.get_historial(pedido_id)


@router.delete(
    "/{pedido_id}",
    response_model=PedidoRead,
    summary="Cancelar propio pedido (solo PENDIENTE o CONFIRMADO)",
)
async def cancelar_pedido(
    pedido_id: int,
    payload: dict = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoRead:
    usuario_id = int(payload["uid"])
    return await svc.cancelar_propio(pedido_id, usuario_id)


