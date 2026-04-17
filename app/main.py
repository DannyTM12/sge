"""
Entry point de la aplicación FastAPI — SGE: Sistema de Gestión Escolar.
Registra todos los routers y configura el middleware de CORS y logging.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, alumnos, auth, ia, profesores

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SGE — Sistema de Gestión Escolar",
    version="0.1.0",
    description="""
SaaS multitenancy para gestión escolar orientado a prepas privadas en México.

## Roles del sistema

| Rol | Descripción |
|-----|-------------|
| **superadmin** | Gestiona instituciones a nivel plataforma (dueño del SaaS) |
| **admin** | Director o secretaría de una institución |
| **profesor** | Docente: pasa lista, sube calificaciones, agrega notas |
| **alumno** | Estudiante: solo lectura de su propia información |
""",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Logging de requests (método + path + status, nunca el body) ───────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info("%s %s → %s", request.method, request.url.path, response.status_code)
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(profesores.router)
app.include_router(alumnos.router)
app.include_router(ia.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
