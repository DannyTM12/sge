"""
Modelos del dominio de estructura académica.
Tablas: ciclos_escolares, grupos, materias, grupo_materia,
        profesor_grupo_materia, inscripciones.
"""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asistencias import SesionClase
    from app.models.core import Institucion, PerfilAlumno, Usuario
    from app.models.evaluaciones import (
        Calificacion,
        CalificacionFinal,
        Parcial,
    )
    from app.models.ia import PrediccionRiesgo
    from app.models.notas import Horario


class TipoPeriodo(str, enum.Enum):
    semestral = "semestral"
    cuatrimestral = "cuatrimestral"


class TurnoGrupo(str, enum.Enum):
    matutino = "matutino"
    vespertino = "vespertino"
    mixto = "mixto"


class CicloEscolar(Base):
    __tablename__ = "ciclos_escolares"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[TipoPeriodo] = mapped_column(Enum(TipoPeriodo), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="ciclos_escolares")
    grupos: Mapped[list["Grupo"]] = relationship("Grupo", back_populates="ciclo_escolar")
    inscripciones: Mapped[list["Inscripcion"]] = relationship("Inscripcion", back_populates="ciclo_escolar")
    predicciones_riesgo: Mapped[list["PrediccionRiesgo"]] = relationship("PrediccionRiesgo", back_populates="ciclo_escolar")


class Grupo(Base):
    __tablename__ = "grupos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    ciclo_escolar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ciclos_escolares.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_periodo: Mapped[TipoPeriodo] = mapped_column(Enum(TipoPeriodo), nullable=False)
    turno: Mapped[TurnoGrupo] = mapped_column(Enum(TurnoGrupo), nullable=False)
    capacidad_maxima: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="grupos")
    ciclo_escolar: Mapped["CicloEscolar"] = relationship("CicloEscolar", back_populates="grupos")
    grupo_materias: Mapped[list["GrupoMateria"]] = relationship("GrupoMateria", back_populates="grupo")
    inscripciones: Mapped[list["Inscripcion"]] = relationship("Inscripcion", back_populates="grupo")


class Materia(Base):
    __tablename__ = "materias"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    clave: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    creditos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    grupo_materias: Mapped[list["GrupoMateria"]] = relationship("GrupoMateria", back_populates="materia")
    calificaciones_finales: Mapped[list["CalificacionFinal"]] = relationship("CalificacionFinal", back_populates="materia")


class GrupoMateria(Base):
    __tablename__ = "grupo_materia"

    __table_args__ = (
        UniqueConstraint("grupo_id", "materia_id", name="uq_grupo_materia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grupo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"), nullable=False)
    materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materias.id"), nullable=False)
    num_parciales: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    grupo: Mapped["Grupo"] = relationship("Grupo", back_populates="grupo_materias")
    materia: Mapped["Materia"] = relationship("Materia", back_populates="grupo_materias")
    profesor_grupo_materias: Mapped[list["ProfesorGrupoMateria"]] = relationship("ProfesorGrupoMateria", back_populates="grupo_materia")
    parciales: Mapped[list["Parcial"]] = relationship("Parcial", back_populates="grupo_materia")
    sesiones_clase: Mapped[list["SesionClase"]] = relationship("SesionClase", back_populates="grupo_materia")
    horarios: Mapped[list["Horario"]] = relationship("Horario", back_populates="grupo_materia")
    predicciones_riesgo: Mapped[list["PrediccionRiesgo"]] = relationship("PrediccionRiesgo", back_populates="grupo_materia")


class ProfesorGrupoMateria(Base):
    __tablename__ = "profesor_grupo_materia"

    __table_args__ = (
        UniqueConstraint("usuario_id", "grupo_materia_id", name="uq_profesor_grupo_materia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    grupo_materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupo_materia.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario")
    grupo_materia: Mapped["GrupoMateria"] = relationship("GrupoMateria", back_populates="profesor_grupo_materias")


class Inscripcion(Base):
    __tablename__ = "inscripciones"

    __table_args__ = (
        UniqueConstraint("alumno_id", "grupo_id", "ciclo_escolar_id", name="uq_inscripcion"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alumno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perfiles_alumno.id"), nullable=False)
    grupo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id"), nullable=False)
    ciclo_escolar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ciclos_escolares.id"), nullable=False)
    fecha_inscripcion: Mapped[date] = mapped_column(Date, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    alumno: Mapped["PerfilAlumno"] = relationship("PerfilAlumno", back_populates="inscripciones")
    grupo: Mapped["Grupo"] = relationship("Grupo", back_populates="inscripciones")
    ciclo_escolar: Mapped["CicloEscolar"] = relationship("CicloEscolar", back_populates="inscripciones")
    calificaciones: Mapped[list["Calificacion"]] = relationship("Calificacion", back_populates="inscripcion")
    calificaciones_finales: Mapped[list["CalificacionFinal"]] = relationship("CalificacionFinal", back_populates="inscripcion")
