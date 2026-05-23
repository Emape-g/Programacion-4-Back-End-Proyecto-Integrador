# app/modules/rol/models.py
#
# Catálogo cerrado de roles con PK semántica (codigo) — seeds obligatorios:
# ADMIN, STOCK, PEDIDOS, CLIENT.
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.usuario_rol.models import UsuarioRol


class Rol(SQLModel, table=True):
    __tablename__ = "rol"

    codigo: str = Field(primary_key=True, max_length=20)
    nombre: str = Field(max_length=50, unique=True)
    descripcion: Optional[str] = Field(default=None)

    usuarios_link: List["UsuarioRol"] = Relationship(back_populates="rol")
