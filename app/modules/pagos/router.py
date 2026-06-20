import hashlib
import hmac
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.modules.pagos.schemas import (
    CrearPagoRequest,
    PagoCrearResponse,
    PagoEstadoResponse,
    PagoResponse,
)
from app.modules.pagos.service import PagoService

router = APIRouter()


def get_pago_service(session: Session = Depends(get_session)) -> PagoService:
    return PagoService(session)


@router.post(
    "/crear",
    response_model=PagoCrearResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear preferencia de pago en MercadoPago",
)
async def crear_pago(
    data: CrearPagoRequest,
    payload: dict = Depends(get_current_user),
    svc: PagoService = Depends(get_pago_service),
) -> PagoCrearResponse:
    usuario_id = int(payload["uid"])
    return await svc.crear_pago(data, usuario_id)


@router.post(
    "/webhook",
    summary="Webhook IPN de MercadoPago",
)
async def webhook(
    request: Request,
    svc: PagoService = Depends(get_pago_service),
) -> dict:
    body = await request.json()
    query_params = dict(request.query_params)

    secret = settings.mp_webhook_secret
    if secret:
        signature = request.headers.get("x-signature", "")
        request_id = request.headers.get("x-request-id", "")
        parts = dict(
            p.strip().split("=", 1)
            for p in signature.split(",") if "=" in p
        )
        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")
        data_id = (
            query_params.get("data.id")
            or (body.get("data") or {}).get("id")
            or body.get("id")
            or ""
        )
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        expected = hmac.new(
            secret.encode(), manifest.encode(), hashlib.sha256,
        ).hexdigest()
        if not v1 or not hmac.compare_digest(expected, v1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firma MercadoPago inválida",
            )

    return await svc.procesar_webhook(body, query_params)


@router.get(
    "/confirmar/{pedido_id}",
    response_model=PagoEstadoResponse,
    summary="Confirmar/sincronizar estado de pago con MercadoPago",
)
def confirmar_pago(
    pedido_id: int,
    payment_id: Optional[int] = None,
    payload: dict = Depends(get_current_user),
    svc: PagoService = Depends(get_pago_service),
) -> PagoEstadoResponse:
    return svc.confirmar_pago(pedido_id, payment_id)


@router.get(
    "/{pedido_id}",
    response_model=PagoResponse,
    summary="Consultar pago de un pedido",
)
def get_pago(
    pedido_id: int,
    payload: dict = Depends(get_current_user),
    svc: PagoService = Depends(get_pago_service),
) -> PagoResponse:
    usuario_id = int(payload["uid"])
    roles = set(payload.get("roles") or [])
    return svc.get_by_pedido(pedido_id, usuario_id, roles)
