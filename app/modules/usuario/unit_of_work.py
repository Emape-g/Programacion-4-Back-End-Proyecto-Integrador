from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.rol.repository import RolRepository
from app.modules.usuario.repository import (
    DireccionEntregaRepository,
    RefreshTokenRepository,
    UsuarioRepository,
    UsuarioRolRepository,
)


class UsuarioUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.usuario_roles = UsuarioRolRepository(session)
        self.direcciones = DireccionEntregaRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.roles = RolRepository(session)
