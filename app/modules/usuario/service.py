# app/modules/usuario/service.py
#
# Service único del dominio Usuario. Maneja:
#   - Identidad/sesión (register, login, refresh, logout, me)
#   - Administración de usuarios (list/get/soft-delete)
#   - Asignación de roles (pivot UsuarioRol)
#   - CRUD de direcciones de entrega (1:N propio)
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.auth import create_access_token
from app.core.config import settings
from app.core.security import (
    generate_refresh_token,
    hash_password,
    hash_token_sha256,
    verify_password,
)
from app.modules.usuario.models import (
    DireccionEntrega,
    RefreshToken,
    Usuario,
    UsuarioRol,
)
from app.modules.usuario.schemas import (
    DireccionEntregaCreate,
    DireccionEntregaList,
    DireccionEntregaPublic,
    DireccionEntregaUpdate,
    LoginRequest,
    TokenPair,
    UsuarioCreate,
    UsuarioList,
    UsuarioPublic,
    UsuarioRolAdd,
    UsuarioRolPublic,
    UsuarioUpdate,
)
from app.modules.usuario.unit_of_work import UsuarioUnitOfWork

CLIENT_ROLE = "CLIENT"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_public(usuario: Usuario, roles: List[str]) -> UsuarioPublic:
    return UsuarioPublic(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        celular=usuario.celular,
        created_at=usuario.created_at,
        updated_at=usuario.updated_at,
        roles=roles,
    )


