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

if TYPE_CHECKING:
    from app.modules.categoria.models import Categoria
    from app.modules.ingrediente.models import Ingrediente


# ── Tabla pivot: Producto ↔ Categoria ─────────────────────────────────────────

class ProductoCategoria(SQLModel, table=True):
    """
    Tabla pivot N:M entre Producto y Categoria.
    PK compuesta: (producto_id, categoria_id).
    Atributo extra: es_principal indica la categoría principal del producto.
    """

    __tablename__ = "producto_categorias"

    producto_id: int = Field(
        foreign_key="productos.id",
        primary_key=True,
    )
    categoria_id: int = Field(
        foreign_key="categorias.id",
        primary_key=True,
    )
    es_principal: bool = Field(default=False)

    # Relationships hacia los extremos
    producto: Optional["Producto"] = Relationship(back_populates="categorias_link")
    categoria: Optional["Categoria"] = Relationship(back_populates="productos_link")


# ── Tabla pivot: Producto ↔ Ingrediente ───────────────────────────────────────

class ProductoIngrediente(SQLModel, table=True):
    """
    Tabla pivot N:M entre Producto e Ingrediente.
    PK compuesta: (producto_id, ingrediente_id).
    Atributos extra:
      - es_removible: el cliente puede pedir que se retire
      - es_opcional:  no viene por defecto pero se puede agregar
    """

    __tablename__ = "producto_ingredientes"

    producto_id: int = Field(
        foreign_key="productos.id",
        primary_key=True,
    )
    ingrediente_id: int = Field(
        foreign_key="ingredientes.id",
        primary_key=True,
    )
    es_removible: bool = Field(default=False)
    es_opcional: bool = Field(default=False)

    # Relationships hacia los extremos
    producto: Optional["Producto"] = Relationship(back_populates="ingredientes_link")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="productos_link")


# ── Tabla principal: Producto ─────────────────────────────────────────────────

class Producto(SQLModel, table=True):
    """
    Tabla productos.
    Se relaciona con Categoria (N:M via ProductoCategoria)
    y con Ingrediente (N:M via ProductoIngrediente).
    """

    __tablename__ = "productos"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = Field(default=None)
    precio_base: float = Field(ge=0)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    disponible: bool = Field(default=True)

    # Relationships hacia las tablas pivot
    categorias_link: List[ProductoCategoria] = Relationship(
        back_populates="producto"
    )
    ingredientes_link: List[ProductoIngrediente] = Relationship(
        back_populates="producto"
    )
