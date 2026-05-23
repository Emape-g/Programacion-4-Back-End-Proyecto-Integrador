from typing import List, Optional, Literal
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.forma_de_pago.models import FormaDePago
from app.modules.forma_de_pago.schemas import (
    FormaDePagoCreate,
    FormaDePagoUpdate,
    FormaDePagoPublic,
    FormaDePagoList
)
from app.modules.forma_de_pago.unit_of_work import FormaDePagoUnitOfWork


class FormaDePagoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: FormaDePagoUnitOfWork, codigo: str) -> FormaDePago:
        forma = uow.forma_de_pago.get_by_id(codigo)
        if not forma:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forma de pago con codigo={codigo} no encontrada",
            )
        return forma

    def _assert_codigo_unique(self, uow: FormaDePagoUnitOfWork, codigo: str) -> None:
        if uow.forma_de_pago.get_by_id(codigo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una forma de pago con ese codigo '{codigo}'",
            )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: FormaDePagoCreate) -> FormaDePagoPublic:
        with FormaDePagoUnitOfWork(self._session) as uow:
            self._assert_codigo_unique(uow, data.codigo)
            forma = FormaDePago.model_validate(data)
            uow.forma_de_pago.add(forma)
            result = FormaDePagoPublic.model_validate(forma)
        return result

    def get_all(self, offset: int = 0,
        limit: int = 20,
        orden: Literal["asc", "desc"] = "desc",) -> FormaDePagoList:
        with FormaDePagoUnitOfWork(self._session) as uow:
            items = uow.forma_de_pago.get_all(offset=offset, limit=limit, orden=orden)
            total = uow.forma_de_pago.count()
            result = FormaDePagoList(
                data=[FormaDePagoPublic.model_validate(i) for i in items],
                total=total,
            )
        return result
    
    

    def get_habilitadas(self) -> List[FormaDePagoPublic]:
        with FormaDePagoUnitOfWork(self._session) as uow:
            items = uow.forma_de_pago.get_habilitadas()
            result = [FormaDePagoPublic.model_validate(i) for i in items]
        return result

    def get_by_codigo(self, codigo: str) -> FormaDePagoPublic:
        with FormaDePagoUnitOfWork(self._session) as uow:
            forma = self._get_or_404(uow, codigo)
            result = FormaDePagoPublic.model_validate(forma)
        return result

    def update(self, codigo: str, data: FormaDePagoUpdate) -> FormaDePagoPublic:
        with FormaDePagoUnitOfWork(self._session) as uow:
            forma = self._get_or_404(uow, codigo)
            if not forma.habilitado:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"La forma de pago '{codigo}' está deshabilitada y no puede modificarse",
                )
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(forma, field, value)
            uow.forma_de_pago.add(forma)
            result = FormaDePagoPublic.model_validate(forma)
        return result

    def delete(self, codigo: str) -> None:
        with FormaDePagoUnitOfWork(self._session) as uow:
            forma = self._get_or_404(uow, codigo)
            forma.habilitado = False
            uow.forma_de_pago.add(forma)
