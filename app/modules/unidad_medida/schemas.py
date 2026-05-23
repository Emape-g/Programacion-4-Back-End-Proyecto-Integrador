from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel


class UnidadMedidaCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=50)
    simbolo: str = Field(min_length=1, max_length=10)
    tipo: str = Field(min_length=1, max_length=20)


class UnidadMedidaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=50)
    simbolo: Optional[str] = Field(default=None, min_length=1, max_length=10)
    tipo: Optional[str] = Field(default=None, min_length=1, max_length=20)


class UnidadMedidaPublic(SQLModel):
    id: int
    nombre: str
    simbolo: str
    tipo: str
    created_at: datetime


class UnidadMedidaList(SQLModel):
    data: List[UnidadMedidaPublic]
    total: int
