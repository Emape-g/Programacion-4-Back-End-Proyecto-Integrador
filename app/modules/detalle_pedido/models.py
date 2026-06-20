from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class DetallePedido(SQLModel, table=True):
    __tablename__ = "detalle_pedido"

    pedido_id: int = Field(foreign_key="pedido.id", primary_key=True)
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)

    cantidad: int = Field(ge=1)
    nombre_snapshot: str = Field(max_length=200)
    precio_snapshot: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    subtotal_snap: Decimal = Field(max_digits=10, decimal_places=2)

    personalizacion: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
