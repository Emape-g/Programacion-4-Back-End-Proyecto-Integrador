from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.modules.detalle_pedido.service import DetallePedidoService
from app.modules.pedido.schemas import DetallePedidoRead

router = APIRouter()


def get_detalle_service(
    session: Session = Depends(get_session),
) -> DetallePedidoService:
    return DetallePedidoService(session)


# ── Endpoints (montados bajo /pedidos) ────────────────────────────────────────

@router.get(
    "/{pedido_id}/detalles",
    response_model=List[DetallePedidoRead],
    summary="Listar ítems de un pedido",
)
def get_detalles(
    pedido_id: int,
    svc: DetallePedidoService = Depends(get_detalle_service),
) -> List[DetallePedidoRead]:
    return svc.get_by_pedido(pedido_id)


@router.get(
    "/{pedido_id}/detalles/{producto_id}",
    response_model=DetallePedidoRead,
    summary="Obtener ítem específico de un pedido",
)
def get_detalle(
    pedido_id: int,
    producto_id: int,
    svc: DetallePedidoService = Depends(get_detalle_service),
) -> DetallePedidoRead:
    return svc.get_item(pedido_id, producto_id)
