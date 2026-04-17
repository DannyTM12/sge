"""
Middleware de control de acceso basado en roles (RBAC).
Verifica que el rol del usuario tenga permiso para acceder al endpoint solicitado.
Roles disponibles: superadmin, admin, profesor, alumno.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.middleware.auth import get_current_user
from app.models.core import Usuario


def require_roles(*roles: str) -> Callable:
    """
    Fábrica de dependencias que verifica el rol del usuario autenticado.

    Uso: Depends(require_roles("admin", "superadmin"))
    Lanza HTTP 403 si el rol del usuario no está en la lista permitida.
    """

    async def role_checker(
        current_user: Usuario = Depends(get_current_user),
    ) -> Usuario:
        if current_user.rol.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return current_user

    return role_checker
