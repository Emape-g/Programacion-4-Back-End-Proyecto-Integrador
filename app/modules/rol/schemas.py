from typing import List, Optional

from sqlmodel import Field, SQLModel


class RolCreate(SQLModel):
    codigo: str = Field(min_length=2, max_length=20)
    nombre: str = Field(min_length=2, max_length=50)
    descripcion: Optional[str] = None


class RolUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=50)
    descripcion: Optional[str] = None


class RolPublic(SQLModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None


class RolList(SQLModel):
    data: List[RolPublic]
    total: int
