from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class CrearPagoRequest(BaseModel):
    pedido_id: int
    token: str
    payment_method_id: str
    installments: int = 1
    issuer_id: Optional[str] = None
    payer_email: str


class PagoResponse(BaseModel):
    id: int
    pedido_id: int
    mp_payment_id: Optional[int] = None
    mp_status: str
    mp_status_detail: Optional[str] = None
    transaction_amount: Decimal
    payment_method_id: Optional[str] = None
    external_reference: str
    idempotency_key: str

    model_config = {"from_attributes": True}
