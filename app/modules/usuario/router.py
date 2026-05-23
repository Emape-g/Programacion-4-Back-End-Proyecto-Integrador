# app/modules/usuario/router.py
#
# Router único del módulo Usuario. Agrupa:
#   - Sesión: /register, /login, /refresh, /logout
#   - Perfil propio: /me, /me/direcciones
#   - Administración (ADMIN): /usuarios, /usuarios/{id}
#   - Pivot UsuarioRol:      /usuarios/{id}/roles, /usuarios/{id}/roles/{cod}
#   - Direcciones:           /usuarios/{id}/direcciones, /direcciones/{id}
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.auth import get_current_user, require_role
from app.core.database import get_session
from app.modules.usuario.schemas import (
    DireccionEntregaCreate,
    DireccionEntregaList,
    DireccionEntregaPublic,
    DireccionEntregaUpdate,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UsuarioCreate,
    UsuarioList,
    UsuarioPublic,
    UsuarioRolAdd,
    UsuarioRolPublic,
    UsuarioUpdate,
)
from app.modules.usuario.service import UsuarioService

router = APIRouter()


def get_usuario_service(
    session: Session = Depends(get_session),
) -> UsuarioService:
    return UsuarioService(session)


def _actor(payload: dict) -> tuple[int, set[str]]:
    uid = payload.get("uid")
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin uid",
        )
    return int(uid), set(payload.get("roles") or [])


