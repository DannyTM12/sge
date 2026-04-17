# SGE — Sistema de Gestión Escolar

SaaS multitenancy para gestión escolar: calificaciones, asistencias, horarios e IA predictiva.
Orientado a prepas privadas en México. Monetización por suscripción mensual por institución.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI (Python 3.12) |
| Base de datos | PostgreSQL 16 (async via asyncpg) |
| ORM | SQLAlchemy 2.0 (`Mapped` / `mapped_column`) |
| Migraciones | Alembic |
| Caché / sesiones | Redis 7 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validación | Pydantic v2 |
| Contenedores | Docker + Docker Compose |
| Frontend | React + Vite + TailwindCSS (carpeta `/frontend`) |
| IA / ML | XGBoost + scikit-learn + spaCy ES |

---

## Arquitectura

- **Multitenancy**: schema compartido + `institucion_id` en cada tabla relevante. Cada query DEBE filtrar por `institucion_id` sin excepción.
- **Row-Level Security (RLS)** en PostgreSQL como segunda capa de seguridad.
- **Stateless**: todo el estado vive en PostgreSQL o Redis. FastAPI no guarda estado local.
- **AI Worker**: proceso separado con scheduler (APScheduler). Lee datos de alumnos y escribe predicciones a PostgreSQL. No corre en cada request HTTP.

---

## Roles del sistema

| Rol | Descripción |
|-----|-------------|
| `superadmin` | Gestiona instituciones a nivel plataforma (dueño del SaaS) |
| `admin` | Director o secretaría de una institución |
| `profesor` | Docente: pasa lista, sube calificaciones, agrega notas |
| `alumno` | Estudiante: solo lectura de su propia información |

---

## Estructura de carpetas

