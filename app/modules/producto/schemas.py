# app/modules/producto/schemas.py
#
# Schemas Pydantic de entrada y salida para el módulo Producto.
# Incluye schemas para los pivots ProductoCategoria y ProductoIngrediente.
from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime

# ── Schemas de pivot (entrada) ───

class ProductoCategoriaAdd(SQLModel):
    
    categoria_id: int
    es_principal: bool = False


class ProductoIngredienteAdd(SQLModel):

    ingrediente_id: int
    es_removible: bool = False


# ── Schemas de pivot (salida) ───

class ProductoCategoriaPublic(SQLModel):
    
    categoria_id: int
    nombre_categoria: str
    es_principal: bool


class ProductoIngredientePublic(SQLModel):
    
    ingrediente_id: int
    nombre_ingrediente: str
    es_removible: bool
    


# ── Entrada: Producto ──

class ProductoCreate(SQLModel):
    
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: float = Field(ge=0)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    disponible: bool = True
    
    categorias: List[ProductoCategoriaAdd] = []
    ingredientes: List[ProductoIngredienteAdd] = []


class ProductoUpdate(SQLModel):
    
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=150)
    descripcion: Optional[str] = None
    precio_base: Optional[float] = Field(default=None, ge=0)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None


# ── Salida: Producto ──

class ProductoPublic(SQLModel):
    
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: float
    tiempo_prep_min: Optional[int] = None
    disponible: bool
    created_at: datetime
    updated_at: datetime


class ProductoDetalle(SQLModel):
   
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: float
    tiempo_prep_min: Optional[int] = None
    disponible: bool
    categorias: List[ProductoCategoriaPublic] = []
    ingredientes: List[ProductoIngredientePublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductoList(SQLModel):
    
    data: List[ProductoPublic]
    total: int
