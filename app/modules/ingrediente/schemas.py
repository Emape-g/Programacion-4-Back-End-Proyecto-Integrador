from decimal import Decimal
from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime


class IngredienteCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: bool = False
    stock_cantidad: Decimal = Field(default=Decimal("0.000"), max_digits=10, decimal_places=3, ge=0)
    unidad_medida_id: int = Field(gt=0)
    precio_unitario: Decimal = Field(max_digits=12, decimal_places=4, gt=0)


class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    stock_cantidad: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=3, ge=0)
    unidad_medida_id: Optional[int] = Field(default=None, gt=0)
    precio_unitario: Optional[Decimal] = Field(
        default=None, max_digits=12, decimal_places=4, gt=0
    )


class IngredientePublic(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool
    stock_cantidad: Decimal = Decimal("0.000")
    unidad_medida_id: int
    unidad_nombre: str
    unidad_simbolo: str
    precio_unitario: Decimal
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class IngredienteList(SQLModel):
    data: List[IngredientePublic]
    total: int
