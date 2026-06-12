import uuid
from datetime import datetime, timezone
from decimal import Decimal

import mercadopago
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.modules.pedido.models import HistorialEstadoPedido, Pago, Pedido
from app.modules.pedido.repository import PagoRepository, PedidoRepository
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.pagos.schemas import CrearPagoRequest, PagoResponse


class PagoService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._sdk = mercadopago.SDK(settings.mp_access_token)

    async def crear_pago(self, data: CrearPagoRequest, usuario_id: int) -> PagoResponse:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(data.pedido_id)
            if not pedido or pedido.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado",
                )
            if pedido.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes pagar un pedido ajeno",
                )
            if pedido.estado_codigo != "PENDIENTE":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El pedido no está en estado PENDIENTE",
                )

            existing = uow.pagos.get_by_pedido(pedido.id)
            if existing and existing.mp_status == "approved":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este pedido ya fue pagado",
                )

            external_reference = str(uuid.uuid4())
            idempotency_key = str(uuid.uuid4())

            payment_data = {
                "transaction_amount": float(pedido.total),
                "token": data.token,
                "description": f"Pedido #{pedido.id} - Food Store",
                "installments": data.installments,
                "payment_method_id": data.payment_method_id,
                "payer": {"email": data.payer_email},
                "external_reference": external_reference,
            }
            if data.issuer_id:
                payment_data["issuer_id"] = data.issuer_id

            request_options = mercadopago.config.RequestOptions()
            request_options.custom_headers = {
                "X-Idempotency-Key": idempotency_key
            }

            mp_response = self._sdk.payment().create(payment_data, request_options)
            mp_data = mp_response.get("response", {})

            pago = Pago(
                pedido_id=pedido.id,
                mp_payment_id=mp_data.get("id"),
                mp_status=mp_data.get("status", "pending"),
                mp_status_detail=mp_data.get("status_detail"),
                transaction_amount=Decimal(str(mp_data.get("transaction_amount", pedido.total))),
                payment_method_id=mp_data.get("payment_method_id"),
                external_reference=external_reference,
                idempotency_key=idempotency_key,
            )
            uow.pagos.add(pago)

            if pago.mp_status == "approved":
                pedido.estado_codigo = "CONFIRMADO"
                pedido.updated_at = datetime.now(timezone.utc)
                uow.pedidos.add(pedido)

                uow.historial.add(HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde="PENDIENTE",
                    estado_hacia="CONFIRMADO",
                    motivo="Pago aprobado por MercadoPago",
                    usuario_id=None,
                ))

            result = PagoResponse.model_validate(pago)

        if pago.mp_status == "approved":
            await ws_manager.broadcast_pedido(pedido.id, {
                "event": "pago_confirmado",
                "pedido_id": pedido.id,
                "estado_anterior": "PENDIENTE",
                "estado_nuevo": "CONFIRMADO",
                "usuario_id": None,
                "motivo": "Pago aprobado por MercadoPago",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return result

    async def webhook(self, body: dict) -> dict:
        topic = body.get("type") or body.get("topic")
        if topic != "payment":
            return {"status": "ignored"}

        mp_data = body.get("data", {})
        payment_id = mp_data.get("id") or body.get("data_id")
        if not payment_id:
            return {"status": "no_id"}

        mp_response = self._sdk.payment().get(int(payment_id))
        payment_info = mp_response.get("response", {})
        external_ref = payment_info.get("external_reference")
        if not external_ref:
            return {"status": "no_ref"}

        with PedidoUnitOfWork(self._session) as uow:
            pago = uow.pagos.get_by_external_reference(external_ref)
            if not pago:
                return {"status": "not_found"}

            pago.mp_payment_id = int(payment_id)
            pago.mp_status = payment_info.get("status", pago.mp_status)
            pago.mp_status_detail = payment_info.get("status_detail")
            pago.transaction_amount = Decimal(
                str(payment_info.get("transaction_amount", pago.transaction_amount))
            )
            pago.payment_method_id = payment_info.get("payment_method_id")
            pago.updated_at = datetime.now(timezone.utc)
            uow.pagos.add(pago)

            pedido = uow.pedidos.get_by_id(pago.pedido_id)
            if pedido and pago.mp_status == "approved" and pedido.estado_codigo == "PENDIENTE":
                pedido.estado_codigo = "CONFIRMADO"
                pedido.updated_at = datetime.now(timezone.utc)
                uow.pedidos.add(pedido)

                uow.historial.add(HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde="PENDIENTE",
                    estado_hacia="CONFIRMADO",
                    motivo="Pago confirmado vía webhook MercadoPago",
                    usuario_id=None,
                ))

        if pedido and pago.mp_status == "approved":
            await ws_manager.broadcast_pedido(pedido.id, {
                "event": "pago_confirmado",
                "pedido_id": pedido.id,
                "estado_anterior": "PENDIENTE",
                "estado_nuevo": "CONFIRMADO",
                "usuario_id": None,
                "motivo": "Pago confirmado vía webhook",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return {"status": "ok"}

    def get_by_pedido(self, pedido_id: int, usuario_id: int, roles: set[str]) -> PagoResponse:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)
            if not pedido or pedido.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado",
                )
            if not roles.intersection({"ADMIN"}) and pedido.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sin acceso a este pago",
                )

            pago = uow.pagos.get_by_pedido(pedido_id)
            if not pago:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pago no encontrado para este pedido",
                )
            return PagoResponse.model_validate(pago)