# ── Sesión ────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UsuarioPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de cliente (rol CLIENT auto)",
)
def register(
    data: UsuarioCreate,
    svc: UsuarioService = Depends(get_usuario_service),
) -> UsuarioPublic:
    return svc.register(data)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login — devuelve access + refresh token",
)
def login(
    data: LoginRequest,
    svc: UsuarioService = Depends(get_usuario_service),
) -> TokenPair:
    return svc.login(data)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotar tokens (revoca el viejo + emite nuevo par)",
)
def refresh(
    data: RefreshRequest,
    svc: UsuarioService = Depends(get_usuario_service),
) -> TokenPair:
    return svc.refresh(data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revocar refresh token",
)
def logout(
    data: LogoutRequest,
    _: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> Response:
    svc.logout(data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Perfil propio (/me) ───────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UsuarioPublic,
    summary="Datos del usuario logueado",
)
def me(
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> UsuarioPublic:
    uid, _ = _actor(payload)
    return svc.me(uid)


@router.patch(
    "/me",
    response_model=UsuarioPublic,
    summary="Actualizar perfil propio",
)
def update_me(
    data: UsuarioUpdate,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> UsuarioPublic:
    uid, _ = _actor(payload)
    return svc.update_me(uid, data)


@router.post(
    "/me/direcciones",
    response_model=DireccionEntregaPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear dirección propia",
)
def crear_direccion_propia(
    data: DireccionEntregaCreate,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> DireccionEntregaPublic:
    uid, _ = _actor(payload)
    return svc.crear_direccion(data, usuario_id=uid)


@router.get(
    "/me/direcciones",
    response_model=DireccionEntregaList,
    summary="Listar mis direcciones",
)
def list_direcciones_propias(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> DireccionEntregaList:
    uid, _ = _actor(payload)
    return svc.list_direcciones_by_usuario(uid, offset=offset, limit=limit)


# ── Administración de usuarios ────────────────────────────────────────────────

@router.get(
    "/usuarios",
    response_model=UsuarioList,
    summary="Listar usuarios (paginado)",
    dependencies=[Depends(require_role("ADMIN"))],
)
def list_usuarios(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    svc: UsuarioService = Depends(get_usuario_service),
) -> UsuarioList:
    return svc.get_all(offset=offset, limit=limit)


@router.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioPublic,
    summary="Obtener usuario por id (dueño o ADMIN)",
)
def get_usuario(
    usuario_id: int,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> UsuarioPublic:
    actor_uid, actor_roles = _actor(payload)
    if "ADMIN" not in actor_roles and actor_uid != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo el dueño o ADMIN pueden ver este usuario",
        )
    return svc.get_by_id(usuario_id)


@router.delete(
    "/usuarios/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Baja lógica de usuario",
    dependencies=[Depends(require_role("ADMIN"))],
)
def delete_usuario(
    usuario_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
) -> None:
    svc.soft_delete(usuario_id)


# ── Pivot UsuarioRol: /usuarios/{id}/roles ────────────────────────────────────

@router.post(
    "/usuarios/{usuario_id}/roles",
    response_model=UsuarioRolPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar rol a usuario",
)
def asignar_rol(
    usuario_id: int,
    data: UsuarioRolAdd,
    payload: dict = Depends(require_role("ADMIN")),
    svc: UsuarioService = Depends(get_usuario_service),
) -> UsuarioRolPublic:
    return svc.asignar_rol(
        usuario_id, data, asignado_por_id=payload.get("uid")
    )


@router.delete(
    "/usuarios/{usuario_id}/roles/{rol_codigo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar rol de usuario",
    dependencies=[Depends(require_role("ADMIN"))],
)
def quitar_rol(
    usuario_id: int,
    rol_codigo: str,
    svc: UsuarioService = Depends(get_usuario_service),
) -> None:
    svc.quitar_rol(usuario_id, rol_codigo)


@router.get(
    "/usuarios/{usuario_id}/roles",
    response_model=List[UsuarioRolPublic],
    summary="Listar roles de un usuario",
    dependencies=[Depends(require_role("ADMIN"))],
)
def list_roles_de_usuario(
    usuario_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
) -> List[UsuarioRolPublic]:
    return svc.list_roles_de_usuario(usuario_id)


@router.get(
    "/usuarios/asignados-por/{asignado_por_id}",
    response_model=List[UsuarioRolPublic],
    summary="Listar roles que un usuario asignó",
    dependencies=[Depends(require_role("ADMIN"))],
)
def list_roles_asignados_por(
    asignado_por_id: int,
    svc: UsuarioService = Depends(get_usuario_service),
) -> List[UsuarioRolPublic]:
    return svc.list_roles_asignados_por(asignado_por_id)


# ── Direcciones de entrega ────────────────────────────────────────────────────

@router.get(
    "/usuarios/{usuario_id}/direcciones",
    response_model=DireccionEntregaList,
    summary="Listar direcciones de un usuario (dueño o ADMIN)",
)
def list_direcciones_de_usuario(
    usuario_id: int,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> DireccionEntregaList:
    actor_uid, actor_roles = _actor(payload)
    if "ADMIN" not in actor_roles and actor_uid != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo el dueño o ADMIN pueden listar estas direcciones",
        )
    return svc.list_direcciones_by_usuario(
        usuario_id, offset=offset, limit=limit
    )


@router.get(
    "/direcciones/{direccion_id}",
    response_model=DireccionEntregaPublic,
    summary="Obtener dirección",
)
def get_direccion(
    direccion_id: int,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> DireccionEntregaPublic:
    uid, roles = _actor(payload)
    return svc.get_direccion(direccion_id, actor_uid=uid, actor_roles=roles)


@router.patch(
    "/direcciones/{direccion_id}",
    response_model=DireccionEntregaPublic,
    summary="Actualizar dirección",
)
def update_direccion(
    direccion_id: int,
    data: DireccionEntregaUpdate,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> DireccionEntregaPublic:
    uid, roles = _actor(payload)
    return svc.update_direccion(
        direccion_id, data, actor_uid=uid, actor_roles=roles
    )


@router.put(
    "/direcciones/{direccion_id}/principal",
    response_model=DireccionEntregaPublic,
    summary="Marcar dirección como principal",
)
def marcar_principal(
    direccion_id: int,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> DireccionEntregaPublic:
    uid, roles = _actor(payload)
    return svc.marcar_direccion_principal(
        direccion_id, actor_uid=uid, actor_roles=roles
    )


@router.delete(
    "/direcciones/{direccion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Baja lógica de dirección",
)
def delete_direccion(
    direccion_id: int,
    payload: dict = Depends(get_current_user),
    svc: UsuarioService = Depends(get_usuario_service),
) -> None:
    uid, roles = _actor(payload)
    svc.soft_delete_direccion(direccion_id, actor_uid=uid, actor_roles=roles)
