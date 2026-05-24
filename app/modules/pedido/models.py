from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class HistorialEstadoPedido(SQLModel, table=True):
    """
    Audit Trail append-only: registra cada transición de estado del pedido.
    Solo se permite INSERT, jamás UPDATE ni DELETE (RN-06).
    """

    __tablename__ = "historial_estado_pedido"

    id: Optional[int] = Field(default=None, primary_key=True)

    pedido_id: int = Field(foreign_key="pedido.id", nullable=False)
    estado_anterior: Optional[str] = Field(default=None, max_length=20)  # NULL en la creación
    estado_nuevo: str = Field(max_length=20, nullable=False)
    motivo: Optional[str] = Field(default=None)          # requerido al cancelar
    usuario_id: Optional[int] = Field(default=None)      # quién realizó el cambio

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Pedido(SQLModel, table=True):
    """
    Cabecera del pedido. Los campos monetarios son snapshot (inmutables
    desde la creación). El estado cambia siguiendo el FSM de EstadoPedido.
    """

    __tablename__ = "pedido"

    id: Optional[int] = Field(default=None, primary_key=True)

    # FK → usuario que realizó el pedido
    usuario_id: int = Field(foreign_key="usuario.id")

    # FK → estado actual en el FSM
    estado_codigo: str = Field(
        max_length=20,
        foreign_key="estado_pedido.codigo",
        default="PENDIENTE",
    )

    # FK → forma de pago elegida
    forma_pago_codigo: str = Field(max_length=20, foreign_key="forma_de_pago.codigo")

    # Snapshot monetario (se calcula al crear y no cambia)
    subtotal: float = Field(default=0.0, ge=0)
    descuento: float = Field(default=0.0, ge=0)
    costo_envio: float = Field(default=50.0, ge=0)
    total: float = Field(default=0.0, ge=0)

    # Opcional: notas del cliente
    notas: Optional[str] = Field(default=None)

    # Auditoría
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)
