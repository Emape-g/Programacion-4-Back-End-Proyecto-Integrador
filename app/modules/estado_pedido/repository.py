from typing import Sequence
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.estado_pedido.models import EstadoPedido


class EstadoPedidoRepository(BaseRepository[EstadoPedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, EstadoPedido)

    def get_all_ordered(self) -> Sequence[EstadoPedido]:
        """Devuelve todos los estados ordenados por su posición en el FSM."""
        return self.session.exec(
            select(EstadoPedido).order_by(EstadoPedido.orden)
        ).all()

    def get_no_terminales(self) -> Sequence[EstadoPedido]:
        """Devuelve solo los estados desde los que aún se puede transicionar."""
        return self.session.exec(
            select(EstadoPedido)
            .where(EstadoPedido.es_terminal == False)
            .order_by(EstadoPedido.orden)
        ).all()
