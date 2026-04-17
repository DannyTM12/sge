"""
Schemas Pydantic v2 para el dominio de asistencias.
Sesiones de clase, listas de asistencia, justificantes.
"""

import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel

from app.models.asistencias import EstadoAsistencia


# ── Sesiones de clase ─────────────────────────────────────────────────────────

class SesionClaseCreate(BaseModel):
    grupo_materia_id: uuid.UUID
    fecha: date
    hora_inicio: time
    hora_fin: time
    tema: Optional[str] = None


class SesionClaseRead(BaseModel):
    id: uuid.UUID
    grupo_materia_id: uuid.UUID
    profesor_id: uuid.UUID
    fecha: date
    hora_inicio: time
    hora_fin: time
    tema: Optional[str] = None
    created_at: Optional[datetime] = None
    materia_nombre: str = ""
    grupo_nombre: str = ""


# ── Asistencias ───────────────────────────────────────────────────────────────

class AsistenciaItem(BaseModel):
    """Un ítem de la lista de asistencia (alumno + estado)."""
    alumno_id: uuid.UUID
    estado: EstadoAsistencia


class ListaAsistenciaCreate(BaseModel):
    """Cuerpo para registrar la lista completa de asistencia de una sesión."""
    sesion_id: Optional[uuid.UUID] = None   # Redundante con la URL; el path toma precedencia
    asistencias: list[AsistenciaItem]


class AsistenciaRead(BaseModel):
    id: uuid.UUID
    sesion_id: uuid.UUID
    alumno_id: uuid.UUID
    estado: EstadoAsistencia
    registrado_por: uuid.UUID
    created_at: Optional[datetime] = None
    alumno_nombre_completo: str = ""
    justificante_id: Optional[uuid.UUID] = None


class AsistenciaUpdate(BaseModel):
    estado: EstadoAsistencia


# ── Justificantes ─────────────────────────────────────────────────────────────

class JustificanteCreate(BaseModel):
    alumno_id: uuid.UUID
    asistencia_id: Optional[uuid.UUID] = None
    descripcion: str
    documento_url: Optional[str] = None
    fecha_justificante: date


class JustificanteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    alumno_id: uuid.UUID
    asistencia_id: Optional[uuid.UUID] = None
    institucion_id: uuid.UUID
    descripcion: str
    documento_url: Optional[str] = None
    registrado_por: uuid.UUID
    fecha_justificante: date
    created_at: Optional[datetime] = None
