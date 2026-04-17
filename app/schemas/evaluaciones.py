"""
Schemas Pydantic v2 para el dominio de evaluaciones.
Parciales, calificaciones y calificaciones finales.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class ParcialCreate(BaseModel):
    grupo_materia_id: uuid.UUID
    numero: int
    nombre: Optional[str] = None
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None


class ParcialRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    grupo_materia_id: uuid.UUID
    numero: int
    nombre: Optional[str] = None
    fecha_apertura: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    activo: bool
    created_at: Optional[datetime] = None


# ── Calificaciones parciales (para el módulo profesor) ───────────────────────

class CalificacionCreate(BaseModel):
    inscripcion_id: uuid.UUID
    parcial_id: uuid.UUID
    calificacion: Decimal

    @field_validator("calificacion")
    @classmethod
    def calificacion_en_rango(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 100:
            raise ValueError("La calificación debe estar entre 0 y 100")
        return v


class CalificacionRead(BaseModel):
    id: uuid.UUID
    inscripcion_id: uuid.UUID
    parcial_id: uuid.UUID
    calificacion: Decimal
    registrado_por: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    alumno_nombre_completo: str = ""


class CalificacionUpdate(BaseModel):
    calificacion: Decimal

    @field_validator("calificacion")
    @classmethod
    def calificacion_en_rango(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 100:
            raise ValueError("La calificación debe estar entre 0 y 100")
        return v


# ── Resumen de grupo (para mis-grupos) ────────────────────────────────────────

class MiGrupoRead(BaseModel):
    grupo_materia_id: uuid.UUID
    materia_id: uuid.UUID
    materia_nombre: str
    grupo_id: uuid.UUID
    grupo_nombre: str
    num_parciales: int


class DashboardProfesorRead(BaseModel):
    grupos_activos: int
    sesiones_hoy: int
    alumnos_totales: int


# ── Calificaciones finales (override desde admin) ─────────────────────────────

class CalificacionFinalUpdate(BaseModel):
    calificacion_final: Decimal

    @field_validator("calificacion_final")
    @classmethod
    def calificacion_en_rango(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 100:
            raise ValueError("La calificación debe estar entre 0 y 100")
        return v


class CalificacionFinalRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    inscripcion_id: uuid.UUID
    materia_id: uuid.UUID
    calificacion_calculada: Decimal
    calificacion_final: Decimal
    fue_modificada_manualmente: bool
    modificado_por: Optional[uuid.UUID] = None
    fecha_modificacion: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
