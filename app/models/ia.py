"""
Modelos del dominio de IA y alertas.
Tablas: predicciones_riesgo, alertas, notificaciones.
`predicciones_riesgo.factores` es JSONB para guardar feature importances del modelo.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.academico import CicloEscolar, GrupoMateria
    from app.models.core import Institucion, PerfilAlumno, Usuario


class NivelRiesgo(str, enum.Enum):
    bajo = "bajo"
    medio = "medio"
    alto = "alto"
    critico = "critico"


class TipoAlerta(str, enum.Enum):
    riesgo_reprobacion = "riesgo_reprobacion"
    faltas_excesivas = "faltas_excesivas"
    calificacion_baja = "calificacion_baja"
    nota_profesor = "nota_profesor"


class TipoNotificacion(str, enum.Enum):
    info = "info"
    alerta = "alerta"
    aviso = "aviso"


class PrediccionRiesgo(Base):
    __tablename__ = "predicciones_riesgo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alumno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perfiles_alumno.id"), nullable=False)
    grupo_materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupo_materia.id"), nullable=False)
    ciclo_escolar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ciclos_escolares.id"), nullable=False)
    probabilidad_reprobacion: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    nivel_riesgo: Mapped[NivelRiesgo] = mapped_column(Enum(NivelRiesgo), nullable=False)
    factores: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    modelo_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fecha_prediccion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    alumno: Mapped["PerfilAlumno"] = relationship("PerfilAlumno", back_populates="predicciones_riesgo")
    grupo_materia: Mapped["GrupoMateria"] = relationship("GrupoMateria", back_populates="predicciones_riesgo")
    ciclo_escolar: Mapped["CicloEscolar"] = relationship("CicloEscolar", back_populates="predicciones_riesgo")


class Alerta(Base):
    __tablename__ = "alertas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    usuario_destino_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    tipo: Mapped[TipoAlerta] = mapped_column(Enum(TipoAlerta), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alumno_referencia_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("perfiles_alumno.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="alertas")
    usuario_destino: Mapped["Usuario"] = relationship("Usuario", back_populates="alertas_recibidas", foreign_keys=[usuario_destino_id])
    alumno_referencia: Mapped[Optional["PerfilAlumno"]] = relationship("PerfilAlumno", back_populates="alertas_referencia", foreign_keys=[alumno_referencia_id])


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[TipoNotificacion] = mapped_column(Enum(TipoNotificacion), nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="notificaciones")
