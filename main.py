from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import create_db_and_tables
from app.modules.categoria.router import router as categoria_router
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.producto.router import router as producto_router
from app.modules.usuario.router import router as usuario_router
from app.modules.forma_de_pago.router import router as forma_de_pago_router
from app.modules.estado_pedido.router import router as estado_pedido_router
from app.modules.pedido.router import router as pedido_router
from app.modules.detalle_pedido.router import router as detalle_pedido_router
from app.core.config import settings
print(settings.DATABASE_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Catálogo de Productos API",
    description="Parcial 1 — FastAPI + SQLModel + PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuario_router, prefix="/auth", tags=["usuarios"])
app.include_router(categoria_router, prefix="/categorias", tags=["categorias"])
app.include_router(ingrediente_router, prefix="/ingredientes", tags=["ingredientes"])
app.include_router(producto_router, prefix="/productos", tags=["productos"])
app.include_router(forma_de_pago_router, prefix="/formas-de-pago", tags=["formas de pago"])
app.include_router(estado_pedido_router, prefix="/estados-pedido", tags=["estados de pedido"])
app.include_router(pedido_router, prefix="/pedidos", tags=["pedidos"])
app.include_router(detalle_pedido_router, prefix="/pedidos", tags=["pedidos"])