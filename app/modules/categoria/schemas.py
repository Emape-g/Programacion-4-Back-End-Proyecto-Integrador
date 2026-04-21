# app/modules/categoria/schemas.py
#
# Schemas Pydantic de entrada y salida para el módulo Categoria.
# Separados del modelo de tabla: models.py define la DB,
# schemas.py define los contratos HTTP.
from typing import Optional, List
from sqlmodel import SQLModel, Field


# ── Entrada ───────────────────────────────────────────────────────────────────

class CategoriaCreate(SQLModel):
    """Body para POST /categorias/"""
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    orden_display: int = Field(default=0, ge=0)


class CategoriaUpdate(SQLModel):
    """Body para PATCH /categorias/{id} — todos los campos opcionales."""
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    orden_display: Optional[int] = Field(default=None, ge=0)


# ── Salida ────────────────────────────────────────────────────────────────────

class CategoriaPublic(SQLModel):
    """Response model: campos expuestos al cliente."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    orden_display: int


class CategoriaList(SQLModel):
    """Response model paginado para GET /categorias/"""
    data: List[CategoriaPublic]
    total: int
