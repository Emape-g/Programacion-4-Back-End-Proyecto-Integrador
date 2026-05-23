from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.db.seed import seed_roles

# Importar todos los modelos antes de create_all para que SQLModel.metadata
# los registre y resuelva las relationships con strings.
from app.modules.categoria.models import Categoria  # noqa: F401
from app.modules.categoria.router import router as categoria_router
from app.modules.ingrediente.models import Ingrediente  # noqa: F401
from app.modules.ingrediente.router import router as ingrediente_router
from app.modules.producto.models import Producto  # noqa: F401
from app.modules.producto.router import router as producto_router
from app.modules.rol.models import Rol  # noqa: F401
from app.modules.rol.router import router as rol_router
from app.modules.usuario.models import (  # noqa: F401
    DireccionEntrega,
    RefreshToken,
    Usuario,
    UsuarioRol,
)
from app.modules.usuario.router import router as usuario_router

print(settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        seed_roles(session)
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

app.include_router(usuario_router, prefix="/auth", tags=["auth"])
app.include_router(rol_router, prefix="/roles", tags=["roles"])
app.include_router(categoria_router, prefix="/categorias", tags=["categorias"])
app.include_router(ingrediente_router, prefix="/ingredientes", tags=["ingredientes"])
app.include_router(producto_router, prefix="/productos", tags=["productos"])
