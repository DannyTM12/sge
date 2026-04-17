"""
Modelos del dominio de notas y horarios.
Tablas: notas_alumno, horarios.
`notas_alumno.es_visible_alumno` es False por default — el profesor activa la visibilidad.
`horarios` es informativo: no bloquea ni valida ningún flujo.
"""

import enum
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.academico import GrupoMateria
    from app.models.core import Institucion, PerfilAlumno, Usuario


class DiaSemana(str, enum.Enum):
    lunes = "lunes"
    martes = "martes"
    miercoles = "miercoles"
    jueves = "jueves"
    viernes = "viernes"
    sabado = "sabado"


class NotaAlumno(Base):
    __tablename__ = "notas_alumno"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alumno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perfiles_alumno.id"), nullable=False)
    autor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    es_visible_alumno: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    alumno: Mapped["PerfilAlumno"] = relationship("PerfilAlumno", back_populates="notas_alumno", foreign_keys=[alumno_id])
    autor: Mapped["Usuario"] = relationship("Usuario", back_populates="notas_alumno_como_autor", foreign_keys=[autor_id])
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="notas_alumno")


class Horario(Base):
    __tablename__ = "horarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grupo_materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupo_materia.id"), nullable=False)
    dia_semana: Mapped[DiaSemana] = mapped_column(Enum(DiaSemana), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    aula: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relaciones
    grupo_materia: Mapped["GrupoMateria"] = relationship("GrupoMateria", back_populates="horarios")
