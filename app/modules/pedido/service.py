from typing import List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.pedido.models import Pedido, HistorialEstadoPedido
from app.modules.detalle_pedido.models import DetallePedido
from app.modules.pedido.schemas import (
    PedidoCreate,
    PedidoPublic,
    PedidoDetalle,
    PedidoList,
    DetallePedidoPublic,
    CambiarEstadoRequest,
)
from app.modules.pedido.unit_of_work import PedidoUnitOfWork


# ── FSM: transiciones válidas ─────────────────────────────────────────────────
# Definidas aquí en el Service, nunca en el Router (regla de negocio).
TRANSITIONS: dict[str, list[str]] = {
    "PENDIENTE":  ["CONFIRMADO", "CANCELADO"],
    "CONFIRMADO": ["EN_PREP",    "CANCELADO"],
    "EN_PREP":    ["EN_CAMINO",  "CANCELADO"],
    "EN_CAMINO":  ["ENTREGADO"],
    "ENTREGADO":  [],
    "CANCELADO":  [],
}


class PedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: PedidoUnitOfWork, pedido_id: int) -> Pedido:
        p = uow.pedidos.get_by_id(pedido_id)
        if not p or p.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido con id={pedido_id} no encontrado",
            )
        return p

    def _resolve_direccion(self, uow: PedidoUnitOfWork, usuario_id: int, direccion_entrega_id: int | None) -> int:
        if direccion_entrega_id is not None:
            dir = uow.direcciones.get_active_by_id(direccion_entrega_id)
            if not dir:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dirección id={direccion_entrega_id} no encontrada")
            if dir.usuario_id != usuario_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                    detail="La dirección no pertenece al usuario")
            return dir.id

        principales = uow.direcciones.list_principales_by_usuario(usuario_id)
        if principales:
            return principales[0].id

        todas = uow.direcciones.list_by_usuario(usuario_id)
        if todas:
            return todas[0].id

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El usuario no tiene direcciones de entrega registradas")

    def _build_detalle(self, uow: PedidoUnitOfWork, pedido: Pedido) -> PedidoDetalle:
        items = uow.detalles.get_by_pedido(pedido.id)
        return PedidoDetalle(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            direccion_entrega_id=pedido.direccion_entrega_id,
            estado_codigo=pedido.estado_codigo,
            forma_pago_codigo=pedido.forma_pago_codigo,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            notas=pedido.notas,
            detalles=[DetallePedidoPublic.model_validate(i) for i in items],
            created_at=pedido.created_at,
            updated_at=pedido.updated_at,
        )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: PedidoCreate) -> PedidoDetalle:
        with PedidoUnitOfWork(self._session) as uow:

            # Validar forma de pago
            forma = uow.formas_de_pago.get_by_id(data.forma_pago_codigo)
            if not forma:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Forma de pago '{data.forma_pago_codigo}' no encontrada",
                )
            if not forma.habilitado:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Forma de pago '{data.forma_pago_codigo}' no está habilitada",
                )

            # Validar que el estado inicial existe en la BD (requiere seed)
            if not uow.estados.get_by_id("PENDIENTE"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Estado PENDIENTE no encontrado. Ejecute el seed primero.",
                )

            # Validar productos y armar snapshots
            subtotal = 0.0
            snapshots = []

            for item in data.detalles:
                producto = uow.productos.get_by_id(item.producto_id)
                if not producto:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Producto id={item.producto_id} no encontrado",
                    )
                if not producto.disponible:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Producto '{producto.nombre}' no está disponible",
                    )

                # producto.precio_base es Decimal; pedido aún opera en float
                # (pendiente migrar Pedido a Decimal junto al SVG del dominio 3).
                precio = float(producto.precio_base)
                sub = round(precio * item.cantidad, 2)
                subtotal += sub

                snapshots.append({
                    "producto_id": item.producto_id,
                    "cantidad": item.cantidad,
                    "nombre_snapshot": producto.nombre,
                    "precio_snapshot": precio,
                    "subtotal_snap": sub,
                    "personalizacion": item.personalizacion,
                })

            subtotal = round(subtotal, 2)
            descuento = 0.0
            costo_envio = 50.0
            total = round(subtotal - descuento + costo_envio, 2)

            direccion_id = self._resolve_direccion(uow, data.usuario_id, data.direccion_entrega_id)

            # Crear cabecera del pedido
            pedido = Pedido(
                usuario_id=data.usuario_id,
                direccion_entrega_id=direccion_id,
                estado_codigo="PENDIENTE",
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=subtotal,
                descuento=descuento,
                costo_envio=costo_envio,
                total=total,
                notas=data.notas,
            )
            uow.pedidos.add(pedido)  # flush → genera pedido.id

            # Crear detalles con snapshots
            for snap in snapshots:
                detalle = DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=snap["producto_id"],
                    cantidad=snap["cantidad"],
                    nombre_snapshot=snap["nombre_snapshot"],
                    precio_snapshot=snap["precio_snapshot"],
                    subtotal_snap=snap["subtotal_snap"],
                    personalizacion=snap["personalizacion"],
                )
                uow.detalles.add(detalle)

            # Audit Trail: registro inicial (creación del pedido)
            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_anterior=None,
                estado_nuevo="PENDIENTE",
                usuario_id=data.usuario_id,
            ))

            result = self._build_detalle(uow, pedido)
        return result

    def get_by_estado(self, estado_codigo: str, offset: int = 0, limit: int = 20) -> PedidoList:
        with PedidoUnitOfWork(self._session) as uow:
            if not uow.estados.get_by_id(estado_codigo):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Estado '{estado_codigo}' no encontrado",
                )
            items = uow.pedidos.get_by_estado(estado_codigo, offset=offset, limit=limit)
            total = uow.pedidos.count_by_estado(estado_codigo)
            result = PedidoList(
                data=[PedidoPublic.model_validate(p) for p in items],
                total=total,
            )
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> PedidoList:
        with PedidoUnitOfWork(self._session) as uow:
            items = uow.pedidos.get_all_active(offset=offset, limit=limit)
            total = uow.pedidos.count_active()
            result = PedidoList(
                data=[PedidoPublic.model_validate(p) for p in items],
                total=total,
            )
        return result

    def get_by_id(self, pedido_id: int) -> PedidoDetalle:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            result = self._build_detalle(uow, pedido)
        return result

    def cambiar_estado(self, pedido_id: int, data: CambiarEstadoRequest) -> PedidoDetalle:
        """
        Avanza el estado del pedido según el FSM.
        Reglas de negocio (RN-01, RN-05) validadas aquí en el Service.
        """
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            estado_actual = pedido.estado_codigo
            estado_hacia = data.estado_hacia

            # Verificar que el estado destino existe
            if not uow.estados.get_by_id(estado_hacia):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Estado '{estado_hacia}' no encontrado",
                )

            # Validar transición según FSM (RN-01)
            permitidos = TRANSITIONS.get(estado_actual, [])
            if estado_hacia not in permitidos:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Transición inválida: {estado_actual} → {estado_hacia}. "
                        f"Transiciones permitidas desde {estado_actual}: {permitidos or 'ninguna (estado terminal)'}."
                    ),
                )

            # Motivo obligatorio al cancelar (RN-05)
            if estado_hacia == "CANCELADO" and not data.motivo:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El campo 'motivo' es obligatorio al cancelar un pedido",
                )

            pedido.estado_codigo = estado_hacia
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            # Audit Trail: registrar la transición (solo INSERT, nunca UPDATE)
            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_anterior=estado_actual,
                estado_nuevo=estado_hacia,
                motivo=data.motivo,
            ))

            result = self._build_detalle(uow, pedido)
        return result

    def delete(self, pedido_id: int) -> None:
        """Soft delete: marca deleted_at, el pedido deja de aparecer en listados."""
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            pedido.deleted_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)
