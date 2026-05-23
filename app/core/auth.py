from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

_bearer = HTTPBearer()


def create_access_token(*, sub: str, uid: int, roles: Iterable[str]) -> str:
    payload: dict[str, Any] = {
        "sub": sub,
        "uid": uid,
        "roles": list(roles),
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    return decode_token(credentials.credentials)


def require_role(*codigos: str):
    required = set(codigos)

    def _checker(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    ) -> dict:
        payload = decode_token(credentials.credentials)
        user_roles = set(payload.get("roles") or [])
        if "ADMIN" in user_roles:
            return payload
        if not user_roles.intersection(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requiere alguno de los roles: {', '.join(sorted(required))}",
            )
        return payload

    return _checker


require_admin = require_role("ADMIN")
