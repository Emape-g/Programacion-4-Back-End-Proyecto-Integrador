from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime


class IngredienteCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: bool = False
    stock_cantidad: int = Field(default=0, ge=0)


class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)


class IngredientePublic(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool
    stock_cantidad: int = 0
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class IngredienteList(SQLModel):
    data: List[IngredientePublic]
    total: int
