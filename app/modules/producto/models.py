# app/modules/producto/models.py
#
# Contiene:
#   - Producto         → tabla principal
#   - ProductoCategoria → pivot N:M entre Producto y Categoria
#   - ProductoIngrediente → pivot N:M entre Producto e Ingrediente
#
# Las tablas pivot llevan sus propios atributos (es_principal, es_removible),
# por eso se modelan como clases explícitas y no como link tables simples.
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime,timezone
if TYPE_CHECKING:
    from app.modules.categoria.models import Categoria
    from app.modules.ingrediente.models import Ingrediente


# ── Tabla pivot: Producto ↔ Categoria ─────────────────────────────────────────

class ProductoCategoria(SQLModel, table=True):
   

    __tablename__ = "producto_categoria"

    producto_id: int = Field(
        foreign_key="productos.id",
        primary_key=True,
    )
    categoria_id: int = Field(
        foreign_key="categorias.id",
        primary_key=True,
    )
    es_principal: bool = Field(default=False)
    
    # Auditoria
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationship
    producto: Optional["Producto"] = Relationship(back_populates="categorias_link")
    categoria: Optional["Categoria"] = Relationship(back_populates="productos_link")


# ── Tabla pivot: Producto ↔ Ingrediente ───

class ProductoIngrediente(SQLModel, table=True):
    
    

    __tablename__ = "producto_ingrediente"

    producto_id: int = Field(
        foreign_key="productos.id",
        primary_key=True,
    )
    ingrediente_id: int = Field(
        foreign_key="ingredientes.id",
        primary_key=True,
    )
    es_removible: bool = Field(default=False)
    

    # Relationships 
    producto: Optional["Producto"] = Relationship(back_populates="ingredientes_link")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="productos_link")


# ── Tabla principal: Producto ──

class Producto(SQLModel, table=True):
    

    __tablename__ = "producto"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = Field(default=None)
    precio_base: float = Field(ge=0)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    disponible: bool = Field(default=True)
    
    # Auditorias
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)
    
    # Relationships 
    categorias_link: List[ProductoCategoria] = Relationship(
        back_populates="producto"
    )
    ingredientes_link: List[ProductoIngrediente] = Relationship(
        back_populates="producto"
    )
