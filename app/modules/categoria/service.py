# app/modules/categoria/service.py
from typing import Optional
from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.categoria.models import Categoria
from app.modules.categoria.schemas import (
    CategoriaCreate,
    CategoriaPublic,
    CategoriaUpdate,
    CategoriaList,
)
from app.modules.categoria.unit_of_work import CategoriaUnitOfWork


class CategoriaService:
    """
    Capa de lógica de negocio para Categoria.

    Responsabilidades:
    - Validar unicidad de nombre
    - Validar existencia de parent_id si se provee
    - Coordinar repositorio a través del UoW
    - Levantar HTTPException cuando corresponde
    - NUNCA acceder directamente a la Session
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        """Obtiene una categoría por ID o lanza 404."""
        cat = uow.categorias.get_by_id(categoria_id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con id={categoria_id} no encontrada",
            )
        return cat

    def _assert_nombre_unique(self, uow: CategoriaUnitOfWork, nombre: str) -> None:
        """Valida que el nombre no esté en uso. Lanza 409 si existe."""
        if uow.categorias.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una categoría con el nombre '{nombre}'",
            )

    def _validate_parent(
        self, uow: CategoriaUnitOfWork, parent_id: Optional[int]
    ) -> None:
        """Valida que el parent_id exista si se provee."""
        if parent_id is not None:
            parent = uow.categorias.get_by_id(parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Categoría padre con id={parent_id} no encontrada",
                )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: CategoriaCreate) -> CategoriaPublic:
        """Crea una nueva categoría."""
        with CategoriaUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            self._validate_parent(uow, data.parent_id)
            categoria = Categoria.model_validate(data)
            uow.categorias.add(categoria)
            result = CategoriaPublic.model_validate(categoria)
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> CategoriaList:
        """Lista paginada de categorías ordenadas por orden_display."""
        with CategoriaUnitOfWork(self._session) as uow:
            items = uow.categorias.get_all_paginated(offset=offset, limit=limit)
            total = uow.categorias.count()
            result = CategoriaList(
                data=[CategoriaPublic.model_validate(c) for c in items],
                total=total,
            )
        return result

    def get_by_id(self, categoria_id: int) -> CategoriaPublic:
        """Obtiene una categoría por ID."""
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)
            result = CategoriaPublic.model_validate(cat)
        return result

    def update(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaPublic:
        """Actualización parcial de una categoría (PATCH)."""
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)

            if data.nombre and data.nombre != cat.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            if data.parent_id and data.parent_id != cat.parent_id:
                # Evitar ciclos: no puede ser su propio padre
                if data.parent_id == categoria_id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Una categoría no puede ser su propio padre",
                    )
                self._validate_parent(uow, data.parent_id)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(cat, field, value)

            uow.categorias.add(cat)
            result = CategoriaPublic.model_validate(cat)
        return result

    def delete(self, categoria_id: int) -> None:
        """Elimina físicamente una categoría."""
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)
            uow.categorias.delete(cat)
