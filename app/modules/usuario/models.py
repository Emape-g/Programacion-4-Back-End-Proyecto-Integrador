# app/modules/usuario/models.py
#
# Contiene la entidad raíz Usuario y todas las tablas que viven en su dominio:
#   - Usuario             → tabla principal (identidad)
#   - UsuarioRol          → pivot N:M con Rol (con atributos: asignado_por, expires_at)
#   - DireccionEntrega    → 1:N propio de Usuario
#   - RefreshToken        → 1:N propio de Usuario (sesión hasheada SHA-256)
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.rol.models import Rol


# ── Tabla pivot: Usuario ↔ Rol ────────────────────────────────────────────────

class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuario_rol"

    usuario_id: int = Field(foreign_key="usuario.id", primary_key=True)
    rol_codigo: str = Field(foreign_key="rol.codigo", primary_key=True)

    asignado_por_id: Optional[int] = Field(default=None, foreign_key="usuario.id")
    expires_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    usuario: Optional["Usuario"] = Relationship(
        back_populates="roles_link",
        sa_relationship_kwargs={"foreign_keys": "[UsuarioRol.usuario_id]"},
    )
    rol: Optional["Rol"] = Relationship(back_populates="usuarios_link")


# ── 1:N propio: dirección de entrega ──────────────────────────────────────────

class DireccionEntrega(SQLModel, table=True):
    __tablename__ = "direccion_entrega"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", nullable=False, index=True)

    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(nullable=False)
    linea2: Optional[str] = Field(default=None)
    ciudad: str = Field(max_length=100, nullable=False)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)

    latitud: Optional[Decimal] = Field(
        default=None, max_digits=9, decimal_places=6
    )
    longitud: Optional[Decimal] = Field(
        default=None, max_digits=9, decimal_places=6
    )

    es_principal: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    usuario: Optional["Usuario"] = Relationship(back_populates="direcciones")


# ── 1:N propio: refresh token (hash SHA-256) ──────────────────────────────────

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, nullable=False)

    token_hash: str = Field(max_length=64, unique=True, nullable=False)
    expires_at: datetime = Field(nullable=False)
    revoked_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    usuario: Optional["Usuario"] = Relationship(back_populates="refresh_tokens")


# ── Tabla principal: Usuario ──────────────────────────────────────────────────

class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: Optional[int] = Field(default=None, primary_key=True)

    email: str = Field(max_length=254, unique=True, index=True, nullable=False)
    nombre: str = Field(max_length=80, nullable=False)
    apellido: str = Field(max_length=80, nullable=False)
    celular: Optional[str] = Field(default=None, max_length=20)

    password_hash: str = Field(max_length=60, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    roles_link: List["UsuarioRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"foreign_keys": "[UsuarioRol.usuario_id]"},
    )
    direcciones: List["DireccionEntrega"] = Relationship(back_populates="usuario")
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="usuario")
