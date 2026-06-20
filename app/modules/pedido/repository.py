from typing import Sequence
from sqlmodel import Session, select, func

from app.core.repository import BaseRepository
from app.modules.pedido.models import Pedido, HistorialEstadoPedido, Pago


class HistorialEstadoPedidoRepository(BaseRepository[HistorialEstadoPedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, HistorialEstadoPedido)

    def get_by_pedido(self, pedido_id: int) -> Sequence[HistorialEstadoPedido]:
        return self.session.exec(
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido_id)
            .order_by(HistorialEstadoPedido.created_at.asc())
        ).all()


class PagoRepository(BaseRepository[Pago]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pago)

    def get_by_pedido(self, pedido_id: int) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.pedido_id == pedido_id)
        ).first()

    def get_by_mp_payment_id(self, mp_id: int) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.mp_payment_id == mp_id)
        ).first()

    def get_by_mp_merchant_order_id(self, order_id: int) -> Pago | None:
        return self.session.exec(
            select(Pago).where(Pago.mp_merchant_order_id == order_id)
        ).first()

    def get_ultimo_by_pedido(self, pedido_id: int) -> Pago | None:
        return self.session.exec(
            select(Pago)
            .where(Pago.pedido_id == pedido_id)
            .order_by(Pago.created_at.desc())
        ).first()


class PedidoRepository(BaseRepository[Pedido]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Pedido)

    def get_all_active(
        self, offset: int = 0, limit: int = 20
    ) -> Sequence[Pedido]:
        return self.session.exec(
            select(Pedido)
            .where(Pedido.deleted_at.is_(None))
            .order_by(Pedido.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    def count_active(self) -> int:
        return self.session.exec(
            select(func.count(Pedido.id)).where(Pedido.deleted_at.is_(None))
        ).one()

    def get_by_estado(
        self, estado_codigo: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Pedido]:
        return self.session.exec(
            select(Pedido)
            .where(Pedido.estado_codigo == estado_codigo, Pedido.deleted_at.is_(None))
            .order_by(Pedido.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    def count_by_estado(self, estado_codigo: str) -> int:
        return self.session.exec(
            select(func.count(Pedido.id))
            .where(Pedido.estado_codigo == estado_codigo, Pedido.deleted_at.is_(None))
        ).one()

    def get_by_usuario(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[Pedido]:
        return self.session.exec(
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id, Pedido.deleted_at.is_(None))
            .order_by(Pedido.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    def count_by_usuario(self, usuario_id: int) -> int:
        return self.session.exec(
            select(func.count(Pedido.id))
            .where(Pedido.usuario_id == usuario_id, Pedido.deleted_at.is_(None))
        ).one()

    def get_by_usuario_and_estado(
        self, usuario_id: int, estado_codigo: str, offset: int = 0, limit: int = 20
    ) -> Sequence[Pedido]:
        return self.session.exec(
            select(Pedido)
            .where(
                Pedido.usuario_id == usuario_id,
                Pedido.estado_codigo == estado_codigo,
                Pedido.deleted_at.is_(None),
            )
            .order_by(Pedido.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    def count_by_usuario_and_estado(self, usuario_id: int, estado_codigo: str) -> int:
        return self.session.exec(
            select(func.count(Pedido.id))
            .where(
                Pedido.usuario_id == usuario_id,
                Pedido.estado_codigo == estado_codigo,
                Pedido.deleted_at.is_(None),
            )
        ).one()
