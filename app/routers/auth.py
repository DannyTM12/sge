"""
Router de autenticación.
POST /auth/login, POST /auth/refresh, POST /auth/logout,
POST /auth/logout-all, POST /auth/forgot-password, POST /auth/reset-password
"""

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.redis import (
    check_rate_limit,
    delete_all_user_tokens,
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)
from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.core import SesionUsuario, TokenRecuperacion, Usuario
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_GENERIC_AUTH_ERROR = "Credenciales inválidas"


def _hash_token(token: str) -> str:
    """Hashea un token con SHA-256 para almacenamiento seguro."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Autentica al usuario con email + password.
    Rate limit: 5 intentos por IP en 60 segundos.
    Siempre devuelve el mismo mensaje de error para no revelar si el email existe.
    """
    client_ip = request.client.host if request.client else "unknown"
    allowed = await check_rate_limit(
        key=f"login:{client_ip}",
        max_attempts=5,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Intenta nuevamente en un momento.",
        )

    # Buscar usuario por email
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    user = result.scalar_one_or_none()

    # Verificar contraseña (short-circuit si user es None)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_GENERIC_AUTH_ERROR,
        )

    # Usuario inactivo → mismo mensaje genérico
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_GENERIC_AUTH_ERROR,
        )

    # Generar tokens
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "rol": user.rol.value,
            "institucion_id": str(user.institucion_id),
        },
        expires_delta=expires_delta,
    )
    refresh_token = create_refresh_token(user.id)
    token_hash = _hash_token(refresh_token)

    # Guardar refresh token en Redis
    await save_refresh_token(
        user_id=str(user.id),
        token_hash=token_hash,
        ttl_days=settings.refresh_token_expire_days,
    )

    # Guardar sesión en DB
    expira_en = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    sesion = SesionUsuario(
        usuario_id=user.id,
        refresh_token_hash=token_hash,
        dispositivo=request.headers.get("User-Agent", "unknown")[:500],
        ip_address=client_ip,
        expira_en=expira_en,
        activa=True,
    )
    db.add(sesion)
    user.ultimo_acceso = datetime.now(timezone.utc)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Renueva el access token usando un refresh token válido.
    Implementa rotación de refresh tokens: invalida el anterior y emite uno nuevo.
    """
    token_hash = _hash_token(data.refresh_token)

    user_id = await get_refresh_token(token_hash)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido o expirado",
        )

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido o expirado",
        )

    # Rotar: eliminar token anterior
    await delete_refresh_token(token_hash)
    await db.execute(
        update(SesionUsuario)
        .where(SesionUsuario.refresh_token_hash == token_hash)
        .values(activa=False)
    )

    # Generar nuevos tokens
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "rol": user.rol.value,
            "institucion_id": str(user.institucion_id),
        },
        expires_delta=expires_delta,
    )
    new_refresh_token = create_refresh_token(user.id)
    new_token_hash = _hash_token(new_refresh_token)

    await save_refresh_token(
        user_id=str(user.id),
        token_hash=new_token_hash,
        ttl_days=settings.refresh_token_expire_days,
    )

    expira_en = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db.add(SesionUsuario(
        usuario_id=user.id,
        refresh_token_hash=new_token_hash,
        expira_en=expira_en,
        activa=True,
    ))
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> None:
    """
    Cierra la sesión del usuario eliminando el refresh token.
    Requiere autenticación con access token válido.
    """
    token_hash = _hash_token(data.refresh_token)

    # Verificar que el token pertenece al usuario actual
    stored_user_id = await get_refresh_token(token_hash)
    if stored_user_id and stored_user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El token no pertenece al usuario actual",
        )

    await delete_refresh_token(token_hash)
    await db.execute(
        update(SesionUsuario)
        .where(SesionUsuario.refresh_token_hash == token_hash)
        .values(activa=False)
    )
    await db.flush()


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Cierra todas las sesiones activas del usuario en todos los dispositivos.
    Requiere autenticación con access token válido.
    """
    await delete_all_user_tokens(str(current_user.id))
    await db.execute(
        update(SesionUsuario)
        .where(SesionUsuario.usuario_id == current_user.id)
        .values(activa=False)
    )
    await db.flush()


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Inicia el flujo de recuperación de contraseña.
    Siempre responde igual — no revela si el email existe (anti-enumeración).
    """
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    user = result.scalar_one_or_none()

    if user:
        raw_token = str(uuid.uuid4())
        token_hash = _hash_token(raw_token)
        expira_en = datetime.now(timezone.utc) + timedelta(hours=1)

        db.add(TokenRecuperacion(
            usuario_id=user.id,
            token_hash=token_hash,
            expira_en=expira_en,
            usado=False,
        ))
        await db.flush()

        # TODO: enviar por email. Por ahora solo loguear.
        logger.info("[forgot-password] token para %s: %s", data.email, raw_token)

    return {"message": "Si el email existe, recibirás instrucciones"}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Completa el flujo de recuperación: valida el token y actualiza la contraseña.
    """
    token_hash = _hash_token(data.token)

    result = await db.execute(
        select(TokenRecuperacion).where(
            TokenRecuperacion.token_hash == token_hash,
            TokenRecuperacion.usado == False,  # noqa: E712
            TokenRecuperacion.expira_en > datetime.now(timezone.utc),
        )
    )
    recovery = result.scalar_one_or_none()

    if not recovery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        )

    result_user = await db.execute(
        select(Usuario).where(Usuario.id == recovery.usuario_id)
    )
    user = result_user.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        )

    user.password_hash = hash_password(data.new_password)
    recovery.usado = True
    await db.flush()

    return {"message": "Contraseña actualizada correctamente"}
