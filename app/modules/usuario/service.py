from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.auth import create_access_token
from app.modules.usuario.models import Usuario
from app.modules.usuario.schemas import (
    LoginRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioPublic,
)
from app.modules.usuario.unit_of_work import UsuarioUnitOfWork

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class UsuarioService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: UsuarioUnitOfWork, usuario_id: int) -> Usuario:
        u = uow.usuarios.get_by_id(usuario_id)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id={usuario_id} no encontrado",
            )
        return u

    def create(self, data: UsuarioCreate) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            if uow.usuarios.get_by_username(data.username):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Username '{data.username}' ya existe",
                )
            user = Usuario(
                username=data.username,
                password_hash=_hash(data.password),
                rol=data.rol,
            )
            uow.usuarios.add(user)
            result = UsuarioPublic.model_validate(user)
        return result

    def login(self, data: LoginRequest) -> TokenResponse:
        with UsuarioUnitOfWork(self._session) as uow:
            user = uow.usuarios.get_by_username(data.username)
            if not user or not _verify(data.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas",
                )
            token = create_access_token({"sub": user.username, "rol": user.rol})
        return TokenResponse(access_token=token)
