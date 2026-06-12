from typing import List
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.detalle_pedido.unit_of_work import DetallePedidoUnitOfWork
from app.modules.pedido.schemas import DetallePedidoRead


class DetallePedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_pedido(self, pedido_id: int) -> List[DetallePedidoRead]:
        with DetallePedidoUnitOfWork(self._session) as uow:
            items = uow.detalles.get_by_pedido(pedido_id)
            result = [DetallePedidoRead.model_validate(i) for i in items]
        return result

    def get_item(self, pedido_id: int, producto_id: int) -> DetallePedidoRead:
        with DetallePedidoUnitOfWork(self._session) as uow:
            item = uow.detalles.get_item(pedido_id, producto_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Detalle pedido_id={pedido_id}, producto_id={producto_id} no encontrado",
                )
            result = DetallePedidoRead.model_validate(item)
        return result
