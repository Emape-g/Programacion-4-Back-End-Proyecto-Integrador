from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.pedido.repository import (
    PedidoRepository,
    HistorialEstadoPedidoRepository,
    PagoRepository,
)
from app.modules.detalle_pedido.repository import DetallePedidoRepository
from app.modules.forma_de_pago.repository import FormaDePagoRepository
from app.modules.estado_pedido.repository import EstadoPedidoRepository
from app.modules.ingrediente.repository import IngredienteRepository
from app.modules.producto.repository import ProductoIngredienteRepository, ProductoRepository
from app.modules.usuario.repository import DireccionEntregaRepository


class PedidoUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos = PedidoRepository(session)
        self.detalles = DetallePedidoRepository(session)
        self.formas_de_pago = FormaDePagoRepository(session)
        self.estados = EstadoPedidoRepository(session)
        self.productos = ProductoRepository(session)
        self.producto_ingredientes = ProductoIngredienteRepository(session)
        self.ingredientes = IngredienteRepository(session)
        self.historial = HistorialEstadoPedidoRepository(session)
        self.direcciones = DireccionEntregaRepository(session)
        self.pagos = PagoRepository(session)
