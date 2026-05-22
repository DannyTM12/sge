# SGE — Sistema de Gestión Escolar

SaaS multitenancy para prepas privadas en México. Cubre calificaciones, asistencias, horarios e IA predictiva de riesgo de reprobación. Monetización por suscripción mensual por institución.

---

## Tabla de contenidos

- [Características](#características)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Roles del sistema](#roles-del-sistema)
- [Requisitos previos](#requisitos-previos)
- [Inicio rápido](#inicio-rápido)
- [Variables de entorno](#variables-de-entorno)
- [Estructura del proyecto](#estructura-del-proyecto)
- [API](#api)
- [Tests](#tests)
- [Convenciones de código](#convenciones-de-código)
- [Flujo de trabajo Git](#flujo-de-trabajo-git)

---

## Características

- **Multitenancy** con schema compartido — cada institución está completamente aislada
- **Gestión académica** — ciclos, grupos, materias, parciales configurables, inscripciones
- **Calificaciones** — captura por parcial, cálculo automático de promedio, override manual con auditoría
- **Asistencias** — pase de lista móvil optimizado, justificantes, resumen por materia
- **IA predictiva** — modelo XGBoost que predice riesgo de reprobación con explicabilidad SHAP
- **Boleta PDF** — generación bajo demanda con rate limiting y marca de agua
- **Auditoría append-only** — toda modificación de calificaciones y justificantes queda registrada
- **Auth robusta** — JWT + refresh tokens con rotación, rate limiting en login, logout-all

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI (Python 3.12) |
| Base de datos | PostgreSQL 16 (async via asyncpg) |
| ORM | SQLAlchemy 2.0 (`Mapped` / `mapped_column`) |
| Migraciones | Alembic |
| Caché / sesiones | Redis 7 |
| Auth | JWT (python-jose) + bcrypt |
| Validación | Pydantic v2 |
| Contenedores | Docker + Docker Compose |
| Frontend | React 19 + Vite + TypeScript + TailwindCSS |
| Estado cliente | Zustand + TanStack Query |
| IA / ML | XGBoost + scikit-learn + spaCy ES + SHAP |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                    │
│         (React 19 + Vite + TailwindCSS)             │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────┐
│                 FastAPI Backend                     │
│  /auth  /admin  /profesores  /alumnos  /ia          │
│                JWT + RBAC + Tenant isolation        │
└──────┬─────────────────────────────┬────────────────┘
       │                             │
┌──────▼──────┐              ┌───────▼──────┐
│ PostgreSQL  │              │   Redis 7    │
│  16 + RLS   │              │  (sesiones   │
│  24 tablas  │              │   y caché)   │
└─────────────┘              └──────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│              AI Worker (proceso separado)           │
│         XGBoost + spaCy ES + APScheduler            │
│   Lee datos → genera predicciones → escribe a DB    │
└─────────────────────────────────────────────────────┘
```

**Principios clave:**

- **Multitenancy** — schema compartido con `institucion_id` en todas las tablas relevantes. Cada query filtra por tenant sin excepción. PostgreSQL Row-Level Security como segunda capa.
- **Stateless** — todo el estado vive en PostgreSQL o Redis. FastAPI no guarda estado local.
- **AI Worker separado** — corre en su propio proceso con APScheduler; no bloquea requests HTTP.

---

## Roles del sistema

| Rol | Descripción |
|-----|-------------|
| `superadmin` | Gestiona instituciones a nivel plataforma (dueño del SaaS) |
| `admin` | Director o secretaría de una institución |
| `profesor` | Docente: pasa lista, sube calificaciones, agrega notas |
| `alumno` | Estudiante: solo lectura de su propia información |

---

## Requisitos previos

- Docker y Docker Compose (o Podman + podman-compose)
- Node.js 22+ (solo para desarrollo frontend fuera de Docker)
- Python 3.12+ (solo para desarrollo backend fuera de Docker)

> **Nota sobre Podman:** si usas Podman en lugar de Docker, las imágenes requieren FQDN completo (ej. `docker.io/library/postgres:16-alpine`) y `DATABASE_URL`/`REDIS_URL` deben usar `localhost` cuando los servicios corren fuera de los contenedores.

---

## Inicio rápido

```bash
# 1. Clonar el repositorio
git clone https://github.com/DannyTM12/sge.git
cd sge

# 2. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 3. Levantar todos los servicios
docker compose up -d

# 4. Aplicar migraciones
docker compose exec api alembic upgrade head

# 5. (Opcional) Cargar datos de prueba
docker compose exec api python scripts/seed.py
```

El backend queda disponible en `http://localhost:8000`  
El frontend en `http://localhost:5173`  
La documentación interactiva en `http://localhost:8000/docs`

---

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores:

```env
DATABASE_URL=postgresql+asyncpg://sge_user:sge_pass@db:5432/sge_db
REDIS_URL=redis://redis:6379/0

# Seguridad — cambia estas en producción
SECRET_KEY=cambia_esto_por_una_clave_segura_de_minimo_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

ENVIRONMENT=development

# Superadmin inicial de la plataforma
SUPERADMIN_EMAIL=admin@sge.local
SUPERADMIN_PASSWORD=cambia_esto_en_produccion
```

---

## Estructura del proyecto

```
sge/
├── app/                        # Backend FastAPI
│   ├── main.py                 # Entry point, registro de routers
│   ├── config.py               # Settings via pydantic-settings
│   ├── db/                     # Sesión async, Redis
│   ├── models/                 # 7 archivos de modelos SQLAlchemy (24 tablas)
│   ├── schemas/                # Schemas Pydantic v2 por dominio
│   ├── routers/                # auth, admin, profesores, alumnos, ia
│   ├── services/               # Lógica de negocio desacoplada
│   ├── middleware/             # JWT, RBAC, tenant isolation
│   └── utils/                  # Seguridad, auditoría
├── alembic/                    # Migraciones de base de datos
│   └── versions/
│       └── 001_initial_schema.py  # 24 tablas, 8 ENUMs
├── ai_worker/                  # Proceso independiente de IA
│   ├── main.py                 # Entry point + APScheduler
│   ├── predictor.py            # Modelo XGBoost
│   └── text_analyzer.py        # spaCy ES para notas de profesores
├── frontend/                   # React + Vite + TypeScript
│   └── src/
│       ├── api/                # Clientes HTTP por dominio
│       ├── components/         # UI + layouts por rol
│       ├── pages/              # admin/, alumno/, profesor/, auth/
│       ├── stores/             # Zustand (auth)
│       └── types/              # TypeScript interfaces
├── tests/                      # 60+ tests con mocks (sin servicios externos)
│   ├── test_auth.py
│   ├── test_admin.py
│   ├── test_profesores.py
│   └── test_alumnos.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## API

### Endpoints disponibles

| Router | Prefijo | Descripción |
|--------|---------|-------------|
| Auth | `/auth` | Login, refresh, logout, recuperación de contraseña |
| Admin | `/admin` | Ciclos, grupos, materias, usuarios, inscripciones, parciales, auditoría |
| Profesores | `/profesores` | Pase de lista, calificaciones, notas de alumnos |
| Alumnos | `/alumnos` | Dashboard, calificaciones, asistencias, horario, boleta PDF |
| IA | `/ia` | Predicciones de riesgo, alertas |

La documentación interactiva completa está disponible en `/docs` (Swagger UI) y `/redoc`.

### Decisiones de seguridad notables

- Recursos de otra institución devuelven **404**, nunca 403 (anti-enumeración)
- `alumno_id` **nunca** es parámetro en `/alumnos/*` — siempre se extrae del token
- Datos sensibles de menores (CURP, etc.) nunca aparecen en logs ni boletas (LFPDPPP)
- Rate limit en login: 5 intentos / 60 segundos por IP
- Rate limit en boleta: 10 descargas / hora por alumno

---

## Tests

Los tests usan mocks — no requieren PostgreSQL ni Redis levantados.

```bash
# Ejecutar todos los tests
docker compose exec api pytest

# Con cobertura
docker compose exec api pytest --cov=app --cov-report=term-missing

# Un módulo específico
docker compose exec api pytest tests/test_auth.py -v
```

**Cobertura actual:** 60+ tests pasando en 4 módulos (auth, admin, profesores, alumnos).

---

## Convenciones de código

- SQLAlchemy 2.0 moderno: siempre `Mapped[tipo]` y `mapped_column()`
- Toda función de acceso a BD: `async def`
- `snake_case` para todo — Python, BD, rutas de API
- Un router por dominio, prefijado en el `APIRouter`
- Nunca hardcodear secrets — todo desde `.env` vía `config.py`
- Cada modificación de calificación o justificante escribe en `auditoria`
- La tabla `auditoria` es **append-only** — nunca UPDATE ni DELETE

---

## Flujo de trabajo Git

El proyecto usa GitHub Flow con ramas de trabajo con prefijos:

| Prefijo | Cuándo usarlo |
|---------|--------------|
| `fase/` | Implementación de una fase completa del roadmap |
| `feat/` | Feature nuevo dentro de una fase |
| `fix/` | Corrección de bug |
| `chore/` | Mantenimiento sin cambio funcional |

```bash
# Crear rama y trabajar
git checkout -b feat/nombre-del-feature

# Commit con convención
git commit -m "feat(alumnos): endpoint historial de calificaciones"

# Push y PR
git push origin feat/nombre-del-feature
gh pr create --title "..." --body "X → Y tests pasando"
```

**Formato de commits:** `tipo(scope): descripción corta`  
Tipos: `feat`, `fix`, `test`, `chore`, `docs`

### Versionado del modelo de IA

Los archivos `.pkl` no se versionan en git. Nomenclatura del campo `modelo_version`:

```
sge_v{MAJOR}.{MINOR}.{YYYYMMDD}
# Ejemplo: sge_v1.0.20260416
```

---

## Notas de seguridad y legales

- Datos de menores de edad están protegidos por la **LFPDPPP** (Ley Federal de Protección de Datos Personales en Posesión de los Particulares). No se exponen datos sensibles de alumnos en logs ni respuestas de error.
- En producción: HTTPS obligatorio, HSTS habilitado, cookies `HttpOnly` para refresh tokens.
- La tabla `auditoria` recibe un insert en cada modificación de calificación o justificante.
