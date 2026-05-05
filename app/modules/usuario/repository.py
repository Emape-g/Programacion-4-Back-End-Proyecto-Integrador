from typing import Optional
from sqlmodel import Session, select, func

from app.core.repository import BaseRepository
from app.modules.usuario.models import Usuario


class UsuarioRepository(BaseRepository[Usuario]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    def get_by_username(self, username: str) -> Optional[Usuario]:
        return self.session.exec(
            select(Usuario).where(Usuario.username == username)
        ).first()

    def count(self) -> int:
        return self.session.exec(select(func.count(Usuario.id))).one()
