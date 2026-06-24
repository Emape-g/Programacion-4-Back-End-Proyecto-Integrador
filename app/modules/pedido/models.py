from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column


class HistorialEstadoPedido(SQLModel, table=True):
    __tablename__ = "historial_estado_pedido"

    id: Optional[int] = Field(default=None, primary_key=True)

    pedido_id: int = Field(foreign_key="pedido.id", nullable=False)
    estado_desde: Optional[str] = Field(
        default=None, max_length=20, foreign_key="estado_pedido.codigo"
    )
    estado_hacia: str = Field(
        max_length=20, nullable=False, foreign_key="estado_pedido.codigo"
    )
    motivo: Optional[str] = Field(default=None)
    usuario_id: Optional[int] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Pedido(SQLModel, table=True):
    __tablename__ = "pedido"

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(foreign_key="usuario.id")

    direccion_entrega_id: Optional[int] = Field(
        default=None, foreign_key="direccion_entrega.id"
    )

    estado_codigo: str = Field(
        max_length=20,
        foreign_key="estado_pedido.codigo",
        default="PENDIENTE",
    )

    forma_pago_codigo: str = Field(
        max_length=20, foreign_key="forma_de_pago.codigo"
    )

    subtotal: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2, ge=0)
    descuento: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2, ge=0)
    costo_envio: Decimal = Field(default=Decimal("50.00"), max_digits=10, decimal_places=2, ge=0)
    total: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2, ge=0)

    notas: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)


class Pago(SQLModel, table=True):
    __tablename__ = "pago"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedido.id", nullable=False, index=True)

    external_reference: str = Field(max_length=64, unique=True, nullable=False)
    transaction_amount: Decimal = Field(
        max_digits=10, decimal_places=2, nullable=False, default=Decimal("0.00"),
    )
    payment_method_id: Optional[str] = Field(default=None, max_length=50)

    monto: Decimal = Field(max_digits=10, decimal_places=2, nullable=False, default=Decimal("0.00"))
    estado: str = Field(max_length=20, nullable=False, default="pendiente")

    mp_preference_id: Optional[str] = Field(default=None, max_length=200)
    mp_init_point: Optional[str] = Field(default=None, max_length=500)
    mp_payment_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, unique=True, nullable=True),
    )
    mp_status: Optional[str] = Field(default=None, max_length=30)
    mp_status_detail: Optional[str] = Field(default=None, max_length=100)
    mp_merchant_order_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
    )

    idempotency_key: str = Field(max_length=100, unique=True, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
