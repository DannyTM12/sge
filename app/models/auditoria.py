"""
Modelo del dominio de auditoría.
Tabla: auditoria.
Esta tabla es APPEND-ONLY — nunca UPDATE ni DELETE sobre ella.
Registra cada acción sensible: modificaciones de calificaciones y justificantes.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.core import Institucion, Usuario


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    tabla_afectada: Mapped[str] = mapped_column(String(100), nullable=False)
    registro_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    valor_anterior: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    valor_nuevo: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="auditorias")
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="auditorias")
