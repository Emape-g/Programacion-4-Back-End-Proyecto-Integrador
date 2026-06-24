from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.auth import decode_token
from app.core.database import get_session
from app.core.ws_manager import ws_manager
from app.modules.pedido.models import Pedido

router = APIRouter()


def _decode_or_none(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        return decode_token(token)
    except Exception:
        return None


@router.websocket("/ws/admin/pedidos")
async def ws_admin_pedidos(websocket: WebSocket, token: str | None = None):
    await websocket.accept()
    payload = _decode_or_none(token)
    if payload is None:
        await websocket.close(code=4001)
        return

    roles = set(payload.get("roles") or [])
    if not roles.intersection({"ADMIN", "PEDIDOS"}):
        await websocket.close(code=4003)
        return

    ws_manager.connect(websocket, "admin")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, "admin")


@router.websocket("/ws/productos")
async def ws_productos(websocket: WebSocket):
    await websocket.accept()
    ws_manager.connect(websocket, "productos")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, "productos")


@router.websocket("/ws/pedidos/{pedido_id}")
async def ws_pedido(
    websocket: WebSocket,
    pedido_id: int,
    token: str | None = None,
    session: Session = Depends(get_session),
):
    await websocket.accept()
    payload = _decode_or_none(token)
    if payload is None:
        await websocket.close(code=4001)
        return

    pedido = session.get(Pedido, pedido_id)
    if not pedido or pedido.deleted_at is not None:
        await websocket.close(code=4003)
        return

    roles = set(payload.get("roles") or [])
    uid = int(payload.get("uid") or 0)
    if not roles.intersection({"ADMIN", "PEDIDOS"}) and pedido.usuario_id != uid:
        await websocket.close(code=4003)
        return

    ws_manager.connect(websocket, pedido_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, pedido_id)
