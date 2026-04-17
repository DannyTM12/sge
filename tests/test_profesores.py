"""
Tests del módulo de profesores — SGE.
Cubre: sesiones, asistencias, calificaciones, notas y dashboard.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.academico import GrupoMateria, Inscripcion, ProfesorGrupoMateria
from app.models.asistencias import Asistencia, EstadoAsistencia, SesionClase
from app.models.core import RolUsuario
from app.models.evaluaciones import Calificacion, Parcial
from app.models.notas import NotaAlumno

from tests.conftest import (
    INST_A_ID,
    make_access_token,
    make_db_override,
    make_mock_user,
)

# ── Constantes ────────────────────────────────────────────────────────────────

GM_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
GRUPO_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
MATERIA_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
PARCIAL_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")
INSCRIPCION_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
SESION_ID = uuid.UUID("11000000-0000-0000-0000-000000000001")
ASISTENCIA_ID = uuid.UUID("12000000-0000-0000-0000-000000000001")
CALIFICACION_ID = uuid.UUID("13000000-0000-0000-0000-000000000001")
ALUMNO_ID = uuid.UUID("80000000-0000-0000-0000-000000000001")
NOTA_ID = uuid.UUID("14000000-0000-0000-0000-000000000001")


# ── Helpers de mock ───────────────────────────────────────────────────────────

def _single(value):
    """Resultado mock con scalar_one_or_none()."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _list_result(items):
    """Resultado mock con scalars().all() y all()."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.all.return_value = items
    return r


def make_multi_db(*results):
    """Mock DB que consume resultados en orden."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.execute.side_effect = list(results)
    return mock_db


def _make_profesor():
    return make_mock_user("prof@test.com", RolUsuario.profesor, INST_A_ID)


def _make_pgm():
    pgm = MagicMock(spec=ProfesorGrupoMateria)
    pgm.id = uuid.uuid4()
    pgm.grupo_materia_id = GM_ID
    return pgm


def _make_gm():
    gm = MagicMock(spec=GrupoMateria)
    gm.id = GM_ID
    gm.grupo_id = GRUPO_ID
    gm.materia_id = MATERIA_ID
    gm.num_parciales = 3
    return gm


def _make_sesion(profesor_id=None):
    s = MagicMock(spec=SesionClase)
    s.id = SESION_ID
    s.grupo_materia_id = GM_ID
    s.profesor_id = profesor_id or uuid.uuid4()
    s.fecha = date.today()
    s.hora_inicio = "08:00:00"
    s.hora_fin = "09:00:00"
    s.tema = "Álgebra"
    s.created_at = None
    return s


def _make_asistencia(created_at=None):
    a = MagicMock(spec=Asistencia)
    a.id = ASISTENCIA_ID
    a.sesion_id = SESION_ID
    a.alumno_id = ALUMNO_ID
    a.estado = EstadoAsistencia.presente
    a.registrado_por = uuid.uuid4()
    a.created_at = created_at
    return a


def _make_calificacion():
    c = MagicMock(spec=Calificacion)
    c.id = CALIFICACION_ID
    c.inscripcion_id = INSCRIPCION_ID
    c.parcial_id = PARCIAL_ID
    c.calificacion = Decimal("8.50")
    c.registrado_por = uuid.uuid4()
    c.created_at = None
    c.updated_at = None
    return c


def _make_inscripcion():
    insc = MagicMock(spec=Inscripcion)
    insc.id = INSCRIPCION_ID
    insc.alumno_id = ALUMNO_ID
    insc.grupo_id = GRUPO_ID
    insc.ciclo_escolar_id = uuid.uuid4()
    insc.fecha_inscripcion = date.today()
    insc.activa = True
    insc.created_at = None
    return insc


def _make_parcial():
    p = MagicMock(spec=Parcial)
    p.id = PARCIAL_ID
    p.grupo_materia_id = GM_ID
    p.numero = 1
    p.activo = True
    return p


