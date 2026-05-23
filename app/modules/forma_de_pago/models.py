from typing import Optional
from sqlmodel import SQLModel, Field


class FormaDePago(SQLModel, table=True):

    __tablename__ = "forma_de_pago"

    codigo: str = Field(max_length=20, primary_key=True)        
    descripcion: str = Field(max_length=80)                     
    habilitado: bool = Field(default=True)                      