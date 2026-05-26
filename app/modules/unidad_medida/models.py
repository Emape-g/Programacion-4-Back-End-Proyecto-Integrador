# app/modules/unidad_medida/models.py
#
# Catálogo de unidades de medida (kg, g, L, mL, u, doc, m²).
# Seeds obligatorios desde app/db/seed.py.
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ingrediente.models import Ingrediente
    from app.modules.producto.models import Producto, ProductoIngrediente


class UnidadMedida(SQLModel, table=True):
    __tablename__ = "unidad_medida"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=50, unique=True, nullable=False)
    simbolo: str = Field(max_length=10, unique=True, nullable=False)
    tipo: str = Field(max_length=20, nullable=False)
    factor_base: Decimal = Field(
        max_digits=15, decimal_places=6, gt=0, nullable=False, default=1
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    productos_venta: List["Producto"] = Relationship(back_populates="unidad_venta")
    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="unidad_medida"
    )
    ingredientes: List["Ingrediente"] = Relationship(back_populates="unidad_medida")
