from typing import Sequence
from sqlmodel import Session, select, func

from app.core.repository import BaseRepository
from app.modules.pedido.models import Pedido


class PedidoRepository(BaseRepository[Pedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    def get_all_active(self, offset: int = 0, limit: int = 20) -> Sequence[Pedido]:
        """Pedidos que no fueron eliminados (soft delete)."""
        return self.session.exec(
            select(Pedido)
            .where(Pedido.deleted_at == None)
            .offset(offset)
            .limit(limit)
        ).all()

    def count_active(self) -> int:
        return self.session.exec(
            select(func.count(Pedido.id)).where(Pedido.deleted_at == None)
        ).one()

    def get_by_usuario(self, usuario_id: int) -> Sequence[Pedido]:
        return self.session.exec(
            select(Pedido).where(
                Pedido.usuario_id == usuario_id,
                Pedido.deleted_at == None,
            )
        ).all()
