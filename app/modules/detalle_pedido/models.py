from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class DetallePedido(SQLModel, table=True):
    """
    PK compuesta (pedido_id, producto_id).
    Fila INMUTABLE por diseño (RN-04): no tiene updated_at.
    Los campos *_snapshot guardan los valores en el momento de la compra.
    personalizacion: lista de IDs de ingrediente que el cliente removió.
    """

    __tablename__ = "detalle_pedido"

    pedido_id: int = Field(foreign_key="pedido.id", primary_key=True)
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)

    cantidad: int = Field(ge=1)                                    # NN, CHECK >= 1
    nombre_snapshot: str = Field(max_length=200)                   # NN, snap
    precio_snapshot: float = Field(ge=0)                           # NN, snap
    subtotal_snap: float                                           # NN, snap

    # INTEGER[] en PostgreSQL — almacenado como JSON
    personalizacion: Optional[List[int]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