```
sge-backend/
├── app/
│   ├── main.py                  # FastAPI app, registro de routers
│   ├── config.py                # Settings via pydantic-settings
│   ├── db/
│   │   ├── base.py              # Base declarativa SQLAlchemy
│   │   ├── session.py           # AsyncSession factory
│   │   └── redis.py             # Redis async connection
│   ├── models/
│   │   ├── __init__.py          # Importa todos los modelos
│   │   ├── core.py              # instituciones, usuarios, perfiles_*, sesiones_usuario, tokens_recuperacion
│   │   ├── academico.py         # ciclos_escolares, grupos, materias, grupo_materia, profesor_grupo_materia, inscripciones
│   │   ├── evaluaciones.py      # parciales, calificaciones, calificaciones_finales
│   │   ├── asistencias.py       # sesiones_clase, asistencias, justificantes
│   │   ├── notas.py             # notas_alumno, horarios
│   │   ├── ia.py                # predicciones_riesgo, alertas, notificaciones
│   │   └── auditoria.py         # auditoria
│   ├── schemas/                 # Pydantic schemas (por crear, uno por dominio)
│   ├── routers/
│   │   ├── auth.py              # /auth/login, /auth/refresh, /auth/logout
│   │   ├── admin.py             # /admin/* — gestión institucional
│   │   ├── profesores.py        # /profesores/* — lista, calificaciones, notas
│   │   ├── alumnos.py           # /alumnos/* — consultas de alumno
│   │   └── ia.py                # /ia/* — predicciones y alertas
│   ├── services/                # Lógica de negocio desacoplada de los routers
│   ├── middleware/
│   │   ├── auth.py              # Validación JWT
│   │   ├── rbac.py              # Control de acceso por rol
│   │   └── tenant.py            # Tenant isolation
│   └── utils/
│       ├── security.py          # Hash de contraseñas, generación de tokens
│       └── audit.py             # Helper para insertar en tabla auditoria
├── alembic/
│   ├── env.py
│   └── versions/
├── ai_worker/
│   ├── main.py                  # Entry point del worker
│   ├── predictor.py             # Modelo XGBoost
│   └── text_analyzer.py        # spaCy para notas de profesores
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Modelo de base de datos — 24 tablas

### Dominio 1: Core / Multitenancy
```
instituciones       → id (PK), nombre, logo_url, direccion, telefono, email_contacto, activa, plan_suscripcion, created_at, updated_at
usuarios            → id (PK), institucion_id (FK), nombre, apellido_paterno, apellido_materno, email (UNIQUE), password_hash, rol ENUM, activo, ultimo_acceso, created_at, updated_at
perfiles_alumno     → id (PK), usuario_id (FK UNIQUE), matricula, fecha_nacimiento, curp, telefono_tutor, nombre_tutor, email_tutor
perfiles_profesor   → id (PK), usuario_id (FK UNIQUE), numero_empleado, especialidad, telefono
sesiones_usuario    → id (PK), usuario_id (FK), refresh_token_hash (UNIQUE), dispositivo, ip_address INET, expira_en, activa, created_at
tokens_recuperacion → id (PK), usuario_id (FK), token_hash (UNIQUE), expira_en, usado BOOL, created_at
```

### Dominio 2: Estructura académica
```
ciclos_escolares        → id (PK), institucion_id (FK), nombre, tipo ENUM('semestral','cuatrimestral'), fecha_inicio, fecha_fin, activo, created_at
grupos                  → id (PK), institucion_id (FK), ciclo_escolar_id (FK), nombre, tipo_periodo ENUM, turno ENUM('matutino','vespertino','mixto'), capacidad_maxima, activo, created_at
materias                → id (PK), institucion_id (FK), nombre, clave, creditos, activa, created_at
grupo_materia           → id (PK), grupo_id (FK), materia_id (FK), num_parciales INT DEFAULT 3, created_at — UNIQUE(grupo_id, materia_id)
profesor_grupo_materia  → id (PK), usuario_id (FK), grupo_materia_id (FK), activo, created_at — UNIQUE(usuario_id, grupo_materia_id)
inscripciones           → id (PK), alumno_id (FK), grupo_id (FK), ciclo_escolar_id (FK), fecha_inscripcion, activa, created_at — UNIQUE(alumno_id, grupo_id, ciclo_escolar_id)
```

### Dominio 3: Evaluaciones
```
parciales              → id (PK), grupo_materia_id (FK), numero INT, nombre, fecha_apertura TIMESTAMP, fecha_cierre TIMESTAMP, activo, created_at — UNIQUE(grupo_materia_id, numero)
calificaciones         → id (PK), inscripcion_id (FK), parcial_id (FK), calificacion DECIMAL(5,2), registrado_por (FK), created_at, updated_at — UNIQUE(inscripcion_id, parcial_id)
calificaciones_finales → id (PK), inscripcion_id (FK), materia_id (FK), calificacion_calculada DECIMAL(5,2), calificacion_final DECIMAL(5,2), fue_modificada_manualmente BOOL DEFAULT false, modificado_por (FK nullable), fecha_modificacion TIMESTAMP nullable, created_at, updated_at — UNIQUE(inscripcion_id, materia_id)
```

### Dominio 4: Asistencias
```
sesiones_clase → id (PK), grupo_materia_id (FK), profesor_id (FK), fecha DATE, hora_inicio TIME, hora_fin TIME, tema VARCHAR(500), created_at
asistencias    → id (PK), sesion_id (FK), alumno_id (FK), estado ENUM('presente','ausente','tardanza','justificada'), registrado_por (FK), created_at — UNIQUE(sesion_id, alumno_id)
justificantes  → id (PK), alumno_id (FK), asistencia_id (FK nullable), institucion_id (FK), descripcion TEXT, documento_url TEXT nullable, registrado_por (FK), fecha_justificante DATE, created_at
```

### Dominio 5: Notas y horarios
```
notas_alumno → id (PK), alumno_id (FK), autor_id (FK), institucion_id (FK), contenido TEXT, es_visible_alumno BOOL DEFAULT false, created_at, updated_at
horarios     → id (PK), grupo_materia_id (FK), dia_semana ENUM('lunes','martes','miercoles','jueves','viernes','sabado'), hora_inicio TIME, hora_fin TIME, aula VARCHAR(100)
```

### Dominio 6: IA y alertas
```
predicciones_riesgo → id (PK), alumno_id (FK), grupo_materia_id (FK), ciclo_escolar_id (FK), probabilidad_reprobacion DECIMAL(5,4), nivel_riesgo ENUM('bajo','medio','alto','critico'), factores JSONB, modelo_version VARCHAR(50), fecha_prediccion TIMESTAMP
alertas             → id (PK), institucion_id (FK), usuario_destino_id (FK), tipo ENUM('riesgo_reprobacion','faltas_excesivas','calificacion_baja','nota_profesor'), mensaje TEXT, leida BOOL DEFAULT false, alumno_referencia_id (FK nullable), created_at
notificaciones      → id (PK), usuario_id (FK), titulo VARCHAR(200), mensaje TEXT, tipo ENUM('info','alerta','aviso'), leida BOOL DEFAULT false, created_at
```

### Dominio 7: Auditoría
```
auditoria → id (PK), institucion_id (FK), usuario_id (FK), accion VARCHAR(100), tabla_afectada VARCHAR(100), registro_id UUID, valor_anterior JSONB nullable, valor_nuevo JSONB nullable, ip_address INET nullable, user_agent VARCHAR(500), created_at
```

---

## Decisiones de diseño — NO cambiar sin discutir

1. **UUID como PK en todas las tablas** — `default=uuid.uuid4`
2. **`grupo_materia` es la tabla pivote central** — parciales, sesiones_clase, horarios y predicciones dependen de ella
3. **`inscripciones` es el nodo del alumno** — calificaciones y asistencias apuntan a `inscripcion_id`, no a `alumno_id` directamente. Preserva historial si cambia de grupo
4. **`calificaciones_finales` guarda los dos valores** — `calificacion_calculada` (promedio automático) y `calificacion_final` (posible override del admin). Ambos siempre presentes
5. **`notas_alumno.es_visible_alumno = false` por default** — el profesor activa explícitamente la visibilidad
6. **`horarios` es informativo** — no bloquea ni valida ningún flujo
7. **`auditoria` es append-only** — nunca UPDATE ni DELETE sobre esta tabla
8. **`predicciones_riesgo.factores` es JSONB** — guarda feature importances para explicabilidad de la IA
9. **passlib 1.7.4 es incompatible con bcrypt 5.x en Python 3.13** — se usa bcrypt directamente en utils/security.py

---

## Convenciones de código

- SQLAlchemy 2.0 moderno: usar `Mapped[tipo]` y `mapped_column()` siempre
- `__tablename__` debe coincidir exactamente con los nombres definidos arriba
- Usar `relationship()` con `back_populates` en todos los modelos relacionados
- Enums de Python deben coincidir con los valores del ENUM de PostgreSQL
- Toda función de acceso a BD: `async def`
- Naming: `snake_case` para todo — Python, BD, rutas de API
- Un router por dominio, prefijado en el `APIRouter`
- Nunca hardcodear secrets — todo desde `.env` via `config.py` (pydantic-settings)
- Cada modificación de calificación o justificante debe escribir en `auditoria`

---

## Variables de entorno (`.env.example`)

```env
DATABASE_URL=postgresql+asyncpg://sge_user:sge_pass@db:5432/sge_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=cambia_esto_por_una_clave_segura_de_minimo_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
SUPERADMIN_EMAIL=admin@sge.local
SUPERADMIN_PASSWORD=cambia_esto_en_produccion
```

---

## Estado del proyecto

- [x] Requerimientos definidos y documentados
- [x] Modelo de BD diseñado — 24 tablas en 7 dominios
- [x] Arquitectura definida — FastAPI + PostgreSQL + Redis + Docker
- [x] CLAUDE.md creado
- [x] Estructura de carpetas inicializada
- [x] Modelos SQLAlchemy escritos (7 archivos)
- [x] Alembic configurado + primera migración
- [x] Docker Compose funcional
- [x] Schemas Pydantic (auth.py, usuario.py)
- [x] Middleware de auth, RBAC y tenant isolation
- [x] Router /auth (login, refresh, logout, logout-all, forgot-password, reset-password)
- [x] Router /admin (CRUD ciclos, grupos, materias, inscripciones, parciales, calificaciones, justificantes, dashboard, auditoría)
- [x] Router /profesores
- [x] Router /alumnos
- [ ] Router /ia
- [ ] AI Worker
- [ ] Frontend React

---

## Notas de seguridad y legales

- Datos de menores de edad están protegidos por **LFPDPPP** (ley mexicana). No exponer datos sensibles de alumnos en logs ni en respuestas de error.
- La tabla `auditoria` debe recibir un insert cada vez que se modifique una calificación o se agregue/modifique un justificante.
- En producción: HTTPS obligatorio, HSTS habilitado, cookies HttpOnly para refresh tokens.
