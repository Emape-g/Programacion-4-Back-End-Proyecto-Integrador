from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.ws_manager import ws_manager
from app.modules.detalle_pedido.models import DetallePedido
from app.modules.pedido.models import HistorialEstadoPedido, Pedido
from app.modules.pedido.schemas import (
    AvanzarEstadoRequest,
    CrearPedidoRequest,
    DetallePedidoRead,
    HistorialRead,
    PagoRead,
    PedidoDetail,
    PedidoList,
    PedidoRead,
)
from app.modules.pedido.unit_of_work import PedidoUnitOfWork

TRANSITIONS: dict[str, list[str]] = {
    "PENDIENTE":  ["CONFIRMADO", "CANCELADO"],
    "CONFIRMADO": ["EN_PREP",    "CANCELADO"],
    "EN_PREP":    ["ENTREGADO",  "CANCELADO"],
    "ENTREGADO":  [],
    "CANCELADO":  [],
}

STOCK_CONFIRMED_STATES = {"CONFIRMADO", "EN_PREP", "ENTREGADO"}


class PedidoService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: PedidoUnitOfWork, pedido_id: int) -> Pedido:
        p = uow.pedidos.get_by_id(pedido_id)
        if not p or p.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido con id={pedido_id} no encontrado",
            )
        return p

    def _resolve_direccion(
        self, uow: PedidoUnitOfWork, usuario_id: int, direccion_id: int | None
    ) -> int | None:
        if direccion_id is not None:
            d = uow.direcciones.get_active_by_id(direccion_id)
            if not d:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dirección id={direccion_id} no encontrada",
                )
            if d.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="La dirección no pertenece al usuario",
                )
            return d.id

        principales = uow.direcciones.list_principales_by_usuario(usuario_id)
        if principales:
            return principales[0].id

        todas = uow.direcciones.list_by_usuario(usuario_id)
        if todas:
            return todas[0].id

        return None

    def _restore_stock(self, uow: PedidoUnitOfWork, pedido_id: int) -> None:
        items = uow.detalles.get_by_pedido(pedido_id)
        for item in items:
            producto = uow.productos.get_by_id(item.producto_id)
            if producto:
                producto.stock_cantidad += item.cantidad
                uow.productos.add(producto)

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

    def _build_read(self, pedido: Pedido) -> PedidoRead:
        return PedidoRead.model_validate(pedido)

    def _build_detail(self, uow: PedidoUnitOfWork, pedido: Pedido) -> PedidoDetail:
        items = uow.detalles.get_by_pedido(pedido.id)
        historial = uow.historial.get_by_pedido(pedido.id)
        pago_obj = uow.pagos.get_by_pedido(pedido.id)

        return PedidoDetail(
            id=pedido.id,
            usuario_id=pedido.usuario_id,
            estado_codigo=pedido.estado_codigo,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            items=[DetallePedidoRead.model_validate(i) for i in items],
            historial=[HistorialRead.model_validate(h) for h in historial],
            pago=PagoRead.model_validate(pago_obj) if pago_obj else None,
            created_at=pedido.created_at,
        )

    async def create(self, data: CrearPedidoRequest, usuario_id: int) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
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

            if not uow.estados.get_by_id("PENDIENTE"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Estado PENDIENTE no encontrado. Ejecute el seed.",
                )

            subtotal = Decimal("0.00")
            snapshots = []

            for item in data.items:
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
                if producto.stock_cantidad < item.cantidad:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Stock insuficiente para '{producto.nombre}' "
                               f"(disponible: {producto.stock_cantidad}, pedido: {item.cantidad})",
                    )

                precio = producto.precio_base
                sub = precio * item.cantidad
                subtotal += sub

                snapshots.append({
                    "producto_id": item.producto_id,
                    "cantidad": item.cantidad,
                    "nombre_snapshot": producto.nombre,
                    "precio_snapshot": precio,
                    "subtotal_snap": sub,
                    "personalizacion": item.personalizacion,
                })

            descuento = Decimal("0.00")
            costo_envio = Decimal("50.00")
            total = subtotal - descuento + costo_envio

            direccion_id = self._resolve_direccion(uow, usuario_id, data.direccion_id)

            pedido = Pedido(
                usuario_id=usuario_id,
                direccion_entrega_id=direccion_id,
                estado_codigo="PENDIENTE",
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=subtotal,
                descuento=descuento,
                costo_envio=costo_envio,
                total=total,
                notas=data.notas,
            )
            uow.pedidos.add(pedido)

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

            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=None,
                estado_hacia="PENDIENTE",
                usuario_id=usuario_id,
            ))

            result = self._build_read(pedido)

        await ws_manager.broadcast_pedido(result.id, {
            "event": "estado_cambiado",
            "pedido_id": result.id,
            "estado_anterior": None,
            "estado_nuevo": "PENDIENTE",
            "usuario_id": usuario_id,
            "motivo": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return result

    def get_all(
        self, offset: int = 0, limit: int = 20,
        usuario_id: int | None = None, estado: str | None = None,
    ) -> PedidoList:
        with PedidoUnitOfWork(self._session) as uow:
            if usuario_id and estado:
                items = uow.pedidos.get_by_usuario_and_estado(usuario_id, estado, offset=offset, limit=limit)
                total = uow.pedidos.count_by_usuario_and_estado(usuario_id, estado)
            elif usuario_id:
                items = uow.pedidos.get_by_usuario(usuario_id, offset=offset, limit=limit)
                total = uow.pedidos.count_by_usuario(usuario_id)
            elif estado:
                items = uow.pedidos.get_by_estado(estado, offset=offset, limit=limit)
                total = uow.pedidos.count_by_estado(estado)
            else:
                items = uow.pedidos.get_all_active(offset=offset, limit=limit)
                total = uow.pedidos.count_active()

            page = (offset // limit) + 1 if limit else 1
            return PedidoList(
                items=[PedidoRead.model_validate(p) for p in items],
                total=total,
                page=page,
                size=limit,
            )

    def get_by_id(self, pedido_id: int) -> PedidoDetail:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            return self._build_detail(uow, pedido)

    def get_historial(self, pedido_id: int) -> list[HistorialRead]:
        with PedidoUnitOfWork(self._session) as uow:
            self._get_or_404(uow, pedido_id)
            items = uow.historial.get_by_pedido(pedido_id)
            return [HistorialRead.model_validate(h) for h in items]

    async def avanzar_estado(
        self, pedido_id: int, data: AvanzarEstadoRequest, usuario_id: int
    ) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            estado_actual = pedido.estado_codigo
            nuevo_estado = data.nuevo_estado

            if not uow.estados.get_by_id(nuevo_estado):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Estado '{nuevo_estado}' no encontrado",
                )

            permitidos = TRANSITIONS.get(estado_actual, [])
            if nuevo_estado not in permitidos:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Transición inválida: {estado_actual} → {nuevo_estado}. "
                        f"Permitidas: {permitidos or 'ninguna (estado terminal)'}."
                    ),
                )

            if nuevo_estado == "CANCELADO" and not data.motivo:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="El campo 'motivo' es obligatorio al cancelar un pedido",
                )

            if estado_actual == "PENDIENTE" and nuevo_estado == "CONFIRMADO":
                self._discount_stock(uow, pedido.id)

            if nuevo_estado == "CANCELADO" and estado_actual in STOCK_CONFIRMED_STATES:
                self._restore_stock(uow, pedido.id)

            pedido.estado_codigo = nuevo_estado
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=estado_actual,
                estado_hacia=nuevo_estado,
                motivo=data.motivo,
                usuario_id=usuario_id,
            ))

            result = self._build_read(pedido)

        event_name = "pedido_cancelado" if nuevo_estado == "CANCELADO" else "estado_cambiado"
        await ws_manager.broadcast_pedido(result.id, {
            "event": event_name,
            "pedido_id": result.id,
            "estado_anterior": estado_actual,
            "estado_nuevo": nuevo_estado,
            "usuario_id": usuario_id,
            "motivo": data.motivo,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return result

    async def cancelar_propio(
        self, pedido_id: int, usuario_id: int, motivo: str | None = None,
    ) -> PedidoRead:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            if pedido.usuario_id != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puedes cancelar tus propios pedidos",
                )

            if pedido.estado_codigo not in ("PENDIENTE", "CONFIRMADO"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Solo se pueden cancelar pedidos en estado PENDIENTE o CONFIRMADO",
                )

            estado_anterior = pedido.estado_codigo
            if estado_anterior in STOCK_CONFIRMED_STATES:
                self._restore_stock(uow, pedido.id)
            pedido.estado_codigo = "CANCELADO"
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=estado_anterior,
                estado_hacia="CANCELADO",
                motivo=motivo or "Cancelado por el cliente",
                usuario_id=usuario_id,
            ))

            result = self._build_read(pedido)

        await ws_manager.broadcast_pedido(result.id, {
            "event": "pedido_cancelado",
            "pedido_id": result.id,
            "estado_anterior": estado_anterior,
            "estado_nuevo": "CANCELADO",
            "usuario_id": usuario_id,
            "motivo": motivo or "Cancelado por el cliente",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return result
