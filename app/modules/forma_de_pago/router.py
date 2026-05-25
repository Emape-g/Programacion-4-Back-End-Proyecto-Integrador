from typing import List
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.modules.forma_de_pago.schemas import (
    FormaDePagoCreate,
    FormaDePagoUpdate,
    FormaDePagoPublic,
    FormaDePagoList,
)
from app.modules.forma_de_pago.service import FormaDePagoService

router = APIRouter()


def get_forma_de_pago_service(
    session: Session = Depends(get_session),
) -> FormaDePagoService:
    return FormaDePagoService(session)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=FormaDePagoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear forma de pago",
)
def create_forma_de_pago(
    data: FormaDePagoCreate,
    svc: FormaDePagoService = Depends(get_forma_de_pago_service),
) -> FormaDePagoPublic:
    return svc.create(data)


@router.get(
    "/",
    response_model=FormaDePagoList,
    summary="Listar todas las formas de pago (admin)",
)
def list_formas_de_pago(
    svc: FormaDePagoService = Depends(get_forma_de_pago_service),
) -> FormaDePagoList:
    return svc.get_all()


@router.get(
    "/habilitadas",
    response_model=List[FormaDePagoPublic],
    summary="Listar formas de pago habilitadas (cliente)",
)
def list_habilitadas(
    svc: FormaDePagoService = Depends(get_forma_de_pago_service),
) -> List[FormaDePagoPublic]:
    return svc.get_habilitadas()


@router.get(
    "/{codigo}",
    response_model=FormaDePagoPublic,
    summary="Obtener forma de pago por código",
)
def get_forma_de_pago(
    codigo: str,
    svc: FormaDePagoService = Depends(get_forma_de_pago_service),
) -> FormaDePagoPublic:
    return svc.get_by_codigo(codigo)


@router.patch(
    "/{codigo}",
    response_model=FormaDePagoPublic,
    summary="Actualizar forma de pago",
)
def update_forma_de_pago(
    codigo: str,
    data: FormaDePagoUpdate,
    svc: FormaDePagoService = Depends(get_forma_de_pago_service),
) -> FormaDePagoPublic:
    return svc.update(codigo, data)


@router.delete(
    "/{codigo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deshabilitar forma de pago (soft delete)",
)
def delete_forma_de_pago(
    codigo: str,
    svc: FormaDePagoService = Depends(get_forma_de_pago_service),
) -> None:
    svc.delete(codigo)
