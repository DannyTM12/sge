"""
Fixtures de pytest para tests del sistema SGE.
Usa mocks para DB y Redis — no requiere servicios externos levantados.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.core import RolUsuario, Usuario
from app.utils.security import create_access_token, hash_password

# ── Constantes de prueba ──────────────────────────────────────────────────────

TEST_PASSWORD = "test_password_123"
INST_A_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
INST_B_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_user(
    email: str,
    rol: RolUsuario,
    institucion_id: uuid.UUID = INST_A_ID,
    activo: bool = True,
    password: str = TEST_PASSWORD,
) -> MagicMock:
    """Crea un usuario mock con contraseña real hasheada."""
    user = MagicMock(spec=Usuario)
    user.id = uuid.uuid4()
    user.email = email
    user.password_hash = hash_password(password)
    user.activo = activo
    user.rol = rol
    user.institucion_id = institucion_id
    user.nombre = "Test"
    user.apellido_paterno = "User"
    user.ultimo_acceso = None
    return user


def make_mock_db(user: Any = None, *, side_effects: list | None = None) -> AsyncMock:
    """
    Crea un AsyncMock de AsyncSession.
    - Si se pasa `user`, scalar_one_or_none() devuelve ese usuario en todas las llamadas.
    - Si se pasa `side_effects`, las llamadas a execute() consumen esa lista en orden.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    if side_effects is not None:
        # Cada elemento puede ser un usuario/objeto o None
        def _make_result(value: Any) -> MagicMock:
            r = MagicMock()
            r.scalar_one_or_none.return_value = value
            return r

        mock_db.execute.side_effect = [_make_result(v) for v in side_effects]
    else:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

    return mock_db


def make_db_override(mock_db: AsyncMock):
    """Devuelve una función override compatible con get_db (async generator)."""
    async def _override() -> AsyncGenerator:
        yield mock_db
    return _override


def make_access_token(user: MagicMock, expires_delta: timedelta | None = None) -> str:
    """Genera un access token real para el usuario mock dado."""
    delta = expires_delta if expires_delta is not None else timedelta(minutes=30)
    return create_access_token(
        data={
            "sub": str(user.id),
            "rol": user.rol.value,
            "institucion_id": str(user.institucion_id),
        },
        expires_delta=delta,
    )


# ── Fixtures de usuarios ──────────────────────────────────────────────────────

@pytest.fixture
def superadmin_user() -> MagicMock:
    return make_mock_user("superadmin@test.com", RolUsuario.superadmin, INST_A_ID)


@pytest.fixture
def admin_user() -> MagicMock:
    return make_mock_user("admin@test.com", RolUsuario.admin, INST_A_ID)


@pytest.fixture
def profesor_user() -> MagicMock:
    return make_mock_user("profesor@test.com", RolUsuario.profesor, INST_A_ID)


@pytest.fixture
def alumno_user() -> MagicMock:
    return make_mock_user("alumno@test.com", RolUsuario.alumno, INST_A_ID)


@pytest.fixture
def inactive_user() -> MagicMock:
    return make_mock_user("inactive@test.com", RolUsuario.admin, INST_A_ID, activo=False)


@pytest.fixture
def inst_b_user() -> MagicMock:
    return make_mock_user("user@inst-b.com", RolUsuario.admin, INST_B_ID)


# ── Fixture de cliente HTTP ───────────────────────────────────────────────────

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP async para tests de endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
