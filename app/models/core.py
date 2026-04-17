"""
Modelos del dominio Core / Multitenancy.
Tablas: instituciones, usuarios, perfiles_alumno, perfiles_profesor,
        sesiones_usuario, tokens_recuperacion.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.academico import CicloEscolar, Grupo, Inscripcion
    from app.models.asistencias import Asistencia, Justificante, SesionClase
    from app.models.auditoria import Auditoria
    from app.models.evaluaciones import Calificacion, CalificacionFinal
    from app.models.ia import Alerta, Notificacion, PrediccionRiesgo
    from app.models.notas import NotaAlumno


class RolUsuario(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    profesor = "profesor"
    alumno = "alumno"


class Institucion(Base):
    __tablename__ = "instituciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email_contacto: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan_suscripcion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    usuarios: Mapped[list["Usuario"]] = relationship("Usuario", back_populates="institucion")
    ciclos_escolares: Mapped[list["CicloEscolar"]] = relationship("CicloEscolar", back_populates="institucion")
    grupos: Mapped[list["Grupo"]] = relationship("Grupo", back_populates="institucion")
    alertas: Mapped[list["Alerta"]] = relationship("Alerta", back_populates="institucion")
    auditorias: Mapped[list["Auditoria"]] = relationship("Auditoria", back_populates="institucion")
    justificantes: Mapped[list["Justificante"]] = relationship("Justificante", back_populates="institucion")
    notas_alumno: Mapped[list["NotaAlumno"]] = relationship("NotaAlumno", back_populates="institucion")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_materno: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(Enum(RolUsuario), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    institucion: Mapped["Institucion"] = relationship("Institucion", back_populates="usuarios")
    perfil_alumno: Mapped[Optional["PerfilAlumno"]] = relationship("PerfilAlumno", back_populates="usuario", uselist=False)
    perfil_profesor: Mapped[Optional["PerfilProfesor"]] = relationship("PerfilProfesor", back_populates="usuario", uselist=False)
    sesiones: Mapped[list["SesionUsuario"]] = relationship("SesionUsuario", back_populates="usuario")
    tokens_recuperacion: Mapped[list["TokenRecuperacion"]] = relationship("TokenRecuperacion", back_populates="usuario")
    calificaciones_registradas: Mapped[list["Calificacion"]] = relationship("Calificacion", back_populates="registrado_por_usuario", foreign_keys="Calificacion.registrado_por")
    calificaciones_finales_modificadas: Mapped[list["CalificacionFinal"]] = relationship("CalificacionFinal", back_populates="modificado_por_usuario", foreign_keys="CalificacionFinal.modificado_por")
    sesiones_clase_impartidas: Mapped[list["SesionClase"]] = relationship("SesionClase", back_populates="profesor")
    asistencias_registradas: Mapped[list["Asistencia"]] = relationship("Asistencia", back_populates="registrado_por_usuario", foreign_keys="Asistencia.registrado_por")
    justificantes_registrados: Mapped[list["Justificante"]] = relationship("Justificante", back_populates="registrado_por_usuario", foreign_keys="Justificante.registrado_por")
    alertas_recibidas: Mapped[list["Alerta"]] = relationship("Alerta", back_populates="usuario_destino", foreign_keys="Alerta.usuario_destino_id")
    notificaciones: Mapped[list["Notificacion"]] = relationship("Notificacion", back_populates="usuario")
    auditorias: Mapped[list["Auditoria"]] = relationship("Auditoria", back_populates="usuario")
    notas_alumno_como_autor: Mapped[list["NotaAlumno"]] = relationship("NotaAlumno", back_populates="autor", foreign_keys="NotaAlumno.autor_id")


class PerfilAlumno(Base):
    __tablename__ = "perfiles_alumno"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), unique=True, nullable=False)
    matricula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fecha_nacimiento: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    curp: Mapped[Optional[str]] = mapped_column(String(18), nullable=True)
    telefono_tutor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nombre_tutor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email_tutor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="perfil_alumno")
    inscripciones: Mapped[list["Inscripcion"]] = relationship("Inscripcion", back_populates="alumno")
    asistencias: Mapped[list["Asistencia"]] = relationship("Asistencia", back_populates="alumno", foreign_keys="Asistencia.alumno_id")
    justificantes: Mapped[list["Justificante"]] = relationship("Justificante", back_populates="alumno", foreign_keys="Justificante.alumno_id")
    notas_alumno: Mapped[list["NotaAlumno"]] = relationship("NotaAlumno", back_populates="alumno", foreign_keys="NotaAlumno.alumno_id")
    predicciones_riesgo: Mapped[list["PrediccionRiesgo"]] = relationship("PrediccionRiesgo", back_populates="alumno")
    alertas_referencia: Mapped[list["Alerta"]] = relationship("Alerta", back_populates="alumno_referencia", foreign_keys="Alerta.alumno_referencia_id")


class PerfilProfesor(Base):
    __tablename__ = "perfiles_profesor"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), unique=True, nullable=False)
    numero_empleado: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    especialidad: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="perfil_profesor")


class SesionUsuario(Base):
    __tablename__ = "sesiones_usuario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    dispositivo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="sesiones")


class TokenRecuperacion(Base):
    __tablename__ = "tokens_recuperacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="tokens_recuperacion")
