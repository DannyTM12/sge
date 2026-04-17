"""
Modelos del dominio de evaluaciones.
Tablas: parciales, calificaciones, calificaciones_finales.
Nota: `inscripciones` es el nodo del alumno — calificaciones apuntan a inscripcion_id,
no a alumno_id directamente, preservando historial si el alumno cambia de grupo.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.academico import GrupoMateria, Inscripcion, Materia
    from app.models.core import Usuario


class Parcial(Base):
    __tablename__ = "parciales"

    __table_args__ = (
        UniqueConstraint("grupo_materia_id", "numero", name="uq_parcial_grupo_materia"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grupo_materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupo_materia.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fecha_apertura: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    grupo_materia: Mapped["GrupoMateria"] = relationship("GrupoMateria", back_populates="parciales")
    calificaciones: Mapped[list["Calificacion"]] = relationship("Calificacion", back_populates="parcial")


class Calificacion(Base):
    __tablename__ = "calificaciones"

    __table_args__ = (
        UniqueConstraint("inscripcion_id", "parcial_id", name="uq_calificacion"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inscripcion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inscripciones.id"), nullable=False)
    parcial_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parciales.id"), nullable=False)
    calificacion: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    registrado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    inscripcion: Mapped["Inscripcion"] = relationship("Inscripcion", back_populates="calificaciones")
    parcial: Mapped["Parcial"] = relationship("Parcial", back_populates="calificaciones")
    registrado_por_usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="calificaciones_registradas", foreign_keys=[registrado_por])


class CalificacionFinal(Base):
    __tablename__ = "calificaciones_finales"

    __table_args__ = (
        UniqueConstraint("inscripcion_id", "materia_id", name="uq_calificacion_final"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inscripcion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inscripciones.id"), nullable=False)
    materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materias.id"), nullable=False)
    calificacion_calculada: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    calificacion_final: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    fue_modificada_manualmente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    fecha_modificacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    inscripcion: Mapped["Inscripcion"] = relationship("Inscripcion", back_populates="calificaciones_finales")
    materia: Mapped["Materia"] = relationship("Materia", back_populates="calificaciones_finales")
    modificado_por_usuario: Mapped[Optional["Usuario"]] = relationship("Usuario", back_populates="calificaciones_finales_modificadas", foreign_keys=[modificado_por])
