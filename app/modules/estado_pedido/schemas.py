from typing import Optional
from sqlmodel import SQLModel, Field


class EstadoPedidoCreate(SQLModel):
    codigo: str = Field(max_length=20)
    descripcion: str = Field(max_length=80)
    orden: int = Field(ge=1)
    es_terminal: bool


class EstadoPedidoUpdate(SQLModel):
    descripcion: Optional[str] = Field(default=None, max_length=80)
    orden: Optional[int] = Field(default=None, ge=1)
    es_terminal: Optional[bool] = None


class EstadoPedidoPublic(SQLModel):
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool

