"""
Schemas Pydantic v2 para el dominio de notas de alumno.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotaCreate(BaseModel):
    alumno_id: uuid.UUID
    contenido: str
    es_visible_alumno: bool = False


class NotaRead(BaseModel):
    id: uuid.UUID
    alumno_id: uuid.UUID
    autor_id: uuid.UUID
    institucion_id: uuid.UUID
    contenido: str
    es_visible_alumno: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotaUpdate(BaseModel):
    contenido: Optional[str] = None
    es_visible_alumno: Optional[bool] = None
