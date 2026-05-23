from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.unidad_medida.models import UnidadMedida
from app.modules.unidad_medida.schemas import (
    UnidadMedidaCreate,
    UnidadMedidaList,
    UnidadMedidaPublic,
    UnidadMedidaUpdate,
)
from app.modules.unidad_medida.unit_of_work import UnidadMedidaUnitOfWork


class UnidadMedidaService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(
        self, uow: UnidadMedidaUnitOfWork, unidad_id: int
    ) -> UnidadMedida:
        u = uow.unidades.get_by_id(unidad_id)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unidad de medida con id={unidad_id} no encontrada",
            )
        return u

    def create(self, data: UnidadMedidaCreate) -> UnidadMedidaPublic:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            if uow.unidades.get_by_nombre(data.nombre):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una unidad con nombre='{data.nombre}'",
                )
            if uow.unidades.get_by_simbolo(data.simbolo):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una unidad con simbolo='{data.simbolo}'",
                )
            unidad = UnidadMedida(**data.model_dump())
            uow.unidades.add(unidad)
            return UnidadMedidaPublic.model_validate(unidad)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        tipo: Optional[str] = None,
    ) -> UnidadMedidaList:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            items = uow.unidades.list_paginated(
                offset=offset, limit=limit, tipo=tipo
            )
            total = uow.unidades.count(tipo=tipo)
            return UnidadMedidaList(
                data=[UnidadMedidaPublic.model_validate(u) for u in items],
                total=total,
            )

    def get_by_id(self, unidad_id: int) -> UnidadMedidaPublic:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            u = self._get_or_404(uow, unidad_id)
            return UnidadMedidaPublic.model_validate(u)

    def update(
        self, unidad_id: int, data: UnidadMedidaUpdate
    ) -> UnidadMedidaPublic:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            u = self._get_or_404(uow, unidad_id)
            if data.nombre and data.nombre != u.nombre:
                if uow.unidades.get_by_nombre(data.nombre):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe una unidad con nombre='{data.nombre}'",
                    )
            if data.simbolo and data.simbolo != u.simbolo:
                if uow.unidades.get_by_simbolo(data.simbolo):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe una unidad con simbolo='{data.simbolo}'",
                    )
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(u, field, value)
            uow.unidades.add(u)
            return UnidadMedidaPublic.model_validate(u)

    def delete(self, unidad_id: int) -> None:
        with UnidadMedidaUnitOfWork(self._session) as uow:
            u = self._get_or_404(uow, unidad_id)
            uow.unidades.delete(u)
