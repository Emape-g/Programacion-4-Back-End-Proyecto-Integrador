"""ingrediente unidad y precio unitario

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
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
    op.add_column(
        "ingrediente",
        sa.Column("unidad_medida_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ingrediente",
        sa.Column(
            "precio_unitario",
            sa.Numeric(12, 4),
            nullable=False,
            server_default="0",
        ),
    )

    for nombre, unidad in UNIDADES_POR_NOMBRE.items():
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
        UPDATE ingrediente
        SET unidad_medida_id = (
            SELECT id FROM unidad_medida WHERE nombre = 'unidad'
        )
        WHERE unidad_medida_id IS NULL
        """
    )
    op.alter_column("ingrediente", "unidad_medida_id", nullable=False)
    op.create_foreign_key(
        "fk_ingrediente_unidad_medida",
        "ingrediente",
        "unidad_medida",
        ["unidad_medida_id"],
        ["id"],
    )
    op.create_index(
        "ix_ingrediente_unidad_medida_id",
        "ingrediente",
        ["unidad_medida_id"],
    )
    op.alter_column("ingrediente", "precio_unitario", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_ingrediente_unidad_medida_id", table_name="ingrediente")
    op.drop_constraint(
        "fk_ingrediente_unidad_medida", "ingrediente", type_="foreignkey"
    )
    op.drop_column("ingrediente", "precio_unitario")
    op.drop_column("ingrediente", "unidad_medida_id")