class UsuarioService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _get_active_or_404(
        self, uow: UsuarioUnitOfWork, usuario_id: int
    ) -> Usuario:
        u = uow.usuarios.get_active_by_id(usuario_id)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id={usuario_id} no encontrado",
            )
        return u

    def _roles_codigos(
        self, uow: UsuarioUnitOfWork, usuario_id: int
    ) -> List[str]:
        links = uow.usuario_roles.get_by_usuario(usuario_id)
        now = _now()
        return [
            link.rol_codigo
            for link in links
            if link.expires_at is None or link.expires_at > now
        ]

    def _emit_token_pair(
        self, uow: UsuarioUnitOfWork, usuario: Usuario
    ) -> TokenPair:
        roles = self._roles_codigos(uow, usuario.id)
        access = create_access_token(
            sub=usuario.email, uid=usuario.id, roles=roles
        )
        refresh_plain = generate_refresh_token()
        refresh = RefreshToken(
            usuario_id=usuario.id,
            token_hash=hash_token_sha256(refresh_plain),
            expires_at=_now()
            + timedelta(days=settings.refresh_token_expire_days),
        )
        uow.refresh_tokens.add(refresh)
        return TokenPair(
            access_token=access,
            refresh_token=refresh_plain,
            expires_in=settings.jwt_expire_minutes * 60,
        )

    def _unset_other_principales(
        self,
        uow: UsuarioUnitOfWork,
        usuario_id: int,
        exclude_id: Optional[int] = None,
    ) -> None:
        for other in uow.direcciones.list_principales_by_usuario(
            usuario_id, exclude_id=exclude_id
        ):
            other.es_principal = False
            other.updated_at = _now()
            uow.direcciones.add(other)

    def _assert_owner_or_admin(
        self,
        target_usuario_id: int,
        actor_uid: int,
        actor_roles: set[str],
    ) -> None:
        if "ADMIN" not in actor_roles and target_usuario_id != actor_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sólo el dueño o ADMIN pueden operar este recurso",
            )

    # ── Identidad / sesión ────────────────────────────────────────────────────

    def register(self, data: UsuarioCreate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            email = data.email.lower()
            if uow.usuarios.get_by_email(email, include_deleted=True):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{email}' ya registrado",
                )
            if not uow.roles.get_by_codigo(CLIENT_ROLE):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Catálogo de roles no inicializado",
                )
            usuario = Usuario(
                email=email,
                nombre=data.nombre,
                apellido=data.apellido,
                celular=data.celular,
                password_hash=hash_password(data.password),
            )
            uow.usuarios.add(usuario)
            uow.usuario_roles.add(
                UsuarioRol(usuario_id=usuario.id, rol_codigo=CLIENT_ROLE)
            )
            return _to_public(usuario, [CLIENT_ROLE])

    def login(self, data: LoginRequest) -> TokenPair:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = uow.usuarios.get_by_email(data.email.lower())
            if not usuario or not verify_password(
                data.password, usuario.password_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas",
                )
            return self._emit_token_pair(uow, usuario)

    def refresh(self, refresh_token_plain: str) -> TokenPair:
        with UsuarioUnitOfWork(self._session) as uow:
            token_hash = hash_token_sha256(refresh_token_plain)
            stored = uow.refresh_tokens.get_by_hash(token_hash)
            now = _now()
            if (
                not stored
                or stored.revoked_at is not None
                or stored.expires_at <= now
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido o expirado",
                )
            usuario = uow.usuarios.get_active_by_id(stored.usuario_id)
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario inactivo",
                )
            stored.revoked_at = now
            uow.refresh_tokens.add(stored)
            return self._emit_token_pair(uow, usuario)

    def logout(self, refresh_token_plain: str) -> None:
        with UsuarioUnitOfWork(self._session) as uow:
            token_hash = hash_token_sha256(refresh_token_plain)
            stored = uow.refresh_tokens.get_by_hash(token_hash)
            if not stored or stored.revoked_at is not None:
                return
            stored.revoked_at = _now()
            uow.refresh_tokens.add(stored)

    # ── Perfil propio / lectura ───────────────────────────────────────────────

    def me(self, usuario_id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_active_or_404(uow, usuario_id)
            return _to_public(usuario, self._roles_codigos(uow, usuario.id))

    def update_me(self, usuario_id: int, data: UsuarioUpdate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_active_or_404(uow, usuario_id)
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(usuario, field, value)
            usuario.updated_at = _now()
            uow.usuarios.add(usuario)
            return _to_public(usuario, self._roles_codigos(uow, usuario.id))

    def get_by_id(self, usuario_id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_active_or_404(uow, usuario_id)
            return _to_public(usuario, self._roles_codigos(uow, usuario.id))

    def get_all(self, offset: int = 0, limit: int = 20) -> UsuarioList:
        with UsuarioUnitOfWork(self._session) as uow:
            items = uow.usuarios.list_paginated(offset=offset, limit=limit)
            total = uow.usuarios.count()
            data = [
                _to_public(u, self._roles_codigos(uow, u.id)) for u in items
            ]
            return UsuarioList(data=data, total=total)

    def soft_delete(self, usuario_id: int) -> None:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_active_or_404(uow, usuario_id)
            usuario.deleted_at = _now()
            uow.usuarios.add(usuario)
            uow.refresh_tokens.revoke_all_for_usuario(usuario.id)

    # ── Asignación de roles (pivot UsuarioRol) ────────────────────────────────

    def asignar_rol(
        self,
        usuario_id: int,
        data: UsuarioRolAdd,
        asignado_por_id: Optional[int],
    ) -> UsuarioRolPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            self._get_active_or_404(uow, usuario_id)
            codigo = data.rol_codigo.upper()
            if not uow.roles.get_by_codigo(codigo):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rol con codigo='{data.rol_codigo}' no encontrado",
                )
            if uow.usuario_roles.get_vinculo(usuario_id, codigo):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El usuario ya tiene asignado este rol",
                )
            link = UsuarioRol(
                usuario_id=usuario_id,
                rol_codigo=codigo,
                asignado_por_id=asignado_por_id,
                expires_at=data.expires_at,
            )
            uow.usuario_roles.add(link)
            return UsuarioRolPublic.model_validate(link)

    def quitar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        with UsuarioUnitOfWork(self._session) as uow:
            link = uow.usuario_roles.get_vinculo(usuario_id, rol_codigo.upper())
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Asignación no encontrada",
                )
            uow.usuario_roles.delete(link)

    def list_roles_de_usuario(
        self, usuario_id: int
    ) -> List[UsuarioRolPublic]:
        with UsuarioUnitOfWork(self._session) as uow:
            self._get_active_or_404(uow, usuario_id)
            items = uow.usuario_roles.get_by_usuario(usuario_id)
            return [UsuarioRolPublic.model_validate(i) for i in items]

    def list_roles_asignados_por(
        self, asignado_por_id: int
    ) -> List[UsuarioRolPublic]:
        with UsuarioUnitOfWork(self._session) as uow:
            items = uow.usuario_roles.get_by_asignado(asignado_por_id)
            return [UsuarioRolPublic.model_validate(i) for i in items]

    # ── Direcciones de entrega (1:N propio) ───────────────────────────────────

    def crear_direccion(
        self,
        data: DireccionEntregaCreate,
        usuario_id: int,
    ) -> DireccionEntregaPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            self._get_active_or_404(uow, usuario_id)
            direccion = DireccionEntrega(
                usuario_id=usuario_id, **data.model_dump()
            )
            uow.direcciones.add(direccion)
            if direccion.es_principal:
                self._unset_other_principales(
                    uow, usuario_id, exclude_id=direccion.id
                )
            return DireccionEntregaPublic.model_validate(direccion)

    def get_direccion(
        self,
        direccion_id: int,
        actor_uid: int,
        actor_roles: set[str],
    ) -> DireccionEntregaPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            d = uow.direcciones.get_active_by_id(direccion_id)
            if not d:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dirección con id={direccion_id} no encontrada",
                )
            self._assert_owner_or_admin(d.usuario_id, actor_uid, actor_roles)
            return DireccionEntregaPublic.model_validate(d)

    def list_direcciones_by_usuario(
        self,
        usuario_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> DireccionEntregaList:
        with UsuarioUnitOfWork(self._session) as uow:
            items = uow.direcciones.list_by_usuario(
                usuario_id, offset=offset, limit=limit
            )
            total = uow.direcciones.count_by_usuario(usuario_id)
            return DireccionEntregaList(
                data=[
                    DireccionEntregaPublic.model_validate(d) for d in items
                ],
                total=total,
            )

    def update_direccion(
        self,
        direccion_id: int,
        data: DireccionEntregaUpdate,
        actor_uid: int,
        actor_roles: set[str],
    ) -> DireccionEntregaPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            d = uow.direcciones.get_active_by_id(direccion_id)
            if not d:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dirección con id={direccion_id} no encontrada",
                )
            self._assert_owner_or_admin(d.usuario_id, actor_uid, actor_roles)
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(d, field, value)
            d.updated_at = _now()
            uow.direcciones.add(d)
            if d.es_principal:
                self._unset_other_principales(uow, d.usuario_id, exclude_id=d.id)
            return DireccionEntregaPublic.model_validate(d)

    def marcar_direccion_principal(
        self,
        direccion_id: int,
        actor_uid: int,
        actor_roles: set[str],
    ) -> DireccionEntregaPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            d = uow.direcciones.get_active_by_id(direccion_id)
            if not d:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dirección con id={direccion_id} no encontrada",
                )
            self._assert_owner_or_admin(d.usuario_id, actor_uid, actor_roles)
            d.es_principal = True
            d.updated_at = _now()
            uow.direcciones.add(d)
            self._unset_other_principales(uow, d.usuario_id, exclude_id=d.id)
            return DireccionEntregaPublic.model_validate(d)

    def soft_delete_direccion(
        self,
        direccion_id: int,
        actor_uid: int,
        actor_roles: set[str],
    ) -> None:
        with UsuarioUnitOfWork(self._session) as uow:
            d = uow.direcciones.get_active_by_id(direccion_id)
            if not d:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dirección con id={direccion_id} no encontrada",
                )
            self._assert_owner_or_admin(d.usuario_id, actor_uid, actor_roles)
            d.deleted_at = _now()
            d.es_principal = False
            uow.direcciones.add(d)
