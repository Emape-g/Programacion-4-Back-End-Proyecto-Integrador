# app/modules/categoria/models.py
from datetime import datetime,timezone
# Modelo de tabla SQLModel para Categoria.
# Soporta auto-referencia (árbol de categorías padre/hijo).
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.producto.models import ProductoCategoria


class Categoria(SQLModel, table=True):
    

    __tablename__ = "categoria"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Auto-referencia: categoría padre (NULL = raíz)
    padre_id: Optional[int] = Field(
        default=None,
        foreign_key="categoria.id",
        description="Autoreferencial categoria",
    )

    nombre: str = Field(min_length=2, max_length=100, unique=True)
    descripcion: Optional[str] = Field(default=None)
    imagen_url: Optional[str] = Field(default=None) 

    # Campos de Auditoría (Audit) 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    productos_link: List["ProductoCategoria"] = Relationship(
        back_populates="categoria"
    )
    