from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field


# ── Schemas de DetallePedido ──────────────────────────────────────────────────

class DetallePedidoCreate(SQLModel):
    """Ítem enviado por el cliente al crear un pedido."""
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: Optional[List[int]] = None   # IDs de ingredientes removidos


class DetallePedidoPublic(SQLModel):
    """Ítem devuelto en la respuesta. Incluye los snapshots."""
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: float
    subtotal_snap: float
    personalizacion: Optional[List[int]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Schemas de Pedido ─────────────────────────────────────────────────────────

class PedidoCreate(SQLModel):
    """Payload para crear un pedido. Los precios los calcula el servidor."""
    usuario_id: int
    forma_pago_codigo: str
    notas: Optional[str] = None
    detalles: List[DetallePedidoCreate] = Field(min_length=1)


class CambiarEstadoRequest(SQLModel):
    """Payload para avanzar el estado de un pedido por el FSM."""
    estado_hacia: str
    motivo: Optional[str] = None   # Obligatorio si estado_hacia == CANCELADO (RN-05)


class PedidoPublic(SQLModel):
    """Respuesta compacta para listados."""
    id: int
    usuario_id: int
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: float
    descuento: float
    costo_envio: float
    total: float
    notas: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PedidoDetalle(SQLModel):
    """Respuesta completa con los ítems del pedido."""
    id: int
    usuario_id: int
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: float
    descuento: float
    costo_envio: float
    total: float
    notas: Optional[str] = None
    detalles: List[DetallePedidoPublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PedidoList(SQLModel):
    data: List[PedidoPublic]
    total: int
