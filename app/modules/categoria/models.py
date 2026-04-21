# app/modules/categoria/models.py
#
# Modelo de tabla SQLModel para Categoria.
# Soporta auto-referencia (árbol de categorías padre/hijo).
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.producto.models import ProductoCategoria


class Categoria(SQLModel, table=True):
    """Tabla categorias — soporta jerarquía con auto-referencia parent_id."""

    __tablename__ = "categorias"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Auto-referencia: categoría padre (NULL = raíz)
    parent_id: Optional[int] = Field(
        default=None,
        foreign_key="categorias.id",
        description="ID de la categoría padre. NULL indica categoría raíz.",
    )

    nombre: str = Field(min_length=2, max_length=100, unique=True)
    descripcion: Optional[str] = Field(default=None)
    orden_display: int = Field(default=0)

    # Relationships
    productos_link: List["ProductoCategoria"] = Relationship(
        back_populates="categoria"
    )
