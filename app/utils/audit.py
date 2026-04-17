"""
Helper de auditoría.
Función de conveniencia para insertar registros en la tabla `auditoria`.
Debe llamarse en cada modificación de calificaciones y justificantes.
La tabla auditoria es APPEND-ONLY — nunca UPDATE ni DELETE sobre ella.
"""

import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditoria import Auditoria


async def registrar_auditoria(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    institucion_id: uuid.UUID,
    accion: str,
    tabla: str,
    registro_id: Optional[uuid.UUID],
    valor_anterior: Optional[dict[str, Any]],
    valor_nuevo: Optional[dict[str, Any]],
    request: Optional[Request] = None,
) -> None:
    """
    Inserta un registro en la tabla auditoria.
    Extrae IP y user_agent del objeto Request si está disponible.
    """
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    if request is not None:
        if request.client:
            ip_address = request.client.host
        raw_ua = request.headers.get("User-Agent")
        if raw_ua:
            user_agent = raw_ua[:500]

    db.add(Auditoria(
        id=uuid.uuid4(),
        institucion_id=institucion_id,
        usuario_id=usuario_id,
        accion=accion,
        tabla_afectada=tabla,
        registro_id=registro_id,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        ip_address=ip_address,
        user_agent=user_agent,
    ))
