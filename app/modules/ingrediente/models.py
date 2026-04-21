# app/modules/ingrediente/models.py
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.producto.models import ProductoIngrediente


class Ingrediente(SQLModel, table=True):
    """Tabla ingredientes — catálogo global, no duplicado por producto."""

    __tablename__ = "ingredientes"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(min_length=2, max_length=100, unique=True)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)

    # Relationship hacia la tabla pivot
    productos_link: List["ProductoIngrediente"] = Relationship(
        back_populates="ingrediente"
    )
