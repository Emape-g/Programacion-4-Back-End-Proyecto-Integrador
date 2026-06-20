from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class CrearPagoRequest(BaseModel):
    pedido_id: int


class PagoCrearResponse(BaseModel):
    pago_id: int
    pedido_id: int
    mp_preference_id: Optional[str] = None
    init_point: Optional[str] = None
    external_reference: str
    idempotency_key: str
    transaction_amount: Decimal
    estado: str = "pendiente"
    public_key: Optional[str] = None


class PagoEstadoResponse(BaseModel):
    estado: Optional[str] = None
    pedido_id: int


class PagoResponse(BaseModel):
    id: int
    pedido_id: int
    monto: Decimal
    transaction_amount: Decimal
    payment_method_id: Optional[str] = None
    external_reference: str
    estado: str
    mp_preference_id: Optional[str] = None
    mp_init_point: Optional[str] = None
    mp_payment_id: Optional[int] = None
    mp_status: Optional[str] = None
    mp_status_detail: Optional[str] = None
    idempotency_key: str

    model_config = {"from_attributes": True}
