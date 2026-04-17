"""
Schemas Pydantic v2 para el dominio de usuarios.
"""

import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, computed_field

from app.models.core import RolUsuario


class UserRead(BaseModel):
    """Schema de lectura de usuario. Nunca incluye password_hash."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    nombre: str
    apellido_paterno: str
    email: EmailStr
    rol: RolUsuario
    institucion_id: uuid.UUID


class UserCreate(BaseModel):
    """Schema para crear un usuario desde el panel de admin."""

    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    email: EmailStr
    password: str
    rol: RolUsuario
    institucion_id: uuid.UUID


class UsuarioAdminCreate(BaseModel):
    """
    Schema completo para crear cualquier tipo de usuario desde el panel admin.
    Incluye campos de perfil según el rol indicado.
    """
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    email: EmailStr
    password: str
    rol: RolUsuario

    # Perfil alumno (obligatorio si rol == alumno)
    matricula: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    curp: Optional[str] = None
    telefono_tutor: Optional[str] = None
    nombre_tutor: Optional[str] = None
    email_tutor: Optional[str] = None

    # Perfil profesor (obligatorio si rol == profesor)
    numero_empleado: Optional[str] = None
    especialidad: Optional[str] = None
    telefono: Optional[str] = None


class UsuarioListRead(BaseModel):
    """Schema de listado de usuarios — incluye nombre completo calculado."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    email: str
    rol: RolUsuario
    activo: bool

    @computed_field
    @property
    def nombre_completo(self) -> str:
        partes = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            partes.append(self.apellido_materno)
        return " ".join(partes)


class EstadoUsuarioUpdate(BaseModel):
    activo: bool
