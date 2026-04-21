# app/modules/producto/schemas.py
#
# Schemas Pydantic de entrada y salida para el módulo Producto.
# Incluye schemas para los pivots ProductoCategoria y ProductoIngrediente.
from typing import Optional, List
from sqlmodel import SQLModel, Field


# ── Schemas de pivot (entrada) ────────────────────────────────────────────────

class ProductoCategoriaAdd(SQLModel):
    """Body para asociar una categoría a un producto."""
    categoria_id: int
    es_principal: bool = False


class ProductoIngredienteAdd(SQLModel):
    """Body para asociar un ingrediente a un producto."""
    ingrediente_id: int
    es_removible: bool = False
    es_opcional: bool = False


# ── Schemas de pivot (salida) ─────────────────────────────────────────────────

class ProductoCategoriaPublic(SQLModel):
    """Muestra el vínculo producto-categoría con sus atributos."""
    categoria_id: int
    nombre_categoria: str
    es_principal: bool


class ProductoIngredientePublic(SQLModel):
    """Muestra el vínculo producto-ingrediente con sus atributos."""
    ingrediente_id: int
    nombre_ingrediente: str
    es_removible: bool
    es_opcional: bool


# ── Entrada: Producto ─────────────────────────────────────────────────────────

class ProductoCreate(SQLModel):
    """
    Body para POST /productos/
    Permite crear el producto y asociar categorías e ingredientes
    en una sola operación.
    """
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: float = Field(ge=0)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    disponible: bool = True
    # Relaciones iniciales (opcionales en la creación)
    categorias: List[ProductoCategoriaAdd] = []
    ingredientes: List[ProductoIngredienteAdd] = []


class ProductoUpdate(SQLModel):
    """Body para PATCH /productos/{id} — todos los campos opcionales."""
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Optional[float] = Field(default=None, ge=0)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None


# ── Salida: Producto ──────────────────────────────────────────────────────────

class ProductoPublic(SQLModel):
    """Response model básico: sin relaciones anidadas."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: float
    tiempo_prep_min: Optional[int] = None
    disponible: bool


class ProductoDetalle(SQLModel):
    """
    Response model completo: incluye categorías e ingredientes asociados.
    Usado en GET /productos/{id}.
    """
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: float
    tiempo_prep_min: Optional[int] = None
    disponible: bool
    categorias: List[ProductoCategoriaPublic] = []
    ingredientes: List[ProductoIngredientePublic] = []

    model_config = {"from_attributes": True}


class ProductoList(SQLModel):
    """Response model paginado para GET /productos/"""
    data: List[ProductoPublic]
    total: int
