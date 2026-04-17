"""
Tests de autenticación y seguridad para el sistema SGE.
Cubre: login, refresh, logout, expiración de tokens, roles, y tenant isolation.
"""

import hashlib
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_roles
from app.middleware.tenant import get_tenant_id
from app.models.core import RolUsuario
from app.utils.security import create_access_token, hash_password, verify_password

from tests.conftest import (
    INST_A_ID,
    INST_B_ID,
    TEST_PASSWORD,
    make_access_token,
    make_db_override,
    make_mock_db,
    make_mock_user,
)

# ── Helpers locales ───────────────────────────────────────────────────────────

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── 1. Login exitoso devuelve access_token y refresh_token ───────────────────

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    mock_db = make_mock_db(admin_user)
    app_override = make_db_override(mock_db)

    from app.main import app
    app.dependency_overrides[get_db] = app_override

    try:
        with (
            patch("app.routers.auth.check_rate_limit", return_value=True),
            patch("app.routers.auth.save_refresh_token", new_callable=AsyncMock),
        ):
            response = await client.post(
                "/auth/login",
                json={"email": "admin@test.com", "password": TEST_PASSWORD},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


# ── 2. Login con password incorrecto devuelve 401 con mensaje genérico ────────

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    mock_db = make_mock_db(admin_user)
    from app.main import app
    app.dependency_overrides[get_db] = make_db_override(mock_db)

    try:
        with patch("app.routers.auth.check_rate_limit", return_value=True):
            response = await client.post(
                "/auth/login",
                json={"email": "admin@test.com", "password": "wrong_password"},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 401
    # El mensaje no debe revelar si el email existe o si la contraseña es incorrecta
    detail = response.json()["detail"]
    assert "email" not in detail.lower()
    assert "contraseña" not in detail.lower()
    assert "no existe" not in detail.lower()


# ── 3. Token expirado devuelve 401 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_token_returns_401(client: AsyncClient, admin_user):
    expired_token = make_access_token(admin_user, expires_delta=timedelta(seconds=-1))

    mock_db = make_mock_db(admin_user)
    from app.main import app
    app.dependency_overrides[get_db] = make_db_override(mock_db)

    try:
        with (
            patch("app.routers.auth.delete_all_user_tokens", new_callable=AsyncMock),
        ):
            response = await client.post(
                "/auth/logout-all",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 401


# ── 4. Refresh exitoso devuelve nuevo access_token ────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, admin_user):
    raw_refresh = str(uuid.uuid4())
    token_hash = _hash(raw_refresh)

    # execute() llamadas: 1) select Usuario, 2) update SesionUsuario, 3) add nueva sesión
    mock_db = make_mock_db(side_effects=[admin_user, MagicMock()])
    from app.main import app
    app.dependency_overrides[get_db] = make_db_override(mock_db)

    try:
        with (
            patch("app.routers.auth.get_refresh_token", return_value=str(admin_user.id)),
            patch("app.routers.auth.delete_refresh_token", new_callable=AsyncMock),
            patch("app.routers.auth.save_refresh_token", new_callable=AsyncMock),
        ):
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": raw_refresh},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # El nuevo refresh token es diferente al anterior
    assert data["refresh_token"] != raw_refresh


# ── 5. Logout invalida el refresh token ──────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(client: AsyncClient, admin_user):
    """
    Después de logout, el mismo refresh token ya no debe servir para hacer refresh.
    """
    raw_refresh = str(uuid.uuid4())
    access_token = make_access_token(admin_user)

    # Primera llamada a DB: get_current_user busca al usuario
    mock_db = make_mock_db(admin_user)
    from app.main import app
    app.dependency_overrides[get_db] = make_db_override(mock_db)

    deleted_tokens = set()

    async def mock_delete(token_hash: str):
        deleted_tokens.add(token_hash)

    async def mock_get(token_hash: str):
        if token_hash in deleted_tokens:
            return None
        return str(admin_user.id)

    try:
        with (
            patch("app.routers.auth.get_refresh_token", side_effect=mock_get),
            patch("app.routers.auth.delete_refresh_token", side_effect=mock_delete),
        ):
            # Logout
            logout_response = await client.post(
                "/auth/logout",
                json={"refresh_token": raw_refresh},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert logout_response.status_code == 204

            # Intentar usar el mismo refresh token → debe fallar
            refresh_mock_db = make_mock_db(None)  # token ya no existe en Redis
            app.dependency_overrides[get_db] = make_db_override(refresh_mock_db)

            refresh_response = await client.post(
                "/auth/refresh",
                json={"refresh_token": raw_refresh},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert refresh_response.status_code == 401


# ── 6. Usuario inactivo no puede hacer login ─────────────────────────────────

@pytest.mark.asyncio
async def test_inactive_user_cannot_login(client: AsyncClient, inactive_user):
    mock_db = make_mock_db(inactive_user)
    from app.main import app
    app.dependency_overrides[get_db] = make_db_override(mock_db)

    try:
        with patch("app.routers.auth.check_rate_limit", return_value=True):
            response = await client.post(
                "/auth/login",
                json={"email": "inactive@test.com", "password": TEST_PASSWORD},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 401


# ── 7. Rol incorrecto en endpoint protegido devuelve 403 ─────────────────────

@pytest.mark.asyncio
async def test_wrong_role_returns_403(alumno_user):
    """
    Un usuario con rol 'alumno' intentando acceder a un endpoint que requiere
    'admin' o 'superadmin' debe recibir 403.
    """
    checker = require_roles("admin", "superadmin")

    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=alumno_user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_correct_role_passes(admin_user):
    """Un usuario con rol 'admin' puede acceder a un endpoint que requiere 'admin'."""
    checker = require_roles("admin", "superadmin")
    result = await checker(current_user=admin_user)
    assert result is admin_user


# ── 8. Tenant isolation ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_isolation_non_superadmin(admin_user):
    """
    Un usuario normal no puede acceder a datos de otra institución,
    incluso si pasa ?tenant=otro_id en la URL.
    """
    # Sin parámetro tenant → devuelve su propio institucion_id
    tenant_id = await get_tenant_id(current_user=admin_user, tenant=None)
    assert tenant_id == INST_A_ID

    # Con parámetro tenant de otra institución → sigue devolviendo el suyo
    tenant_id = await get_tenant_id(current_user=admin_user, tenant=INST_B_ID)
    assert tenant_id == INST_A_ID  # No se respeta el parámetro para no-superadmin


@pytest.mark.asyncio
async def test_tenant_isolation_superadmin_can_switch(superadmin_user):
    """
    El superadmin puede gestionar cualquier institución via ?tenant=uuid.
    """
    # Sin parámetro → su propio institucion_id
    tenant_id = await get_tenant_id(current_user=superadmin_user, tenant=None)
    assert tenant_id == INST_A_ID

    # Con parámetro → puede acceder a otra institución
    tenant_id = await get_tenant_id(current_user=superadmin_user, tenant=INST_B_ID)
    assert tenant_id == INST_B_ID


@pytest.mark.asyncio
async def test_inst_a_user_cannot_get_inst_b_token(admin_user, inst_b_user):
    """
    El access token de un usuario de institución A incluye su propio institucion_id,
    no el de institución B.
    """
    token = make_access_token(admin_user)

    from app.utils.security import decode_access_token
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["institucion_id"] == str(INST_A_ID)
    assert payload["institucion_id"] != str(INST_B_ID)


# ── Tests unitarios de funciones de seguridad ─────────────────────────────────

def test_hash_and_verify_password():
    hashed = hash_password("mi_contraseña")
    assert verify_password("mi_contraseña", hashed) is True
    assert verify_password("otra_contraseña", hashed) is False


def test_decode_invalid_token_returns_none():
    from app.utils.security import decode_access_token
    assert decode_access_token("token.invalido.aqui") is None
    assert decode_access_token("") is None


def test_decode_expired_token_returns_none():
    from app.utils.security import decode_access_token
    user = make_mock_user("x@x.com", RolUsuario.admin)
    expired = make_access_token(user, expires_delta=timedelta(seconds=-60))
    assert decode_access_token(expired) is None


def test_decode_valid_token_returns_payload():
    from app.utils.security import decode_access_token
    user = make_mock_user("x@x.com", RolUsuario.admin)
    token = make_access_token(user)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user.id)
    assert payload["rol"] == "admin"
