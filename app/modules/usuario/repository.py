# app/modules/usuario/repository.py
#
# Repositorios de todas las entidades del dominio Usuario.
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlmodel import Session, func, select

from app.core.repository import BaseRepository
from app.modules.usuario.models import (
    DireccionEntrega,
    RefreshToken,
    Usuario,
    UsuarioRol,
)


class UsuarioRepository(BaseRepository[Usuario]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    def get_by_email(
        self, email: str, include_deleted: bool = False
    ) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.email == email.lower())
        if not include_deleted:
            stmt = stmt.where(Usuario.deleted_at.is_(None))
        return self.session.exec(stmt).first()

    def get_active_by_id(self, usuario_id: int) -> Optional[Usuario]:
        return self.session.exec(
            select(Usuario).where(
                Usuario.id == usuario_id,
                Usuario.deleted_at.is_(None),
            )
        ).first()

    def list_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> Sequence[Usuario]:
        stmt = select(Usuario)
        if not include_deleted:
            stmt = stmt.where(Usuario.deleted_at.is_(None))
        return self.session.exec(
            stmt.order_by(Usuario.id).offset(offset).limit(limit)
        ).all()

    def count(self, include_deleted: bool = False) -> int:
        stmt = select(func.count(Usuario.id))
        if not include_deleted:
            stmt = stmt.where(Usuario.deleted_at.is_(None))
        return self.session.exec(stmt).one()


class UsuarioRolRepository(BaseRepository[UsuarioRol]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, UsuarioRol)

    def get_vinculo(
        self, usuario_id: int, rol_codigo: str
    ) -> Optional[UsuarioRol]:
        return self.session.get(UsuarioRol, (usuario_id, rol_codigo))

    def get_by_usuario(self, usuario_id: int) -> Sequence[UsuarioRol]:
        return self.session.exec(
            select(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id)
        ).all()

    def get_by_asignado(self, asignado_por_id: int) -> Sequence[UsuarioRol]:
        return self.session.exec(
            select(UsuarioRol).where(
                UsuarioRol.asignado_por_id == asignado_por_id
            )
        ).all()


class DireccionEntregaRepository(BaseRepository[DireccionEntrega]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)

    def get_active_by_id(self, direccion_id: int) -> Optional[DireccionEntrega]:
        return self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.id == direccion_id,
                DireccionEntrega.deleted_at.is_(None),
            )
        ).first()

    def list_by_usuario(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> Sequence[DireccionEntrega]:
        return self.session.exec(
            select(DireccionEntrega)
            .where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.deleted_at.is_(None),
            )
            .order_by(DireccionEntrega.id)
            .offset(offset)
            .limit(limit)
        ).all()

    def count_by_usuario(self, usuario_id: int) -> int:
        return self.session.exec(
            select(func.count(DireccionEntrega.id)).where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.deleted_at.is_(None),
            )
        ).one()

    def list_principales_by_usuario(
        self, usuario_id: int, exclude_id: Optional[int] = None
    ) -> Sequence[DireccionEntrega]:
        stmt = select(DireccionEntrega).where(
            DireccionEntrega.usuario_id == usuario_id,
            DireccionEntrega.deleted_at.is_(None),
            DireccionEntrega.es_principal.is_(True),
        )
        if exclude_id is not None:
            stmt = stmt.where(DireccionEntrega.id != exclude_id)
        return self.session.exec(stmt).all()


class RefreshTokenRepository(BaseRepository[RefreshToken]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, RefreshToken)

    def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()

    def get_active_by_usuario(self, usuario_id: int) -> Sequence[RefreshToken]:
        now = datetime.now(timezone.utc)
        return self.session.exec(
            select(RefreshToken).where(
                RefreshToken.usuario_id == usuario_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        ).all()

    def revoke_all_for_usuario(self, usuario_id: int) -> int:
        active = list(self.get_active_by_usuario(usuario_id))
        now = datetime.now(timezone.utc)
        for tok in active:
            tok.revoked_at = now
            self.session.add(tok)
        self.session.flush()
        return len(active)
