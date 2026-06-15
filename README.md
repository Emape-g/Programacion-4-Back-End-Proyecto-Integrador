# Food Store — Backend (Programación 4)

API REST + WebSocket para gestión de pedidos de comida (FastAPI · SQLModel · PostgreSQL · MercadoPago · Cloudinary).

## Integrantes
Emanuel Perez, Andres Salattino y Martin Carcano

## Videos
- Presentación: https://drive.google.com/file/d/1nOl1DhTBzXybq94qOsG7Af9Cb7cmHvFG/view?usp=sharing
- Parcial 2: https://youtu.be/OJh-xYrT_kw

---

## Requisitos
- Python 3.11+
- PostgreSQL 14+ (corriendo local o accesible por red)
- `pip` actualizado

> Los tests usan SQLite in-memory; **no** necesitan PostgreSQL.

## Setup en máquina limpia

```bash
# 1) Clonar y entrar al backend
git clone <repo-url>
cd Programacion-4-Back-End-Proyecto-Integrador

# 2) Crear y activar venv
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# 3) Instalar dependencias
pip install -r requirements.txt

# 4) Crear la base de datos en PostgreSQL
#    (ajustar nombre/usuario a lo que pongas en el .env)
createdb foodstore_db

# 5) Variables de entorno: copiar el ejemplo y completar
cp .env.example .env
#   - Llenar POSTGRES_* con tus credenciales
#   - JWT_SECRET_KEY: poner un string aleatorio largo
#   - MP_ACCESS_TOKEN / MP_PUBLIC_KEY: credenciales de MercadoPago (sandbox o prod)
#   - MP_NOTIFICATION_URL: URL pública del webhook (ngrok/loca.lt en dev)
#   - CLOUDINARY_*: credenciales de Cloudinary

# 6) Migrar el schema (opcional: el lifespan también crea las tablas)
alembic upgrade head

# 7) Arrancar la app — el lifespan siembra catálogos/admin
uvicorn main:app --reload
```

App: <http://localhost:8000>
Swagger: <http://localhost:8000/docs>
Redoc: <http://localhost:8000/redoc>

### Usuario admin sembrado
- email: `admin@foodstore.com`
- password: `Admin1234!`

## Tests

```bash
python -m pytest
```

Los tests corren contra SQLite in-memory, así que no necesitan `.env` ni PostgreSQL.

## Endpoints clave

REST bajo `/api/v1/`:
- `auth` (`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`)
- `pedidos` (CRUD + `/{id}/estado` FSM + `/{id}/historial`)
- `pagos` (`/preferencia`, `/webhook` MercadoPago)
- `productos`, `categorias`, `ingredientes`, `unidades-medida`, `formas-de-pago`, `estados-pedido`, `roles`, `usuarios`
- `uploads` (Cloudinary), `estadisticas`

WebSocket (sin prefijo REST, autenticación por `?token=<jwt>`):
- `WS /ws/admin/pedidos` — feed de TODOS los pedidos (rol `ADMIN` o `PEDIDOS`).
- `WS /ws/pedidos/{pedido_id}` — eventos de un pedido (dueño, `ADMIN` o `PEDIDOS`).

Close codes: `4001` token faltante/inválido · `4003` sin permiso o pedido inexistente.

## Modelo de datos

Ver `food_store_erd_v7.svg` para el ERD completo (Especificación Técnica v6.0 — ERD v7).

## Estructura

```
app/
  core/        # config, auth, db, ws_manager, ws_router, rate_limit, base repository/uow
  modules/     # un paquete por dominio: router · service · unit_of_work · repository · models · schemas
  db/seed.py   # roles, unidades, formas de pago, estados, admin
main.py        # FastAPI + lifespan (create_all + seed) + include_routers
tests/         # integration/ + unit/ con TestClient
```
