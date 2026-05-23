from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.rol.repository import RolRepository


class RolUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.roles = RolRepository(session)
