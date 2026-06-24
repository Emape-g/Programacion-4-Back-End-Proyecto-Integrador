"""normalizar unidades de ingredientes y recetas

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


PRECIOS_POR_NOMBRE = {
    "Harina 000": 1200.00,
    "Queso mozzarella": 8500.00,
    "Salsa de tomate": 2200.00,
    "Jamón cocido": 7500.00,
    "Aceitunas verdes": 6500.00,
    "Carne picada": 8000.00,
    "Pan de hamburguesa": 450.00,
    "Lechuga": 2000.00,
    "Tomate": 2500.00,
    "Cebolla": 1500.00,
    "Queso cheddar": 9000.00,
    "Pollo desmenuzado": 6500.00,
    "Huevo": 250.00,
    "Tapa de empanada": 120.00,
    "Fideos tallarines": 2500.00,
    "Coca-Cola 1.5L": 1800.00,
    "Agua mineral 500ml": 650.00,
    "Dulce de leche": 4500.00,
    "Leche": 1600.00,
    "Azúcar": 1300.00,
}

UNIDADES_POR_NOMBRE = {
    "Harina 000": "kilogramo",
    "Queso mozzarella": "kilogramo",
    "Salsa de tomate": "kilogramo",
    "Jamón cocido": "kilogramo",
    "Aceitunas verdes": "kilogramo",
    "Carne picada": "kilogramo",
    "Pan de hamburguesa": "unidad",
    "Lechuga": "kilogramo",
    "Tomate": "kilogramo",
    "Cebolla": "kilogramo",
    "Queso cheddar": "kilogramo",
    "Pollo desmenuzado": "kilogramo",
    "Huevo": "unidad",
    "Tapa de empanada": "unidad",
    "Fideos tallarines": "kilogramo",
    "Coca-Cola 1.5L": "unidad",
    "Agua mineral 500ml": "unidad",
    "Dulce de leche": "kilogramo",
    "Leche": "litro",
    "Azúcar": "kilogramo",
}


def upgrade() -> None:
    for nombre, unidad in UNIDADES_POR_NOMBRE.items():
        op.execute(
            sa.text(
                """
                UPDATE producto_ingrediente pi
                SET cantidad = CASE
                        WHEN origen.nombre IN ('gramo', 'mililitro')
                         AND destino.nombre IN ('kilogramo', 'litro')
                        THEN pi.cantidad / 1000
                        ELSE pi.cantidad
                    END,
                    unidad_medida_id = destino.id
                FROM ingrediente i, unidad_medida origen, unidad_medida destino
                WHERE pi.ingrediente_id = i.id
                  AND origen.id = pi.unidad_medida_id
                  AND destino.nombre = :unidad
                  AND i.nombre = :nombre
                """
            ).bindparams(nombre=nombre, unidad=unidad)
        )
        op.execute(
            sa.text(
                """
                UPDATE ingrediente
                SET unidad_medida_id = (
                    SELECT id FROM unidad_medida WHERE nombre = :unidad
                )
                WHERE nombre = :nombre
                """
            ).bindparams(nombre=nombre, unidad=unidad)
        )

    for nombre, precio in PRECIOS_POR_NOMBRE.items():
        op.execute(
            sa.text(
                "UPDATE ingrediente SET precio_unitario = :precio WHERE nombre = :nombre"
            ).bindparams(nombre=nombre, precio=precio)
        )

    op.execute(
        """
        UPDATE ingrediente i
        SET unidad_medida_id = receta.unidad_medida_id
        FROM (
            SELECT ingrediente_id, MIN(unidad_medida_id) AS unidad_medida_id
            FROM producto_ingrediente
            GROUP BY ingrediente_id
            HAVING MIN(unidad_medida_id) = MAX(unidad_medida_id)
        ) receta
        WHERE i.id = receta.ingrediente_id
          AND i.precio_unitario = 0
        """
    )


def downgrade() -> None:
    pass
