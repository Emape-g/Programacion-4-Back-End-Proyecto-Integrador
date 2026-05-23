from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.forma_de_pago.repository import FormaDePagoRepository


class FormaDePagoUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.forma_de_pago = FormaDePagoRepository(session)