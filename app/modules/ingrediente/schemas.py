# app/modules/ingrediente/schemas.py
from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime

# ── Entrada ───────────────────────────────────────────────────────────────────

class IngredienteCreate(SQLModel):
    
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: bool = False


class IngredienteUpdate(SQLModel):
    
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None


# ── Salida ────────────────────────────────────────────────────────────────────

class IngredientePublic(SQLModel):
    
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool
    created_at: datetime
    updated_at: datetime


class IngredienteList(SQLModel):
    
    
    data: List[IngredientePublic]
    total: int
