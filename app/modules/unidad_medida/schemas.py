from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlmodel import Field, SQLModel


class UnidadMedidaCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=50)
    simbolo: str = Field(min_length=1, max_length=10)
    tipo: str = Field(min_length=1, max_length=20)
    factor_base: Decimal = Field(max_digits=15, decimal_places=6, gt=0, default=1)


class UnidadMedidaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=50)
    simbolo: Optional[str] = Field(default=None, min_length=1, max_length=10)
    tipo: Optional[str] = Field(default=None, min_length=1, max_length=20)
    factor_base: Optional[Decimal] = Field(
        default=None, max_digits=15, decimal_places=6, gt=0
    )


class UnidadMedidaPublic(SQLModel):
    id: int
    nombre: str
    simbolo: str
    tipo: str
    factor_base: Decimal
    created_at: datetime


class UnidadMedidaList(SQLModel):
    data: List[UnidadMedidaPublic]
    total: int
