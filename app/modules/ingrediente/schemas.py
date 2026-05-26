# app/modules/ingrediente/schemas.py
from decimal import Decimal
from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime

# ── Entrada ───────────────────────────────────────────────────────────────────

class IngredienteCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: bool = False
    precio_unitario: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    unidad_medida_id: int


class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    precio_unitario: Optional[Decimal] = Field(
        default=None, max_digits=10, decimal_places=2, ge=0
    )
    unidad_medida_id: Optional[int] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class IngredientePublic(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool
    precio_unitario: Decimal
    unidad_medida_id: Optional[int] = None
    unidad_simbolo: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    delete_at: Optional[datetime] = None


class IngredienteList(SQLModel):
    data: List[IngredientePublic]
    total: int
