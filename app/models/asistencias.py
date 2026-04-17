"""
Modelos del dominio de asistencias.
Tablas: sesiones_clase, asistencias, justificantes.
"""

import enum
import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.academico import GrupoMateria
    from app.models.core import Institucion, PerfilAlumno, Usuario


class EstadoAsistencia(str, enum.Enum):
    presente = "presente"
    ausente = "ausente"
    tardanza = "tardanza"
    justificada = "justificada"


class SesionClase(Base):
    __tablename__ = "sesiones_clase"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grupo_materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupo_materia.id"), nullable=False)
    profesor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    tema: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    grupo_materia: Mapped["GrupoMateria"] = relationship("GrupoMateria", back_populates="sesiones_clase")
    profesor: Mapped["Usuario"] = relationship("Usuario", back_populates="sesiones_clase_impartidas")
    asistencias: Mapped[list["Asistencia"]] = relationship("Asistencia", back_populates="sesion")


class Asistencia(Base):
    __tablename__ = "asistencias"

    __table_args__ = (
        UniqueConstraint("sesion_id", "alumno_id", name="uq_asistencia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sesion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sesiones_clase.id"), nullable=False)
    alumno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perfiles_alumno.id"), nullable=False)
    estado: Mapped[EstadoAsistencia] = mapped_column(Enum(EstadoAsistencia), nullable=False)
    registrado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    sesion: Mapped["SesionClase"] = relationship("SesionClase", back_populates="asistencias")
    alumno: Mapped["PerfilAlumno"] = relationship("PerfilAlumno", back_populates="asistencias", foreign_keys=[alumno_id])
    registrado_por_usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="asistencias_registradas", foreign_keys=[registrado_por])
    justificante: Mapped[Optional["Justificante"]] = relationship("Justificante", back_populates="asistencia", uselist=False)


class Justificante(Base):
    __tablename__ = "justificantes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alumno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perfiles_alumno.id"), nullable=False)
    asistencia_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("asistencias.id"), nullable=True)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    documento_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    fecha_justificante: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    alumno: Mapped["PerfilAlumno"] = relationship("PerfilAlumno", back_populates="justificantes", foreign_keys=[alumno_id])
    asistencia: Mapped[Optional["Asistencia"]] = relationship("Asistencia", back_populates="justificante", foreign_keys=[asistencia_id])
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="justificantes")
    registrado_por_usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="justificantes_registrados", foreign_keys=[registrado_por])
