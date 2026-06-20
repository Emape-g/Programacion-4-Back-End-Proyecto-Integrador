from decimal import Decimal

from sqlmodel import Session, select

from app.core.security import hash_password
from app.modules.categoria.models import Categoria
from app.modules.estado_pedido.models import EstadoPedido
from app.modules.forma_de_pago.models import FormaDePago
from app.modules.ingrediente.models import Ingrediente
from app.modules.producto.models import (
    Producto, ProductoCategoria, ProductoIngrediente,
)
from app.modules.rol.models import Rol
from app.modules.unidad_medida.models import UnidadMedida
from app.modules.usuario.models import DireccionEntrega, Usuario, UsuarioRol

ROLES_SEED: list[tuple[str, str, str]] = [
    ("ADMIN", "Administrador", "Acceso total sin restricciones"),
    ("STOCK", "Stockista", "Actualiza stock y disponibilidad"),
    ("PEDIDOS", "Pedidos", "Avanza estados CONFIRMADO→ENTREGADO"),
    ("CLIENT", "Cliente", "Opera solo sus propios datos"),
]


UNIDADES_MEDIDA_SEED: list[tuple[str, str, str]] = [
    ("kilogramo", "kg", "peso"),
    ("gramo", "g", "peso"),
    ("litro", "L", "volumen"),
    ("mililitro", "ml", "volumen"),
    ("unidad", "ud", "contable"),
    ("porciones", "porciones", "contable"),
]


def seed_roles(session: Session) -> None:
    changed = False
    for codigo, nombre, descripcion in ROLES_SEED:
        if not session.get(Rol, codigo):
            session.add(
                Rol(codigo=codigo, nombre=nombre, descripcion=descripcion)
            )
            changed = True
    if changed:
        session.commit()


ADMIN_SEED = {
    "email": "admin@foodstore.com",
    "nombre": "Admin",
    "apellido": "Sistema",
    "password": "Admin1234!",
}


def seed_admin_usuario(session: Session) -> None:
    existente = session.exec(
        select(Usuario).where(Usuario.email == ADMIN_SEED["email"])
    ).first()
    if existente:
        return

    usuario = Usuario(
        email=ADMIN_SEED["email"],
        nombre=ADMIN_SEED["nombre"],
        apellido=ADMIN_SEED["apellido"],
        password_hash=hash_password(ADMIN_SEED["password"]),
    )
    session.add(usuario)
    session.flush()

    session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo="ADMIN"))
    session.commit()


CLIENTE_SEED = {
    "email": "cliente@foodstore.com",
    "nombre": "Cliente",
    "apellido": "Demo",
    "celular": "+5493815550101",
    "password": "Cliente1234!",
    "direcciones": [
        {
            "alias": "Casa",
            "linea1": "Av. Sarmiento 1234",
            "linea2": "Depto 3B",
            "ciudad": "San Miguel de Tucumán",
            "provincia": "Tucumán",
            "codigo_postal": "4000",
            "es_principal": True,
        },
        {
            "alias": "Trabajo",
            "linea1": "Calle 25 de Mayo 567",
            "linea2": None,
            "ciudad": "San Miguel de Tucumán",
            "provincia": "Tucumán",
            "codigo_postal": "4000",
            "es_principal": False,
        },
    ],
}


def seed_cliente_demo(session: Session) -> None:
    existente = session.exec(
        select(Usuario).where(Usuario.email == CLIENTE_SEED["email"])
    ).first()
    if existente:
        return

    usuario = Usuario(
        email=CLIENTE_SEED["email"],
        nombre=CLIENTE_SEED["nombre"],
        apellido=CLIENTE_SEED["apellido"],
        celular=CLIENTE_SEED["celular"],
        password_hash=hash_password(CLIENTE_SEED["password"]),
    )
    session.add(usuario)
    session.flush()

    session.add(UsuarioRol(usuario_id=usuario.id, rol_codigo="CLIENT"))
    for dir_data in CLIENTE_SEED["direcciones"]:
        session.add(DireccionEntrega(usuario_id=usuario.id, **dir_data))
    session.commit()


def seed_unidades_medida(session: Session) -> None:
    changed = False
    with session.no_autoflush:
        for nombre, simbolo, tipo in UNIDADES_MEDIDA_SEED:
            existente = session.exec(
                select(UnidadMedida).where(UnidadMedida.nombre == nombre)
            ).first()
            if not existente:
                session.add(UnidadMedida(nombre=nombre, simbolo=simbolo, tipo=tipo))
                changed = True
    if changed:
        session.commit()


