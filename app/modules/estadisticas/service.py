from datetime import date

from sqlmodel import Session

from app.modules.estadisticas.repository import EstadisticasRepository
from app.modules.estadisticas.schemas import (
    IngresosResponse,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)


class EstadisticasService:
    def __init__(self, session: Session) -> None:
        self._repo = EstadisticasRepository(session)

    def get_ventas_periodo(
        self, desde: date, hasta: date, agrupacion: str = "day"
    ) -> list[VentasPeriodoItem]:
        rows = self._repo.get_ventas_periodo(desde, hasta, agrupacion)
        return [VentasPeriodoItem(**r) for r in rows]

    def get_productos_top(self, limit: int = 10) -> list[ProductoTopItem]:
        rows = self._repo.get_productos_top(limit)
        return [ProductoTopItem(**r) for r in rows]

    def get_pedidos_por_estado(self) -> list[PedidosEstadoItem]:
        rows = self._repo.get_pedidos_por_estado()
        return [PedidosEstadoItem(**r) for r in rows]

    def get_ingresos(
        self, desde: date | None = None, hasta: date | None = None
    ) -> list[IngresosResponse]:
        rows = self._repo.get_ingresos_por_forma_pago(desde, hasta)
        return [IngresosResponse(**r) for r in rows]

    def get_resumen(self) -> ResumenResponse:
        data = self._repo.get_resumen_kpis()
        return ResumenResponse(**data)
