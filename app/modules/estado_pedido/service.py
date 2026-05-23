from typing import List
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.estado_pedido.models import EstadoPedido
from app.modules.estado_pedido.schemas import (
    EstadoPedidoCreate,
    EstadoPedidoUpdate,
    EstadoPedidoPublic,
)
from app.modules.estado_pedido.unit_of_work import EstadoPedidoUnitOfWork


class EstadoPedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: EstadoPedidoUnitOfWork, codigo: str) -> EstadoPedido:
        estado = uow.estado_pedido.get_by_id(codigo)
        if not estado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EstadoPedido con codigo='{codigo}' no encontrado",
            )
        return estado

    def _assert_codigo_unique(self, uow: EstadoPedidoUnitOfWork, codigo: str) -> None:
        if uow.estado_pedido.get_by_id(codigo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un estado con codigo '{codigo}'",
            )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: EstadoPedidoCreate) -> EstadoPedidoPublic:
        with EstadoPedidoUnitOfWork(self._session) as uow:
            self._assert_codigo_unique(uow, data.codigo)
            estado = EstadoPedido.model_validate(data)
            uow.estado_pedido.add(estado)
            result = EstadoPedidoPublic.model_validate(estado)
        return result

    def get_all(self) -> List[EstadoPedidoPublic]:
        with EstadoPedidoUnitOfWork(self._session) as uow:
            items = uow.estado_pedido.get_all_ordered()
            result = [EstadoPedidoPublic.model_validate(i) for i in items]
        return result

    def get_by_codigo(self, codigo: str) -> EstadoPedidoPublic:
        with EstadoPedidoUnitOfWork(self._session) as uow:
            estado = self._get_or_404(uow, codigo)
            result = EstadoPedidoPublic.model_validate(estado)
        return result

    def update(self, codigo: str, data: EstadoPedidoUpdate) -> EstadoPedidoPublic:
        with EstadoPedidoUnitOfWork(self._session) as uow:
            estado = self._get_or_404(uow, codigo)
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(estado, field, value)
            uow.estado_pedido.add(estado)
            result = EstadoPedidoPublic.model_validate(estado)
        return result
