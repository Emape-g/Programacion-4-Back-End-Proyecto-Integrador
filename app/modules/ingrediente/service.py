# app/modules/ingrediente/service.py
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.ingrediente.models import Ingrediente
from app.modules.ingrediente.schemas import (
    IngredienteCreate,
    IngredientePublic,
    IngredienteUpdate,
    IngredienteList,
)
from app.modules.ingrediente.unit_of_work import IngredienteUnitOfWork


class IngredienteService:
    """
    Lógica de negocio para Ingrediente.
    Valida unicidad de nombre y coordina el repositorio via UoW.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: IngredienteUnitOfWork, ingrediente_id: int) -> Ingrediente:
        ing = uow.ingredientes.get_by_id(ingrediente_id)
        if not ing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingrediente con id={ingrediente_id} no encontrado",
            )
        return ing

    def _assert_nombre_unique(
        self, uow: IngredienteUnitOfWork, nombre: str
    ) -> None:
        if uow.ingredientes.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un ingrediente con el nombre '{nombre}'",
            )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: IngredienteCreate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            ing = Ingrediente.model_validate(data)
            uow.ingredientes.add(ing)
            result = IngredientePublic.model_validate(ing)
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> IngredienteList:
        with IngredienteUnitOfWork(self._session) as uow:
            items = uow.ingredientes.get_all(offset=offset, limit=limit)
            total = uow.ingredientes.count()
            result = IngredienteList(
                data=[IngredientePublic.model_validate(i) for i in items],
                total=total,
            )
        return result

    def get_by_id(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            result = IngredientePublic.model_validate(ing)
        return result

    def update(self, ingrediente_id: int, data: IngredienteUpdate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)

            if data.nombre and data.nombre != ing.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(ing, field, value)

            uow.ingredientes.add(ing)
            result = IngredientePublic.model_validate(ing)
        return result

    def delete(self, ingrediente_id: int) -> None:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            uow.ingredientes.delete(ing)
