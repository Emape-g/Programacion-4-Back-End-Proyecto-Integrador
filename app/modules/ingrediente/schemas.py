# app/modules/ingrediente/schemas.py
from typing import Optional, List
from sqlmodel import SQLModel, Field


# ── Entrada ───────────────────────────────────────────────────────────────────

class IngredienteCreate(SQLModel):
    """Body para POST /ingredientes/"""
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: bool = False


class IngredienteUpdate(SQLModel):
    """Body para PATCH /ingredientes/{id} — todos los campos opcionales."""
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class IngredientePublic(SQLModel):
    """Response model: campos expuestos al cliente."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool


class IngredienteList(SQLModel):
    """Response model paginado para GET /ingredientes/"""
    data: List[IngredientePublic]
    total: int
