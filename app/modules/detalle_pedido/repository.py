from typing import Sequence, Optional
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.detalle_pedido.models import DetallePedido


class DetallePedidoRepository(BaseRepository[DetallePedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, DetallePedido)

    def get_by_pedido(self, pedido_id: int) -> Sequence[DetallePedido]:
        """Retorna todos los ítems de un pedido."""
        return self.session.exec(
            select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        ).all()

    def get_item(self, pedido_id: int, producto_id: int) -> Optional[DetallePedido]:
        """Retorna un ítem específico por PK compuesta."""
        return self.session.exec(
            select(DetallePedido).where(
                DetallePedido.pedido_id == pedido_id,
                DetallePedido.producto_id == producto_id,
            )
        ).first()
