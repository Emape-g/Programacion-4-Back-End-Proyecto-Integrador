from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.db.seed import (
    seed_admin_usuario,
    seed_estados_pedido,
    seed_formas_pago,
    seed_roles,
    seed_unidades_medida,
)

from app.modules.categoria.models import Categoria  # noqa: F401
from app.modules.ingrediente.models import Ingrediente  # noqa: F401
from app.modules.pedido.models import HistorialEstadoPedido, Pago  # noqa: F401
from app.modules.producto.models import Producto  # noqa: F401
from app.modules.rol.models import Rol  # noqa: F401
from app.modules.unidad_medida.models import UnidadMedida  # noqa: F401
from app.modules.usuario.models import (  # noqa: F401
    DireccionEntrega,
    RefreshToken,
    Usuario,
    UsuarioRol,
)

from app.modules.categoria.router import router as categoria_router
from app.modules.detalle_pedido.router import router as detalle_pedido_router
from app.modules.estado_pedido.router import router as estado_pedido_router
from app.modules.estadisticas.router import router as estadisticas_router
from app.modules.forma_de_pago.router import router as forma_de_pago_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.pagos.router import router as pagos_router
from app.modules.pedido.router import router as pedido_router
from app.modules.producto.router import router as producto_router
from app.modules.rol.router import router as rol_router
from app.modules.unidad_medida.router import router as unidad_medida_router
from app.modules.uploads.router import router as uploads_router
from app.modules.usuario.router import router as usuario_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        seed_roles(session)
        seed_unidades_medida(session)
        seed_formas_pago(session)
        seed_estados_pedido(session)
        seed_admin_usuario(session)
    yield


app = FastAPI(
    title="Food Store API",
    description="Sistema de Gestión de Pedidos de Comida — v6.0",
    version="6.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"withCredentials": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"

app.include_router(usuario_router,        prefix=f"{API_V1}/auth",             tags=["auth"])
app.include_router(rol_router,            prefix=f"{API_V1}/roles",            tags=["roles"])
app.include_router(unidad_medida_router,  prefix=f"{API_V1}/unidades-medida",  tags=["unidades de medida"])
app.include_router(categoria_router,      prefix=f"{API_V1}/categorias",       tags=["categorias"])
app.include_router(ingrediente_router,    prefix=f"{API_V1}/ingredientes",     tags=["ingredientes"])
app.include_router(producto_router,       prefix=f"{API_V1}/productos",        tags=["productos"])
app.include_router(forma_de_pago_router,  prefix=f"{API_V1}/formas-de-pago",   tags=["formas de pago"])
app.include_router(estado_pedido_router,  prefix=f"{API_V1}/estados-pedido",   tags=["estados de pedido"])
app.include_router(pedido_router,         prefix=f"{API_V1}/pedidos",          tags=["pedidos"])
app.include_router(detalle_pedido_router, prefix=f"{API_V1}/pedidos",          tags=["pedidos"])
app.include_router(pagos_router,          prefix=f"{API_V1}/pagos",            tags=["pagos"])
app.include_router(uploads_router,        prefix=f"{API_V1}/uploads",          tags=["uploads"])
app.include_router(estadisticas_router,   prefix=f"{API_V1}/estadisticas",     tags=["estadisticas"])
