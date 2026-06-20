from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.core.config import settings

# ── Importar TODOS los modelos para que SQLModel.metadata los conozca ───────
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

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
