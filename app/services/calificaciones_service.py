"""
Servicio de calificaciones.
Lógica de negocio para calcular y persistir calificaciones finales.
Desacoplado del router para facilitar testing y reutilización.
"""

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluaciones import Calificacion, CalificacionFinal, Parcial


async def calcular_calificacion_final(
    inscripcion_id: uuid.UUID,
    grupo_materia_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[Decimal]:
    """
    Promedia todas las calificaciones de los parciales de una combinación
    inscripcion × grupo_materia.
    Devuelve None si no hay calificaciones registradas.
    """
    resultado = await db.execute(
        select(func.avg(Calificacion.calificacion))
        .join(Parcial, Calificacion.parcial_id == Parcial.id)
        .where(
            Calificacion.inscripcion_id == inscripcion_id,
            Parcial.grupo_materia_id == grupo_materia_id,
        )
    )
    valor = resultado.scalar_one_or_none()
    if valor is None:
        return None
    return Decimal(str(valor)).quantize(Decimal("0.01"))


async def recalcular_y_guardar(
    inscripcion_id: uuid.UUID,
    materia_id: uuid.UUID,
    grupo_materia_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Calcula el promedio y actualiza (o crea) la fila en calificaciones_finales.

    Reglas de negocio:
    - Si no hay calificaciones aún, no hace nada.
    - Si ya existe la fila y fue_modificada_manualmente = True,
      solo actualiza calificacion_calculada, nunca calificacion_final.
    - Si fue_modificada_manualmente = False, sincroniza ambas columnas.
    """
    promedio = await calcular_calificacion_final(inscripcion_id, grupo_materia_id, db)
    if promedio is None:
        return

    resultado = await db.execute(
        select(CalificacionFinal).where(
            CalificacionFinal.inscripcion_id == inscripcion_id,
            CalificacionFinal.materia_id == materia_id,
        )
    )
    cf = resultado.scalar_one_or_none()

    if cf is None:
        db.add(CalificacionFinal(
            inscripcion_id=inscripcion_id,
            materia_id=materia_id,
            calificacion_calculada=promedio,
            calificacion_final=promedio,
        ))
    else:
        cf.calificacion_calculada = promedio
        if not cf.fue_modificada_manualmente:
            cf.calificacion_final = promedio
