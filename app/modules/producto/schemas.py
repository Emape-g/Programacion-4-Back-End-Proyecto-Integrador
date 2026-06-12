# app/modules/producto/schemas.py
#
# Schemas Pydantic de entrada y salida para el módulo Producto.
# Incluye schemas para los pivots ProductoCategoria y ProductoIngrediente.
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlmodel import Field, SQLModel


# ── Schemas de pivot (entrada) ────────────────────────────────────────────────

class ProductoCategoriaAdd(SQLModel):
    categoria_id: int
    es_principal: bool = False


class ProductoIngredienteAdd(SQLModel):
    ingrediente_id: int
    cantidad: Decimal = Field(max_digits=10, decimal_places=3, gt=0)
    unidad_medida_id: int
    es_removible: bool = False


# ── Schemas de pivot (salida) ─────────────────────────────────────────────────

class ProductoCategoriaPublic(SQLModel):
    categoria_id: int
    nombre_categoria: str
    es_principal: bool


class ProductoIngredientePublic(SQLModel):
    ingrediente_id: int
    nombre_ingrediente: str
    cantidad: Decimal
    unidad_medida_id: int
    unidad_simbolo: str
    es_removible: bool


# ── Entrada: Producto ─────────────────────────────────────────────────────────

class ProductoCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    unidad_venta_id: Optional[int] = None
    imagenes_url: List[str] = []
    stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = True

    categorias: List[ProductoCategoriaAdd] = []
    ingredientes: List[ProductoIngredienteAdd] = []


class ProductoUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Optional[Decimal] = Field(
        default=None, max_digits=10, decimal_places=2, ge=0
    )
    unidad_venta_id: Optional[int] = None
    imagenes_url: Optional[List[str]] = None
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None


# ── Salida: Producto ──────────────────────────────────────────────────────────

class ProductoPublic(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Decimal
    unidad_venta_id: Optional[int] = None
    imagenes_url: List[str] = []
    stock_cantidad: int
    disponible: bool
    categorias: List[ProductoCategoriaPublic] = []
    created_at: datetime
    updated_at: datetime


class ProductoDetalle(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Decimal
    unidad_venta_id: Optional[int] = None
    unidad_venta_simbolo: Optional[str] = None
    imagenes_url: List[str] = []
    stock_cantidad: int
    disponible: bool
    categorias: List[ProductoCategoriaPublic] = []
    ingredientes: List[ProductoIngredientePublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductoList(SQLModel):
    data: List[ProductoPublic]
    total: int


class ImagenProductoUpdate(SQLModel):
    imagenes_url: List[str]


class DisponibilidadUpdate(SQLModel):
    disponible: bool
