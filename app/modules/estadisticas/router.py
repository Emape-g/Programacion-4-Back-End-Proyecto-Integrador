from datetime import date
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.auth import require_admin
from app.core.database import get_session
from app.modules.estadisticas.schemas import (
    IngresosResponse,
    PedidosEstadoItem,
    ProductoTopItem,
    ResumenResponse,
    VentasPeriodoItem,
)
from app.modules.estadisticas.service import EstadisticasService

router = APIRouter()


def get_estadisticas_service(
    session: Session = Depends(get_session),
) -> EstadisticasService:
    return EstadisticasService(session)


@router.get(
    "/resumen",
    response_model=ResumenResponse,
    summary="KPIs: ventas hoy, ticket promedio, pedidos activos, ventas mes",
)
def get_resumen(
    _: dict = Depends(require_admin),
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> ResumenResponse:
    return svc.get_resumen()


@router.get(
    "/ventas",
    response_model=List[VentasPeriodoItem],
    summary="Ventas por período (day/week/month)",
)
def get_ventas(
    desde: Annotated[date, Query()],
    hasta: Annotated[date, Query()],
    agrupacion: Annotated[str, Query(pattern="^(day|week|month)$")] = "day",
    _: dict = Depends(require_admin),
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> List[VentasPeriodoItem]:
    return svc.get_ventas_periodo(desde, hasta, agrupacion)


@router.get(
    "/productos-top",
    response_model=List[ProductoTopItem],
    summary="Top productos por ingresos",
)
def get_productos_top(
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    _: dict = Depends(require_admin),
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> List[ProductoTopItem]:
    return svc.get_productos_top(limit)


@router.get(
    "/pedidos-por-estado",
    response_model=List[PedidosEstadoItem],
    summary="Distribución de pedidos por estado",
)
def get_pedidos_por_estado(
    _: dict = Depends(require_admin),
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> List[PedidosEstadoItem]:
    return svc.get_pedidos_por_estado()


@router.get(
    "/ingresos",
    response_model=List[IngresosResponse],
    summary="Ingresos por forma de pago (solo pagos approved)",
)
def get_ingresos(
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    _: dict = Depends(require_admin),
    svc: EstadisticasService = Depends(get_estadisticas_service),
) -> List[IngresosResponse]:
    return svc.get_ingresos(desde, hasta)
