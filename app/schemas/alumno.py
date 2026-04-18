"""Schemas Pydantic para el módulo de alumno (solo lectura)."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MiCalificacionParcialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parcial_numero: int
    parcial_nombre: str | None
    calificacion: Decimal | None
    fecha_registro: datetime | None
    esta_publicada: bool


class MiMateriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    materia_id: UUID
    materia_nombre: str
    clave: str | None
    profesor_nombre: str | None
    num_parciales: int
    parciales: list[MiCalificacionParcialRead]
    calificacion_calculada: Decimal | None
    calificacion_final: Decimal | None
    fue_modificada_manualmente: bool


class MiAsistenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sesion_fecha: date
    sesion_hora_inicio: time
    materia_nombre: str
    estado: str
    justificante_descripcion: str | None


class ResumenAsistenciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    materia_id: UUID
    materia_nombre: str
    total_sesiones: int
    presentes: int
    ausentes: int
    tardanzas: int
    justificadas: int
    porcentaje_asistencia: float | None  # None cuando total_sesiones == 0


class MiHorarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dia_semana: str
    hora_inicio: time
    hora_fin: time
    materia_nombre: str
    profesor_nombre: str | None
    aula: str | None


class MiNotaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contenido: str
    autor_nombre_completo: str
    created_at: datetime


class NotificacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    titulo: str
    mensaje: str
    tipo: str
    leida: bool
    created_at: datetime


class HistorialCicloRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ciclo_id: UUID
    ciclo_nombre: str
    ciclo_tipo: str
    fecha_inicio: date
    fecha_fin: date
    materias: list[MiMateriaRead]
    promedio_ciclo: Decimal | None


class DashboardAlumnoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nombre_completo: str
    matricula: str | None
    grupo_nombre: str | None
    ciclo_nombre: str | None
    ciclo_id: UUID | None
    promedio_general: Decimal | None
    materias_en_riesgo: int
    alertas_no_leidas: int
    materias: list[MiMateriaRead]