def _make_nota():
    n = MagicMock(spec=NotaAlumno)
    n.id = NOTA_ID
    n.alumno_id = ALUMNO_ID
    n.autor_id = uuid.uuid4()
    n.institucion_id = INST_A_ID
    n.contenido = "Buen desempeño"
    n.es_visible_alumno = False
    n.created_at = None
    n.updated_at = None
    return n


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mis_grupos_happy_path(client: AsyncClient):
    """GET /profesores/mis-grupos devuelve lista de grupos asignados."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)

    mock_row = MagicMock()
    mock_row.grupo_materia_id = GM_ID
    mock_row.materia_id = MATERIA_ID
    mock_row.materia_nombre = "Matemáticas"
    mock_row.grupo_id = GRUPO_ID
    mock_row.grupo_nombre = "1A"
    mock_row.num_parciales = 3

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.execute.return_value = _list_result([mock_row])

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.get(
            "/profesores/mis-grupos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["materia_nombre"] == "Matemáticas"
        assert data[0]["grupo_nombre"] == "1A"
        assert data[0]["num_parciales"] == 3
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crear_sesion_happy_path(client: AsyncClient):
    """POST /profesores/sesiones crea sesión cuando el profesor tiene acceso."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    pgm = _make_pgm()

    mock_db = make_multi_db(_single(pgm))

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.post(
            "/profesores/sesiones",
            json={
                "grupo_materia_id": str(GM_ID),
                "fecha": str(date.today()),
                "hora_inicio": "08:00:00",
                "hora_fin": "09:30:00",
                "tema": "Introducción al álgebra",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["grupo_materia_id"] == str(GM_ID)
        assert data["tema"] == "Introducción al álgebra"
        assert "id" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crear_sesion_sin_acceso(client: AsyncClient):
    """POST /profesores/sesiones devuelve 404 si el profesor no tiene acceso."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)

    mock_db = make_multi_db(_single(None))

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.post(
            "/profesores/sesiones",
            json={
                "grupo_materia_id": str(GM_ID),
                "fecha": str(date.today()),
                "hora_inicio": "08:00:00",
                "hora_fin": "09:30:00",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_registrar_asistencia_happy_path(client: AsyncClient):
    """POST /profesores/sesiones/{id}/asistencia crea asistencias nuevas."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    sesion = _make_sesion(profesor_id=profesor.id)

    # execute[0]: sesion check, execute[1]: existing asistencias (empty)
    mock_db = make_multi_db(
        _single(sesion),
        _list_result([]),
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.post(
            f"/profesores/sesiones/{SESION_ID}/asistencia",
            json={
                "asistencias": [
                    {"alumno_id": str(ALUMNO_ID), "estado": "presente"},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["estado"] == "presente"
        assert data[0]["sesion_id"] == str(SESION_ID)
        assert mock_db.add.called
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_actualizar_asistencia_dentro_ventana(client: AsyncClient):
    """PATCH /profesores/asistencias/{id} actualiza cuando está dentro de 48h."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    asistencia = _make_asistencia(
        created_at=datetime.now(timezone.utc) - timedelta(hours=10)
    )

    mock_db = make_multi_db(_single(asistencia))

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.patch(
            f"/profesores/asistencias/{ASISTENCIA_ID}",
            json={"estado": "tardanza"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["estado"] == "tardanza"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_actualizar_asistencia_fuera_ventana_403(client: AsyncClient):
    """PATCH /profesores/asistencias/{id} devuelve 403 si pasaron más de 48h."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    asistencia = _make_asistencia(
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc)  # muy antiguo
    )

    mock_db = make_multi_db(_single(asistencia))

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.patch(
            f"/profesores/asistencias/{ASISTENCIA_ID}",
            json={"estado": "tardanza"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "48 horas" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_registrar_calificacion_happy_path(client: AsyncClient):
    """POST /profesores/calificaciones registra calificación y recalcula final."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    parcial = _make_parcial()
    inscripcion = _make_inscripcion()

    mock_db = make_multi_db(
        _single(parcial),       # acceso al parcial
        _single(inscripcion),   # inscripción existe
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    with patch("app.routers.profesores.recalcular_y_guardar") as mock_recalc:
        mock_recalc.return_value = None

        try:
            response = await client.post(
                "/profesores/calificaciones",
                json={
                    "inscripcion_id": str(INSCRIPCION_ID),
                    "parcial_id": str(PARCIAL_ID),
                    "calificacion": "8.5",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 201
            data = response.json()
            assert Decimal(data["calificacion"]) == Decimal("8.5")
            assert data["inscripcion_id"] == str(INSCRIPCION_ID)
            assert mock_recalc.called
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_actualizar_calificacion_happy_path(client: AsyncClient):
    """PUT /profesores/calificaciones/{id} actualiza y recalcula."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    cal = _make_calificacion()
    inscripcion = _make_inscripcion()
    parcial = _make_parcial()

    mock_db = make_multi_db(
        _single(cal),           # calificación con acceso
        _single(inscripcion),   # inscripción para recalcular
        _single(parcial),       # parcial para recalcular
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    with patch("app.routers.profesores.recalcular_y_guardar") as mock_recalc:
        mock_recalc.return_value = None

        try:
            response = await client.put(
                f"/profesores/calificaciones/{CALIFICACION_ID}",
                json={"calificacion": "9.0"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert Decimal(response.json()["calificacion"]) == Decimal("9.0")
            assert mock_recalc.called
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_crear_nota_happy_path(client: AsyncClient):
    """POST /profesores/notas crea nota sobre un alumno."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.delete = AsyncMock()

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.post(
            "/profesores/notas",
            json={
                "alumno_id": str(ALUMNO_ID),
                "contenido": "Necesita refuerzo en fracciones",
                "es_visible_alumno": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["contenido"] == "Necesita refuerzo en fracciones"
        assert data["es_visible_alumno"] is False
        assert data["alumno_id"] == str(ALUMNO_ID)
        assert mock_db.add.called
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_actualizar_nota_happy_path(client: AsyncClient):
    """PATCH /profesores/notas/{id} actualiza contenido y visibilidad."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    nota = _make_nota()

    mock_db = make_multi_db(_single(nota))

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.patch(
            f"/profesores/notas/{NOTA_ID}",
            json={"es_visible_alumno": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert nota.es_visible_alumno is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_eliminar_nota_happy_path(client: AsyncClient):
    """DELETE /profesores/notas/{id} elimina la nota y devuelve 204."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)
    nota = _make_nota()

    mock_db = make_multi_db(_single(nota))

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.delete(
            f"/profesores/notas/{NOTA_ID}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204
        assert mock_db.delete.called
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_profesor_happy_path(client: AsyncClient):
    """GET /profesores/dashboard devuelve resumen del profesor."""
    from app.main import app

    profesor = _make_profesor()
    token = make_access_token(profesor)

    mock_db = make_multi_db(
        _single(2),   # grupos_activos
        _single(1),   # sesiones_hoy
        _single(30),  # alumnos_totales
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        response = await client.get(
            "/profesores/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["grupos_activos"] == 2
        assert data["sesiones_hoy"] == 1
        assert data["alumnos_totales"] == 30
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rbac_alumno_no_puede_acceder(client: AsyncClient):
    """Alumno accediendo a endpoint de profesor recibe 403."""
    from app.main import app

    alumno = make_mock_user("alumno@test.com", RolUsuario.alumno, INST_A_ID)
    token = make_access_token(alumno)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        response = await client.get(
            "/profesores/mis-grupos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
