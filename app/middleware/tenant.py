"""
Middleware de aislamiento de tenant (institución).
Garantiza que todos los queries filtren por institucion_id del usuario autenticado.
Implementa la capa de multitenancy sobre el schema compartido.
"""

import uuid
from typing import Optional

from fastapi import Depends, Query

from app.middleware.auth import get_current_user
from app.models.core import RolUsuario, Usuario


async def get_tenant_id(
    current_user: Usuario = Depends(get_current_user),
    tenant: Optional[uuid.UUID] = Query(None, alias="tenant"),
) -> uuid.UUID:
    """
    Devuelve el institucion_id que debe usarse para filtrar queries del request actual.

    - Para cualquier rol normal: siempre devuelve current_user.institucion_id
      (el parámetro ?tenant es ignorado para evitar acceso cruzado entre instituciones).
    - Para superadmin: permite sobreescribir via ?tenant=<uuid> para gestionar
      cualquier institución desde el panel de plataforma.
    """
    if current_user.rol == RolUsuario.superadmin and tenant is not None:
        return tenant
    return current_user.institucion_id
