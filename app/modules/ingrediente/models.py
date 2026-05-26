# app/modules/ingrediente/models.py
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime,timezone
if TYPE_CHECKING:
    from app.modules.producto.models import ProductoIngrediente
    from app.modules.unidad_medida.models import UnidadMedida


class Ingrediente(SQLModel, table=True):

    __tablename__ = "ingrediente"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(min_length=2, max_length=100, unique=True)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)

    precio_unitario: Decimal = Field(
        max_digits=10, decimal_places=2, ge=0, nullable=False, default=0
    )
    unidad_medida_id: Optional[int] = Field(
        default=None, foreign_key="unidad_medida.id"
    )

    # Relationships
    unidad_medida: Optional["UnidadMedida"] = Relationship(
        back_populates="ingredientes"
    )
    productos_link: List["ProductoIngrediente"] = Relationship(
        back_populates="ingrediente"
    )
    
    #Auditoria
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)