FORMAS_PAGO_SEED: list[tuple[str, str, bool]] = [
    ("MERCADOPAGO",   "Mercado Pago — Checkout API · CardPayment SDK", True),
    ("EFECTIVO",      "Efectivo — retiro en local (direccion_id=NULL)", True),
    ("TRANSFERENCIA", "Transferencia bancaria",                         True),
]


def seed_formas_pago(session: Session) -> None:
    changed = False
    for codigo, descripcion, habilitado in FORMAS_PAGO_SEED:
        if not session.get(FormaDePago, codigo):
            session.add(
                FormaDePago(
                    codigo=codigo,
                    descripcion=descripcion,
                    habilitado=habilitado,
                )
            )
            changed = True
    if changed:
        session.commit()


# (codigo, descripcion, orden, es_terminal) — FSM del Dominio 3
ESTADOS_PEDIDO_SEED: list[tuple[str, str, int, bool]] = [
    ("PENDIENTE",  "Pedido creado, pago pendiente", 1, False),
    ("CONFIRMADO", "Pago procesado y confirmado",   2, False),
    ("EN_PREP",    "En preparación en cocina",      3, False),
    ("ENTREGADO",  "Entrega confirmada",            4, True),
    ("CANCELADO",  "Pedido cancelado",              5, True),
]


def seed_estados_pedido(session: Session) -> None:
    changed = False
    for codigo, descripcion, orden, es_terminal in ESTADOS_PEDIDO_SEED:
        if not session.get(EstadoPedido, codigo):
            session.add(
                EstadoPedido(
                    codigo=codigo,
                    descripcion=descripcion,
                    orden=orden,
                    es_terminal=es_terminal,
                )
            )
            changed = True
    if changed:
        session.commit()


# ── Catálogo: categorías ──────────────────────────────────────────────────────

CATEGORIAS_SEED: list[tuple[str, str]] = [
    ("Pizzas", "Pizzas a la piedra"),
    ("Hamburguesas", "Hamburguesas artesanales"),
    ("Pastas", "Pastas caseras"),
    ("Empanadas", "Empanadas al horno"),
    ("Bebidas", "Bebidas frías"),
    ("Postres", "Postres caseros"),
]


def seed_categorias(session: Session) -> None:
    changed = False
    for nombre, descripcion in CATEGORIAS_SEED:
        existente = session.exec(
            select(Categoria).where(Categoria.nombre == nombre)
        ).first()
        if not existente:
            session.add(Categoria(nombre=nombre, descripcion=descripcion))
            changed = True
    if changed:
        session.commit()


# ── Catálogo: ingredientes ────────────────────────────────────────────────────
# (nombre, descripcion, es_alergeno, stock_cantidad, unidad_medida_nombre)
INGREDIENTES_SEED: list[tuple[str, str, bool, int, str]] = [
    ("Harina 000",           "Harina de trigo refinada",       True,  50000, "gramo"),
    ("Queso mozzarella",     "Queso mozzarella fileteado",     True,  20000, "gramo"),
    ("Salsa de tomate",      "Salsa de tomate casera",         False, 15000, "gramo"),
    ("Jamón cocido",         "Jamón cocido feteado",           False,  8000, "gramo"),
    ("Aceitunas verdes",     "Aceitunas verdes sin carozo",    False,  5000, "gramo"),
    ("Carne picada",         "Carne picada especial",          False, 25000, "gramo"),
    ("Pan de hamburguesa",   "Pan brioche",                    True,    200, "unidad"),
    ("Lechuga",              "Lechuga criolla",                False,  3000, "gramo"),
    ("Tomate",               "Tomate redondo",                 False, 10000, "gramo"),
    ("Cebolla",              "Cebolla blanca",                 False,  8000, "gramo"),
    ("Queso cheddar",        "Queso cheddar en fetas",         True,   6000, "gramo"),
    ("Pollo desmenuzado",    "Pollo cocido y desmenuzado",     False, 12000, "gramo"),
    ("Huevo",                "Huevo de gallina",               True,    300, "unidad"),
    ("Tapa de empanada",     "Tapa criolla para horno",        True,    500, "unidad"),
    ("Fideos tallarines",    "Fideos secos al huevo",          True,  10000, "gramo"),
    ("Coca-Cola 1.5L",       "Botella PET 1.5 litros",         False,    80, "unidad"),
    ("Agua mineral 500ml",   "Botella PET 500 ml",             False,   120, "unidad"),
    ("Dulce de leche",       "Dulce de leche repostero",       True,   4000, "gramo"),
    ("Leche",                "Leche entera",                   True,  20000, "mililitro"),
    ("Azúcar",               "Azúcar blanca",                  False, 10000, "gramo"),
]


