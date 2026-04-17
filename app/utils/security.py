"""
Utilidades de seguridad.
Funciones para hash de contraseñas con bcrypt y generación/verificación de tokens JWT.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Genera un JWT de acceso con los datos y tiempo de expiración dados."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """
    Genera un token de refresco como UUID aleatorio (no JWT).
    El caller es responsable de hashearlo antes de almacenarlo.
    """
    return str(uuid.uuid4())


def decode_access_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT de acceso.
    Devuelve el payload si es válido, None si está expirado o es inválido.
    Nunca lanza excepción.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError:
        return None
