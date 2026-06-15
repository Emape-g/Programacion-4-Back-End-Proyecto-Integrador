"""initial baseline (ERD v7)

Revision ID: 0001
Revises:
Create Date: 2026-06-15
"""
from alembic import op
from sqlmodel import SQLModel

# Importar TODOS los modelos para que SQLModel.metadata los conozca.
from app.modules.categoria.models import Categoria  # noqa: F401
from app.modules.detalle_pedido.models import DetallePedido  # noqa: F401
from app.modules.estado_pedido.models import EstadoPedido  # noqa: F401
from app.modules.forma_de_pago.models import FormaDePago  # noqa: F401
from app.modules.ingrediente.models import Ingrediente  # noqa: F401
from app.modules.pedido.models import (  # noqa: F401
    HistorialEstadoPedido, Pago, Pedido,
)
from app.modules.producto.models import Producto  # noqa: F401
from app.modules.rol.models import Rol  # noqa: F401
from app.modules.unidad_medida.models import UnidadMedida  # noqa: F401
from app.modules.usuario.models import (  # noqa: F401
    DireccionEntrega, RefreshToken, Usuario, UsuarioRol,
)

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(op.get_bind())


def downgrade() -> None:
    SQLModel.metadata.drop_all(op.get_bind())