def seed_ingredientes(session: Session) -> None:
    changed = False
    with session.no_autoflush:
        for nombre, descripcion, es_alergeno, stock, um_nombre in INGREDIENTES_SEED:
            existente = session.exec(
                select(Ingrediente).where(Ingrediente.nombre == nombre)
            ).first()
            if existente:
                continue
            um = session.exec(
                select(UnidadMedida).where(UnidadMedida.nombre == um_nombre)
            ).first()
            session.add(Ingrediente(
                nombre=nombre,
                descripcion=descripcion,
                es_alergeno=es_alergeno,
                stock_cantidad=stock,
                unidad_medida_id=um.id if um else None,
            ))
            changed = True
    if changed:
        session.commit()


# ── Catálogo: productos ───────────────────────────────────────────────────────
# Cada producto: nombre, descripcion, precio_base, stock, unidad_venta_nombre,
#                categorias[], ingredientes[(nombre, cantidad, unidad_medida_nombre, removible)]
PRODUCTOS_SEED: list[dict] = [
    {
        "nombre": "Pizza Muzzarella",
        "descripcion": "Pizza a la piedra con muzzarella y aceitunas",
        "precio_base": Decimal("5500.00"),
        "stock_cantidad": 30,
        "unidad_venta": "unidad",
        "categorias": ["Pizzas"],
        "ingredientes": [
            ("Harina 000",       Decimal("300"), "gramo", False),
            ("Salsa de tomate",  Decimal("150"), "gramo", False),
            ("Queso mozzarella", Decimal("250"), "gramo", False),
            ("Aceitunas verdes", Decimal("30"),  "gramo", True),
        ],
    },
    {
        "nombre": "Pizza Napolitana",
        "descripcion": "Muzzarella, tomate en rodajas y ajo",
        "precio_base": Decimal("6200.00"),
        "stock_cantidad": 25,
        "unidad_venta": "unidad",
        "categorias": ["Pizzas"],
        "ingredientes": [
            ("Harina 000",       Decimal("300"), "gramo", False),
            ("Salsa de tomate",  Decimal("150"), "gramo", False),
            ("Queso mozzarella", Decimal("250"), "gramo", False),
            ("Tomate",           Decimal("120"), "gramo", False),
        ],
    },
    {
        "nombre": "Pizza Jamón y Morrones",
        "descripcion": "Muzzarella, jamón cocido y morrones",
        "precio_base": Decimal("6800.00"),
        "stock_cantidad": 20,
        "unidad_venta": "unidad",
        "categorias": ["Pizzas"],
        "ingredientes": [
            ("Harina 000",       Decimal("300"), "gramo", False),
            ("Salsa de tomate",  Decimal("150"), "gramo", False),
            ("Queso mozzarella", Decimal("250"), "gramo", False),
            ("Jamón cocido",     Decimal("100"), "gramo", True),
        ],
    },
    {
        "nombre": "Hamburguesa Clásica",
        "descripcion": "Medallón de carne, lechuga, tomate y cebolla",
        "precio_base": Decimal("4800.00"),
        "stock_cantidad": 40,
        "unidad_venta": "unidad",
        "categorias": ["Hamburguesas"],
        "ingredientes": [
            ("Pan de hamburguesa", Decimal("1"),   "unidad", False),
            ("Carne picada",       Decimal("150"), "gramo",  False),
            ("Lechuga",            Decimal("20"),  "gramo",  True),
            ("Tomate",             Decimal("30"),  "gramo",  True),
            ("Cebolla",            Decimal("15"),  "gramo",  True),
        ],
    },
    {
        "nombre": "Hamburguesa Cheddar",
        "descripcion": "Doble cheddar, cebolla caramelizada",
        "precio_base": Decimal("5600.00"),
        "stock_cantidad": 35,
        "unidad_venta": "unidad",
        "categorias": ["Hamburguesas"],
        "ingredientes": [
            ("Pan de hamburguesa", Decimal("1"),   "unidad", False),
            ("Carne picada",       Decimal("180"), "gramo",  False),
            ("Queso cheddar",      Decimal("60"),  "gramo",  False),
            ("Cebolla",            Decimal("30"),  "gramo",  True),
        ],
    },
    {
        "nombre": "Fideos con Tuco",
        "descripcion": "Tallarines caseros con salsa de tomate",
        "precio_base": Decimal("4200.00"),
        "stock_cantidad": 25,
        "unidad_venta": "porciones",
        "categorias": ["Pastas"],
        "ingredientes": [
            ("Fideos tallarines", Decimal("200"), "gramo", False),
            ("Salsa de tomate",   Decimal("200"), "gramo", False),
        ],
    },
    {
        "nombre": "Empanadas de Carne (docena)",
        "descripcion": "Docena de empanadas al horno",
        "precio_base": Decimal("7200.00"),
        "stock_cantidad": 30,
        "unidad_venta": "unidad",
        "categorias": ["Empanadas"],
        "ingredientes": [
            ("Tapa de empanada", Decimal("12"),  "unidad", False),
            ("Carne picada",     Decimal("400"), "gramo",  False),
            ("Cebolla",          Decimal("150"), "gramo",  False),
            ("Huevo",            Decimal("2"),   "unidad", True),
        ],
    },
    {
        "nombre": "Empanadas de Pollo (docena)",
        "descripcion": "Docena de empanadas de pollo al horno",
        "precio_base": Decimal("7000.00"),
        "stock_cantidad": 30,
        "unidad_venta": "unidad",
        "categorias": ["Empanadas"],
        "ingredientes": [
            ("Tapa de empanada",  Decimal("12"),  "unidad", False),
            ("Pollo desmenuzado", Decimal("400"), "gramo",  False),
            ("Cebolla",           Decimal("120"), "gramo",  False),
        ],
    },
    {
        "nombre": "Coca-Cola 1.5L",
        "descripcion": "Botella de gaseosa 1.5 litros",
        "precio_base": Decimal("2800.00"),
        "stock_cantidad": 80,
        "unidad_venta": "unidad",
        "categorias": ["Bebidas"],
        "ingredientes": [
            ("Coca-Cola 1.5L", Decimal("1"), "unidad", False),
        ],
    },
    {
        "nombre": "Agua Mineral 500ml",
        "descripcion": "Botella de agua sin gas",
        "precio_base": Decimal("1200.00"),
        "stock_cantidad": 120,
        "unidad_venta": "unidad",
        "categorias": ["Bebidas"],
        "ingredientes": [
            ("Agua mineral 500ml", Decimal("1"), "unidad", False),
        ],
    },
    {
        "nombre": "Flan con Dulce de Leche",
        "descripcion": "Flan casero con dulce de leche",
        "precio_base": Decimal("2500.00"),
        "stock_cantidad": 20,
        "unidad_venta": "porciones",
        "categorias": ["Postres"],
        "ingredientes": [
            ("Huevo",          Decimal("2"),   "unidad",    False),
            ("Leche",          Decimal("200"), "mililitro", False),
            ("Azúcar",         Decimal("60"),  "gramo",     False),
            ("Dulce de leche", Decimal("80"),  "gramo",     True),
        ],
    },
]


