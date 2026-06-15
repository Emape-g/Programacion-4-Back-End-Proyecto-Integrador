from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import Date, case, func
from sqlmodel import Session, select

from app.modules.detalle_pedido.models import DetallePedido
from app.modules.pedido.models import Pago, Pedido


class EstadisticasRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_ventas_periodo(
        self, desde: date, hasta: date, agrupacion: str = "day"
    ) -> list[dict]:
        trunc = func.date_trunc(agrupacion, Pedido.created_at)
        stmt = (
            select(
                trunc.label("periodo"),
                func.coalesce(func.sum(Pedido.total), 0).label("total_ventas"),
                func.count(Pedido.id).label("cantidad_pedidos"),
            )
            .where(
                Pedido.estado_codigo != "CANCELADO",
                Pedido.deleted_at.is_(None),
                func.cast(Pedido.created_at, Date).between(desde, hasta),
            )
            .group_by(trunc)
            .order_by(trunc)
        )
        rows = self.session.exec(stmt).all()
        return [
            {
                "periodo": str(r[0].date() if hasattr(r[0], "date") else r[0]),
                "total_ventas": Decimal(str(r[1])),
                "cantidad_pedidos": r[2],
            }
            for r in rows
        ]

    def get_productos_top(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(
                DetallePedido.nombre_snapshot.label("nombre"),
                func.coalesce(func.sum(DetallePedido.subtotal_snap), 0).label("ingresos"),
                func.coalesce(func.sum(DetallePedido.cantidad), 0).label("cantidad_vendida"),
            )
            .join(Pedido, Pedido.id == DetallePedido.pedido_id)
            .where(
                Pedido.estado_codigo != "CANCELADO",
                Pedido.deleted_at.is_(None),
            )
            .group_by(DetallePedido.nombre_snapshot)
            .order_by(func.sum(DetallePedido.subtotal_snap).desc())
            .limit(limit)
        )
        rows = self.session.exec(stmt).all()
        return [
            {
                "nombre": r[0],
                "ingresos": Decimal(str(r[1])),
                "cantidad_vendida": r[2],
            }
            for r in rows
        ]

    def get_pedidos_por_estado(self) -> list[dict]:
        stmt = (
            select(
                Pedido.estado_codigo,
                func.count(Pedido.id).label("cantidad"),
            )
            .where(Pedido.deleted_at.is_(None))
            .group_by(Pedido.estado_codigo)
        )
        rows = self.session.exec(stmt).all()
        return [
            {"estado_codigo": r[0], "cantidad": r[1]}
            for r in rows
        ]

    def get_ingresos_por_forma_pago(
        self, desde: date | None = None, hasta: date | None = None
    ) -> list[dict]:
        stmt = (
            select(
                Pedido.forma_pago_codigo,
                func.coalesce(func.sum(Pago.monto), 0).label("total"),
                func.count(Pago.id).label("cantidad"),
            )
            .join(Pago, Pago.pedido_id == Pedido.id)
            .where(
                Pago.estado == "aprobado",
                Pedido.estado_codigo != "CANCELADO",
                Pedido.deleted_at.is_(None),
            )
        )
        if desde:
            stmt = stmt.where(func.cast(Pedido.created_at, Date) >= desde)
        if hasta:
            stmt = stmt.where(func.cast(Pedido.created_at, Date) <= hasta)

        stmt = stmt.group_by(Pedido.forma_pago_codigo)
        rows = self.session.exec(stmt).all()
        return [
            {
                "forma_pago_codigo": r[0],
                "total": Decimal(str(r[1])),
                "cantidad": r[2],
            }
            for r in rows
        ]

    def get_resumen_kpis(self) -> dict:
        today = date.today()
        first_of_month = today.replace(day=1)

        ventas_hoy = self.session.exec(
            select(func.coalesce(func.sum(Pedido.total), 0)).where(
                Pedido.estado_codigo != "CANCELADO",
                Pedido.deleted_at.is_(None),
                func.cast(Pedido.created_at, Date) == today,
            )
        ).one()

        ventas_mes = self.session.exec(
            select(func.coalesce(func.sum(Pedido.total), 0)).where(
                Pedido.estado_codigo != "CANCELADO",
                Pedido.deleted_at.is_(None),
                func.cast(Pedido.created_at, Date) >= first_of_month,
            )
        ).one()

        count_no_cancelados = self.session.exec(
            select(func.count(Pedido.id)).where(
                Pedido.estado_codigo != "CANCELADO",
                Pedido.deleted_at.is_(None),
            )
        ).one()

        ticket_promedio = (
            Decimal(str(ventas_mes)) / count_no_cancelados
            if count_no_cancelados > 0
            else Decimal("0.00")
        )

        pedidos_activos = self.session.exec(
            select(func.count(Pedido.id)).where(
                Pedido.estado_codigo.notin_(["ENTREGADO", "CANCELADO"]),
                Pedido.deleted_at.is_(None),
            )
        ).one()

        return {
            "ventas_hoy": Decimal(str(ventas_hoy)),
            "ticket_promedio": round(ticket_promedio, 2),
            "pedidos_activos": pedidos_activos,
            "ventas_mes": Decimal(str(ventas_mes)),
        }
