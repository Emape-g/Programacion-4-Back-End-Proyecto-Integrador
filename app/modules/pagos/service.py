import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

try:
    import mercadopago
except ImportError:
    mercadopago = None

from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.modules.pedido.models import HistorialEstadoPedido, Pago, Pedido
from app.modules.pedido.unit_of_work import PedidoUnitOfWork
from app.modules.pagos.schemas import (
    CrearPagoRequest,
    PagoCrearResponse,
    PagoEstadoResponse,
    PagoResponse,
)

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

    def _discount_stock(self, uow: PedidoUnitOfWork, pedido_id: int) -> None:
        items = uow.detalles.get_by_pedido(pedido_id)
        for item in items:
            producto = uow.productos.get_by_id(item.producto_id)
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto id={item.producto_id} no encontrado",
                )
            if producto.stock_cantidad < item.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para '{producto.nombre}' "
                           f"(disponible: {producto.stock_cantidad}, pedido: {item.cantidad})",
                )
            producto.stock_cantidad -= item.cantidad
            uow.productos.add(producto)

    # ── Comunicación con SDK de MercadoPago ─────────────────────────────

    def _crear_preferencia_mp(self, monto: float, titulo: str,
                               external_reference: str,
                               idempotency_key: str | None = None) -> dict:
        access_token = settings.mp_access_token
        if not access_token:
            raise RuntimeError("MercadoPago no configurado. Configure MP_ACCESS_TOKEN")

        if mercadopago is None:
            raise RuntimeError("pip install mercadopago")

        try:
            sdk = mercadopago.SDK(access_token)

            success_url = settings.mp_back_url_success
            is_public_url = success_url.startswith("https://") and "localhost" not in success_url

            preference_data = {
                "items": [{
                    "title": titulo,
                    "quantity": 1,
                    "unit_price": float(monto),
                    "currency_id": "ARS",
                }],
                "external_reference": external_reference,
                "back_urls": {
                    "success": success_url,
                    "failure": settings.mp_back_url_failure,
                    "pending": settings.mp_back_url_pending,
                },
                "notification_url": settings.mp_notification_url or None,
            }
            if is_public_url:
                preference_data["auto_return"] = "approved"
            preference_data = {k: v for k, v in preference_data.items() if v is not None}

            request_options = None
            if idempotency_key:
                try:
                    from mercadopago.config import RequestOptions
                    request_options = RequestOptions(
                        custom_headers={"x-idempotency-key": idempotency_key}
                    )
                except Exception:
                    request_options = None

            if request_options is not None:
                result = sdk.preference().create(preference_data, request_options)
            else:
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

        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Error inesperado al crear preferencia MP")
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    def _consultar_pago_mp(self, payment_id: int) -> dict:
        access_token = settings.mp_access_token
        if not access_token:
            raise RuntimeError("MP no configurado")

        if mercadopago is None:
            raise RuntimeError("pip install mercadopago")

        try:
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
                "external_reference": response.get("external_reference"),
            }

        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Error consultando pago MP %s", payment_id)
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    def _crear_payment_mp(self, payment_data: dict,
                          idempotency_key: str) -> dict:
        access_token = settings.mp_access_token
        if not access_token:
            raise RuntimeError("MercadoPago no configurado. Configure MP_ACCESS_TOKEN")
        if mercadopago is None:
            raise RuntimeError("pip install mercadopago")

        try:
            sdk = mercadopago.SDK(access_token)

            request_options = None
            try:
                from mercadopago.config import RequestOptions
                request_options = RequestOptions(
                    custom_headers={"x-idempotency-key": idempotency_key}
                )
            except Exception:
                request_options = None

            if request_options is not None:
                result = sdk.payment().create(payment_data, request_options)
            else:
                result = sdk.payment().create(payment_data)

            if result.get("status") not in (200, 201):
                logger.error("Error creando pago MP: %s", result)
                raise RuntimeError(
                    "Error al crear pago: "
                    f"{result.get('response', {}).get('message', 'desconocido')}"
                )

            response = result.get("response", {})
            return {
                "mp_payment_id": response.get("id"),
                "mp_status": response.get("status"),
                "mp_status_detail": response.get("status_detail"),
                "transaction_amount": response.get("transaction_amount"),
                "payment_method_id": response.get("payment_method_id"),
                "external_reference": response.get("external_reference"),
            }

        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Error inesperado al crear pago MP")
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    # ── Operaciones de negocio ──────────────────────────────────────────

    async def crear_pago(self, data: CrearPagoRequest,
                         usuario_id: int) -> PagoCrearResponse:
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

            idempotency_key = str(uuid.uuid4())
            external_reference = f"pedido-{pedido.id}-{uuid.uuid4().hex[:8]}"
            titulo = f"Pedido #{pedido.id} - Food Store"

            try:
                mp_info = self._crear_preferencia_mp(
                    monto=float(pedido.total),
                    titulo=titulo,
                    external_reference=external_reference,
                    idempotency_key=idempotency_key,
                )
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

            pago = Pago(
                pedido_id=pedido.id,
                external_reference=external_reference,
                transaction_amount=pedido.total,
                monto=pedido.total,
                estado="pendiente",
                mp_preference_id=mp_info.get("preference_id"),
                mp_init_point=mp_info.get("init_point"),
                idempotency_key=idempotency_key,
            )
            uow.pagos.add(pago)

            response = PagoCrearResponse(
                pago_id=pago.id,
                pedido_id=pedido.id,
                mp_preference_id=mp_info.get("preference_id"),
                init_point=mp_info.get("init_point"),
                external_reference=external_reference,
                idempotency_key=idempotency_key,
                transaction_amount=pedido.total,
                estado="pendiente",
                public_key=settings.mp_public_key,
            )

        return response

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

        if topic not in (None, "payment"):
            return {"status": "ignored", "reason": f"Topic: {topic}"}

        try:
            mp_info = self._consultar_pago_mp(int(pago_mp_id))
            estado_mp = mp_info.get("mp_status")
            nuevo_estado = MP_STATUS_MAP.get(estado_mp)

            if not nuevo_estado:
                return {"status": "not_found", "reason": f"Unknown status: {estado_mp}"}

            with PedidoUnitOfWork(self._session) as uow:
                pago = uow.pagos.get_by_mp_payment_id(int(pago_mp_id))

                if not pago and mp_info.get("mp_merchant_order_id"):
                    pago = uow.pagos.get_by_mp_merchant_order_id(
                        mp_info["mp_merchant_order_id"]
                    )

                if not pago and mp_info.get("external_reference"):
                    ext_ref = mp_info["external_reference"]
                    pago = uow.pagos.get_by_external_reference(ext_ref) \
                        if hasattr(uow.pagos, "get_by_external_reference") else None
                    if not pago:
                        try:
                            if ext_ref.startswith("pedido-"):
                                pedido_ref_id = int(ext_ref.split("-")[1])
                            else:
                                pedido_ref_id = int(ext_ref)
                            pago = uow.pagos.get_ultimo_by_pedido(pedido_ref_id)
                        except (ValueError, TypeError, IndexError):
                            pago = None

                if not pago:
                    return {"status": "not_found", "reason": "Pago not found in local DB"}

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
                        self._discount_stock(uow, pedido.id)
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
                        self._discount_stock(uow, pedido.id)
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
