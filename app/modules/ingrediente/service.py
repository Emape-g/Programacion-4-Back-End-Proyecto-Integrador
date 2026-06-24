# app/modules/ingrediente/service.py
from typing import Literal, Optional
from fastapi import HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timezone
from app.modules.ingrediente.models import Ingrediente
from app.modules.producto.models import ProductoIngrediente
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

    def _validate_unidad(
        self, uow: IngredienteUnitOfWork, unidad_medida_id: int
    ) -> None:
        if not uow.unidades.get_by_id(unidad_medida_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unidad de medida con id={unidad_medida_id} no encontrada",
            )

    def _build_public(
        self, uow: IngredienteUnitOfWork, ingrediente: Ingrediente
    ) -> IngredientePublic:
        unidad = uow.unidades.get_by_id(ingrediente.unidad_medida_id)
        if not unidad:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"El ingrediente '{ingrediente.nombre}' no tiene una unidad válida",
            )
        return IngredientePublic(
            id=ingrediente.id,
            nombre=ingrediente.nombre,
            descripcion=ingrediente.descripcion,
            es_alergeno=ingrediente.es_alergeno,
            stock_cantidad=ingrediente.stock_cantidad,
            unidad_medida_id=ingrediente.unidad_medida_id,
            unidad_nombre=unidad.nombre,
            unidad_simbolo=unidad.simbolo,
            precio_unitario=ingrediente.precio_unitario,
            created_at=ingrediente.created_at,
            updated_at=ingrediente.updated_at,
            deleted_at=ingrediente.deleted_at,
        )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: IngredienteCreate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            self._validate_unidad(uow, data.unidad_medida_id)
            ing = Ingrediente.model_validate(data)
            uow.ingredientes.add(ing)
            result = self._build_public(uow, ing)
        return result

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        nombre: Optional[str] = None,
        orden: Literal["asc", "desc"] = "desc",
    ) -> IngredienteList:
        with IngredienteUnitOfWork(self._session) as uow:
            items = uow.ingredientes.get_all(offset=offset, limit=limit, nombre=nombre, orden=orden)
            total = uow.ingredientes.count(nombre=nombre)
            result = IngredienteList(
                data=[self._build_public(uow, i) for i in items],
                total=total,
            )
        return result

    def get_by_id(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            result = self._build_public(uow, ing)
        return result

    def update(self, ingrediente_id: int, data: IngredienteUpdate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)

            if data.nombre and data.nombre != ing.nombre:
                self._assert_nombre_unique(uow, data.nombre)
            if data.unidad_medida_id is not None:
                self._validate_unidad(uow, data.unidad_medida_id)
                if data.unidad_medida_id != ing.unidad_medida_id:
                    en_uso = self._session.exec(
                        select(ProductoIngrediente).where(
                            ProductoIngrediente.ingrediente_id == ingrediente_id
                        )
                    ).first()
                    if en_uso:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                "No se puede cambiar la unidad porque el ingrediente "
                                "está asociado a uno o más productos"
                            ),
                        )

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(ing, field, value)

            ing.updated_at = datetime.now(timezone.utc)
            uow.ingredientes.add(ing)
            result = self._build_public(uow, ing)
        return result

    def delete(self, ingrediente_id: int) -> None:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            uow.ingredientes.soft_delete(ing)

    def activate(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = uow.ingredientes.get_by_id_including_deleted(ingrediente_id)
            if not ing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ingrediente con id={ingrediente_id} no encontrado",
                )
            uow.ingredientes.activate(ing)
            result = self._build_public(uow, ing)
        return result
