from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field


class ItemPedidoRequest(SQLModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: Optional[List[int]] = None


class CrearPedidoRequest(SQLModel):
    items: List[ItemPedidoRequest] = Field(min_length=1)
    forma_pago_codigo: str
    direccion_id: Optional[int] = None
    notas: Optional[str] = None


class AvanzarEstadoRequest(SQLModel):
    nuevo_estado: str
    motivo: Optional[str] = None


class DetallePedidoRead(SQLModel):
    producto_id: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    subtotal_snap: Decimal
    cantidad: int
    personalizacion: Optional[List[int]] = None

    model_config = {"from_attributes": True}


class HistorialRead(SQLModel):
    id: int
    estado_desde: Optional[str] = None
    estado_hacia: str
    motivo: Optional[str] = None
    usuario_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PagoRead(SQLModel):
    id: int
    mp_payment_id: Optional[int] = None
    mp_status: str
    mp_status_detail: Optional[str] = None
    transaction_amount: Decimal
    payment_method_id: Optional[str] = None
    external_reference: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PedidoRead(SQLModel):
    id: int
    estado_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class PedidoDetail(SQLModel):
    id: int
    estado_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    items: List[DetallePedidoRead] = []
    historial: List[HistorialRead] = []
    pago: Optional[PagoRead] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PedidoList(SQLModel):
    items: List[PedidoRead]
    total: int
    page: int
    size: int
