import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.modules.pedido.models import HistorialEstadoPedido, Pago, Pedido
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.pagos.schemas import PagoCrearResponse, PagoEstadoResponse, PagoResponse

logger = logging.getLogger(__name__)

MP_STATUS_MAP = {
    "approved": "aprobado",
    "rejected": "rechazado",
    "cancelled": "rechazado",
    "refunded": "rechazado",
    "charged_back": "rechazado",
    "pending": "pendiente",
    "in_process": "pendiente",
    "authorized": "pendiente",
}


class PagoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Comunicación con SDK de MercadoPago ─────────────────────────────

    def _crear_preferencia_mp(self, monto: float, titulo: str,
                               pedido_id: int) -> dict:
        access_token = settings.mp_access_token
        if not access_token:
            raise RuntimeError("MercadoPago no configurado. Configure MP_ACCESS_TOKEN")

        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)

            preference_data = {
                "items": [{
                    "title": titulo,
                    "quantity": 1,
                    "unit_price": float(monto),
                    "currency_id": "ARS",
                }],
                "external_reference": str(pedido_id),
                "notification_url": settings.mp_notification_url,
            }

            result = sdk.preference().create(preference_data)

            if result.get("status") not in (200, 201):
                logger.error("Error creando preferencia MP: %s", result)
                raise RuntimeError(
                    "Error al crear preferencia: "
                    f"{result.get('response', {}).get('message', 'desconocido')}"
                )

            response = result.get("response", {})
            return {
                "preference_id": response.get("id"),
                "init_point": response.get("init_point"),
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Error inesperado al crear preferencia MP")
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    def _consultar_pago_mp(self, payment_id: int) -> dict:
        access_token = settings.mp_access_token
        if not access_token:
            raise RuntimeError("MP no configurado")

        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)
            result = sdk.payment().get(payment_id)

            if result.get("status") != 200:
                logger.error("Error consultando pago MP %s: %s", payment_id, result)
                raise RuntimeError(f"Error al consultar pago {payment_id}")

            response = result.get("response", {})
            return {
                "mp_payment_id": response.get("id"),
                "mp_status": response.get("status"),
                "mp_status_detail": response.get("status_detail"),
                "mp_merchant_order_id": response.get("merchant_order_id"),
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Error consultando pago MP %s", payment_id)
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    # ── Operaciones de negocio ──────────────────────────────────────────

    async def crear_pago(self, pedido_id: int, usuario_id: int) -> PagoCrearResponse:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)
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
            if existing and existing.estado == "aprobado":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este pedido ya fue pagado",
                )

            if not settings.mp_access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MercadoPago no configurado",
                )

            try:
                mp_data = self._crear_preferencia_mp(
                    monto=pedido.total,
                    titulo=f"Pedido #{pedido_id} - Food Store",
                    pedido_id=pedido_id,
                )
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

            pago = Pago(
                pedido_id=pedido_id,
                monto=pedido.total,
                estado="pendiente",
                mp_preference_id=mp_data["preference_id"],
                mp_init_point=mp_data.get("init_point"),
                idempotency_key=str(uuid.uuid4()),
            )
            uow.pagos.add(pago)

            return PagoCrearResponse(
                pago_id=pago.id,
                preference_id=mp_data["preference_id"],
                init_point=mp_data.get("init_point"),
                public_key=settings.mp_public_key,
            )

    async def procesar_webhook(self, data: dict,
                               query_params: Optional[dict] = None) -> dict:
        logger.info("Webhook recibido: data=%s qs=%s", data, query_params or {})

        if not data and query_params:
            data = query_params

        topic = data.get("type") or data.get("topic")
        data_id = data.get("data_id") or (data.get("data") or {}).get("id")
        payment_id = data.get("id")

        if not data_id and query_params:
            data_id = query_params.get("data.id") or query_params.get("id")
        if not topic and query_params:
            topic = query_params.get("topic") or query_params.get("type")

        pago_mp_id = payment_id or data_id

        if not pago_mp_id:
            return {"status": "ignored", "reason": "No payment ID"}

        if topic not in (None, "payment", "merchant_order"):
            return {"status": "ignored", "reason": f"Topic: {topic}"}

        try:
            mp_info = self._consultar_pago_mp(int(pago_mp_id))
            estado_mp = mp_info.get("mp_status")
            nuevo_estado = MP_STATUS_MAP.get(estado_mp)

            if not nuevo_estado:
                return {"status": "ignored", "reason": f"Unknown status: {estado_mp}"}

            with PedidoUnitOfWork(self._session) as uow:
                pago = uow.pagos.get_by_mp_payment_id(int(pago_mp_id))

                if not pago and mp_info.get("mp_merchant_order_id"):
                    pago = uow.pagos.get_by_mp_merchant_order_id(
                        mp_info["mp_merchant_order_id"]
                    )

                if not pago:
                    return {"status": "ignored", "reason": "Pago not found in local DB"}

                if pago.estado != "pendiente":
                    return {"status": "already_processed", "estado": pago.estado}

                pago.mp_payment_id = int(pago_mp_id)
                pago.mp_status = estado_mp
                pago.mp_status_detail = mp_info.get("mp_status_detail")
                pago.mp_merchant_order_id = mp_info.get("mp_merchant_order_id")
                pago.estado = nuevo_estado
                pago.updated_at = datetime.now(timezone.utc)
                uow.pagos.add(pago)

                if nuevo_estado == "aprobado":
                    pedido = uow.pedidos.get_by_id(pago.pedido_id)
                    if pedido and pedido.estado_codigo == "PENDIENTE":
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

            if nuevo_estado == "aprobado":
                await ws_manager.broadcast_pedido(pago.pedido_id, {
                    "event": "pago_confirmado",
                    "pedido_id": pago.pedido_id,
                    "estado_anterior": "PENDIENTE",
                    "estado_nuevo": "CONFIRMADO",
                    "usuario_id": None,
                    "motivo": "Pago aprobado por MercadoPago",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            return {
                "status": "processed",
                "pago_id": pago.id,
                "estado": nuevo_estado,
                "pedido_id": pago.pedido_id,
            }

        except Exception as e:
            logger.exception("Error procesando webhook MP")
            return {"status": "error", "reason": str(e)}

    def confirmar_pago(self, pedido_id: int,
                       payment_id: Optional[int] = None) -> PagoEstadoResponse:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = uow.pedidos.get_by_id(pedido_id)
            if not pedido or pedido.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido no encontrado",
                )

            resolved_payment_id = payment_id
            if not resolved_payment_id:
                pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)
                if pago_local and pago_local.mp_payment_id:
                    resolved_payment_id = pago_local.mp_payment_id

            if resolved_payment_id:
                try:
                    mp_info = self._consultar_pago_mp(resolved_payment_id)
                except RuntimeError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e),
                    )

                estado_mp = mp_info.get("mp_status")
                nuevo_estado = MP_STATUS_MAP.get(estado_mp, "pendiente")

                pago = uow.pagos.get_by_mp_payment_id(resolved_payment_id)
                if not pago:
                    pago = uow.pagos.get_ultimo_by_pedido(pedido_id)

                if pago:
                    pago.mp_payment_id = resolved_payment_id
                    pago.mp_status = estado_mp
                    pago.mp_status_detail = mp_info.get("mp_status_detail")
                    pago.mp_merchant_order_id = mp_info.get("mp_merchant_order_id")
                    pago.estado = nuevo_estado
                    pago.updated_at = datetime.now(timezone.utc)
                    uow.pagos.add(pago)

                    if nuevo_estado == "aprobado" and pedido.estado_codigo == "PENDIENTE":
                        pedido.estado_codigo = "CONFIRMADO"
                        pedido.updated_at = datetime.now(timezone.utc)
                        uow.pedidos.add(pedido)

                        uow.historial.add(HistorialEstadoPedido(
                            pedido_id=pedido.id,
                            estado_desde="PENDIENTE",
                            estado_hacia="CONFIRMADO",
                            motivo="Pago confirmado manualmente",
                            usuario_id=None,
                        ))

                return PagoEstadoResponse(estado=nuevo_estado, pedido_id=pedido_id)

            pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)
            return PagoEstadoResponse(
                estado=pago_local.estado if pago_local else None,
                pedido_id=pedido_id,
            )

    def get_by_pedido(self, pedido_id: int, usuario_id: int,
                      roles: set[str]) -> PagoResponse:
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