def _unidad_id(session: Session, nombre: str) -> int | None:
    um = session.exec(
        select(UnidadMedida).where(UnidadMedida.nombre == nombre)
    ).first()
    return um.id if um else None


def seed_productos(session: Session) -> None:
    changed = False
    with session.no_autoflush:
        for data in PRODUCTOS_SEED:
            existente = session.exec(
                select(Producto).where(Producto.nombre == data["nombre"])
            ).first()
            if existente:
                continue

            producto = Producto(
                nombre=data["nombre"],
                descripcion=data["descripcion"],
                precio_base=data["precio_base"],
                stock_cantidad=data["stock_cantidad"],
                disponible=True,
                unidad_venta_id=_unidad_id(session, data["unidad_venta"]),
            )
            session.add(producto)
            session.flush()

            for cat_nombre in data["categorias"]:
                cat = session.exec(
                    select(Categoria).where(Categoria.nombre == cat_nombre)
                ).first()
                if cat:
                    session.add(ProductoCategoria(
                        producto_id=producto.id,
                        categoria_id=cat.id,
                        es_principal=True,
                    ))

            for ing_nombre, cantidad, um_nombre, removible in data["ingredientes"]:
                ing = session.exec(
                    select(Ingrediente).where(Ingrediente.nombre == ing_nombre)
                ).first()
                um_id = _unidad_id(session, um_nombre)
                if ing and um_id:
                    session.add(ProductoIngrediente(
                        producto_id=producto.id,
                        ingrediente_id=ing.id,
                        cantidad=cantidad,
                        unidad_medida_id=um_id,
                        es_removible=removible,
                    ))
            changed = True

    if changed:
        session.commit()
