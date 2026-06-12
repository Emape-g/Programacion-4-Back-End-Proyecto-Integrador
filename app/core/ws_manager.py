import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self) -> None:
        self._pedido_connections: dict[int, set[WebSocket]] = {}
        self._admin_connections: set[WebSocket] = set()

    def connect(self, ws: WebSocket, channel: int | str) -> None:
        if channel == "admin":
            self._admin_connections.add(ws)
        else:
            pedido_id = int(channel)
            self._pedido_connections.setdefault(pedido_id, set()).add(ws)

    def disconnect(self, ws: WebSocket, channel: int | str) -> None:
        if channel == "admin":
            self._admin_connections.discard(ws)
        else:
            pedido_id = int(channel)
            conns = self._pedido_connections.get(pedido_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self._pedido_connections[pedido_id]

    async def broadcast_pedido(self, pedido_id: int, evento: dict[str, Any]) -> None:
        payload = json.dumps(evento, default=str)
        targets = list(self._pedido_connections.get(pedido_id, set())) + list(
            self._admin_connections
        )
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                logger.debug("WS send failed, connection probably closed")

    async def broadcast_to_role(self, role: str, evento: dict[str, Any]) -> None:
        if role == "admin":
            payload = json.dumps(evento, default=str)
            for ws in list(self._admin_connections):
                try:
                    await ws.send_text(payload)
                except Exception:
                    logger.debug("WS send failed")


ws_manager = WSManager()
