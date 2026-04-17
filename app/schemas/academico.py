"""
Schemas Pydantic v2 para el dominio académico.
Ciclos, grupos, materias, grupo_materia, inscripciones y asignación de profesores.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.academico import TipoPeriodo, TurnoGrupo


# ── Ciclos escolares ──────────────────────────────────────────────────────────

class CicloEscolarCreate(BaseModel):
    nombre: str
    tipo: TipoPeriodo
    fecha_inicio: date
    fecha_fin: date


class CicloEscolarRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    institucion_id: uuid.UUID
    nombre: str
    tipo: TipoPeriodo
    fecha_inicio: date
    fecha_fin: date
    activo: bool
    created_at: Optional[datetime] = None


# ── Grupos ────────────────────────────────────────────────────────────────────

class GrupoCreate(BaseModel):
    nombre: str
    ciclo_escolar_id: uuid.UUID
    tipo_periodo: TipoPeriodo
    turno: TurnoGrupo
    capacidad_maxima: Optional[int] = None


class GrupoRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    institucion_id: uuid.UUID
    ciclo_escolar_id: uuid.UUID
    nombre: str
    tipo_periodo: TipoPeriodo
    turno: TurnoGrupo
    capacidad_maxima: Optional[int] = None
    activo: bool
    created_at: Optional[datetime] = None


class GrupoDetailRead(BaseModel):
    id: uuid.UUID
    institucion_id: uuid.UUID
    ciclo_escolar_id: uuid.UUID
    nombre: str
    tipo_periodo: TipoPeriodo
    turno: TurnoGrupo
    capacidad_maxima: Optional[int] = None
    activo: bool
    created_at: Optional[datetime] = None
    materias: list["GrupoMateriaRead"] = []
    alumnos_inscritos: list["InscripcionRead"] = []


# ── Materias ──────────────────────────────────────────────────────────────────

class MateriaCreate(BaseModel):
    nombre: str
    clave: Optional[str] = None
    creditos: Optional[int] = None


class MateriaUpdate(BaseModel):
    nombre: Optional[str] = None
    clave: Optional[str] = None
    creditos: Optional[int] = None


class MateriaRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    institucion_id: uuid.UUID
    nombre: str
    clave: Optional[str] = None
    creditos: Optional[int] = None
    activa: bool
    created_at: Optional[datetime] = None


# ── GrupoMateria ──────────────────────────────────────────────────────────────

class GrupoMateriaCreate(BaseModel):
    grupo_id: uuid.UUID
    materia_id: uuid.UUID
    num_parciales: int = 3


class GrupoMateriaRead(BaseModel):
    id: uuid.UUID
    grupo_id: uuid.UUID
    materia_id: uuid.UUID
    num_parciales: int
    created_at: Optional[datetime] = None
    materia_nombre: str = ""
    grupo_nombre: str = ""


# ── Profesor / GrupoMateria ───────────────────────────────────────────────────

class AsignarProfesorRequest(BaseModel):
    usuario_id: uuid.UUID


class ProfesorGrupoMateriaRead(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID
    grupo_materia_id: uuid.UUID
    activo: bool
    created_at: Optional[datetime] = None


# ── Inscripciones ─────────────────────────────────────────────────────────────

class InscripcionCreate(BaseModel):
    alumno_id: uuid.UUID   # ID del perfil_alumno
    grupo_id: uuid.UUID


class TransferirInscripcionRequest(BaseModel):
    nuevo_grupo_id: uuid.UUID


class InscripcionRead(BaseModel):
    id: uuid.UUID
    alumno_id: uuid.UUID
    grupo_id: uuid.UUID
    ciclo_escolar_id: uuid.UUID
    fecha_inscripcion: date
    activa: bool
    created_at: Optional[datetime] = None
    alumno_nombre_completo: str = ""
