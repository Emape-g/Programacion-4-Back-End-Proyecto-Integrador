# app/modules/producto/models.py
#
# Contiene:
#   - Producto              → tabla principal
#   - ProductoCategoria     → pivot N:M entre Producto y Categoria
#   - ProductoIngrediente   → pivot N:M entre Producto e Ingrediente
#                              (con cantidad + unidad de medida)
#
# Notas del SVG:
#   - stock_cantidad y disponible son flags INDEPENDIENTES (stock=0 + disp=true
#     → badge "Sin stock"; stock>0 + disp=false → deshabilitado por operador).
#   - unidad_venta_id resuelve la ambigüedad del precio: "S/. 12.50 / kg"
#     vs. "S/. 3.00" por pieza.
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.categoria.models import Categoria
    from app.modules.ingrediente.models import Ingrediente
    from app.modules.unidad_medida.models import UnidadMedida


# ── Tabla pivot: Producto ↔ Categoria ─────────────────────────────────────────

class ProductoCategoria(SQLModel, table=True):
    __tablename__ = "producto_categoria"

    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    categoria_id: int = Field(foreign_key="categoria.id", primary_key=True)
    es_principal: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    producto: Optional["Producto"] = Relationship(back_populates="categorias_link")
    categoria: Optional["Categoria"] = Relationship(back_populates="productos_link")


# ── Tabla pivot: Producto ↔ Ingrediente ───────────────────────────────────────

class ProductoIngrediente(SQLModel, table=True):
    __tablename__ = "producto_ingrediente"

    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    ingrediente_id: int = Field(foreign_key="ingrediente.id", primary_key=True)

    cantidad: Decimal = Field(
        max_digits=10, decimal_places=3, gt=0, nullable=False
    )
    unidad_medida_id: int = Field(
        foreign_key="unidad_medida.id", nullable=False
    )
    es_removible: bool = Field(default=False, nullable=False)

    producto: Optional["Producto"] = Relationship(back_populates="ingredientes_link")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="productos_link")
    unidad_medida: Optional["UnidadMedida"] = Relationship(
        back_populates="producto_ingredientes"
    )


# ── Tabla principal: Producto ─────────────────────────────────────────────────

class Producto(SQLModel, table=True):
    __tablename__ = "producto"

    id: Optional[int] = Field(default=None, primary_key=True)

    # FK → UnidadMedida (NULL = se vende por pieza implícita)
    unidad_venta_id: Optional[int] = Field(
        default=None, foreign_key="unidad_medida.id"
    )

    nombre: str = Field(min_length=2, max_length=150, nullable=False)
    descripcion: Optional[str] = Field(default=None)
    precio_base: Decimal = Field(
        max_digits=10, decimal_places=2, ge=0, nullable=False
    )

    # PG TEXT[] — array de URLs de imágenes del producto
    imagenes_url: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
    )

    stock_cantidad: int = Field(default=0, ge=0, nullable=False)
    disponible: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    unidad_venta: Optional["UnidadMedida"] = Relationship(
        back_populates="productos_venta"
    )
    categorias_link: List[ProductoCategoria] = Relationship(back_populates="producto")
    ingredientes_link: List[ProductoIngrediente] = Relationship(
        back_populates="producto"
    )
