from datetime import datetime
from pydantic import BaseModel
from sqlmodel import SQLModel

from app.modules.usuario.models import RolUsuario


class UsuarioCreate(SQLModel):
    username: str
    password: str
    rol: RolUsuario = RolUsuario.user


class UsuarioPublic(SQLModel):
    id: int
    username: str
    rol: RolUsuario
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
