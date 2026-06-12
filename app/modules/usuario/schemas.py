# app/modules/usuario/schemas.py
#
# Schemas Pydantic para el módulo Usuario y todas sus entidades hijas
# (UsuarioRol, DireccionEntrega) + payloads de sesión (login/refresh/logout).
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr
from sqlmodel import Field, SQLModel


# ── Usuario: entrada ──────────────────────────────────────────────────────────

class UsuarioCreate(SQLModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    celular: Optional[str] = Field(default=None, max_length=20)


class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=80)
    apellido: Optional[str] = Field(default=None, min_length=1, max_length=80)
    celular: Optional[str] = Field(default=None, max_length=20)


# ── Usuario: salida ───────────────────────────────────────────────────────────

class UsuarioPublic(SQLModel):
    id: int
    email: str
    nombre: str
    apellido: str
    celular: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    roles: List[str] = []


class UsuarioList(SQLModel):
    data: List[UsuarioPublic]
    total: int


# ── Sesión: login / refresh / logout ──────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

TokenPair = TokenResponse


class UserResponse(SQLModel):
    id: int
    nombre: str
    apellido: str
    email: str
    roles: List[str] = []
    created_at: datetime


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ── UsuarioRol: pivot Usuario ↔ Rol ───────────────────────────────────────────

class UsuarioRolAdd(SQLModel):
    rol_codigo: str = Field(min_length=2, max_length=20)
    expires_at: Optional[datetime] = None


class UsuarioRolPublic(SQLModel):
    usuario_id: int
    rol_codigo: str
    asignado_por_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


# ── DireccionEntrega: 1:N ─────────────────────────────────────────────────────

class DireccionEntregaCreate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(min_length=1)
    linea2: Optional[str] = None
    ciudad: str = Field(min_length=1, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool = False


class DireccionEntregaUpdate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: Optional[str] = Field(default=None, min_length=1)
    linea2: Optional[str] = None
    ciudad: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: Optional[bool] = None


class DireccionEntregaPublic(SQLModel):
    id: int
    usuario_id: int
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool
    created_at: datetime
    updated_at: datetime


class DireccionEntregaList(SQLModel):
    data: List[DireccionEntregaPublic]
    total: int
