from decimal import Decimal
from typing import List
from pydantic import BaseModel


class VentasPeriodoItem(BaseModel):
    periodo: str
    total_ventas: Decimal
    cantidad_pedidos: int


class ProductoTopItem(BaseModel):
    nombre: str
    ingresos: Decimal
    cantidad_vendida: int


class PedidosEstadoItem(BaseModel):
    estado_codigo: str
    cantidad: int


class IngresosResponse(BaseModel):
    forma_pago_codigo: str
    total: Decimal
    cantidad: int


class ResumenResponse(BaseModel):
    ventas_hoy: Decimal
    ticket_promedio: Decimal
    pedidos_activos: int
    ventas_mes: Decimal
