from typing import Optional, List
from sqlmodel import SQLModel, Field

class FormaDePagoCreate(SQLModel):

    codigo: str =Field(max_length=20)
    descripcion: str = Field(max_length=80)
    habilitado: bool = True

class FormaDePagoUpdate(SQLModel):
    descripcion: Optional[str] = Field(max_length=80, default=None)
    habilitado: Optional[bool] = None

class FormaDePagoPublic(SQLModel):
    codigo: str
    descripcion: str
    habilitado: bool

class FormaDePagoList(SQLModel):

    data: List[FormaDePagoPublic]
    total: int
