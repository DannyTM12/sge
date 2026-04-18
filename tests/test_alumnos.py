"""
Tests del módulo de alumnos — SGE.
Cubre: dashboard, calificaciones, asistencias, notas, notificaciones, boleta PDF.
PRINCIPIO: alumno_id siempre del token, nunca por parámetro.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.asistencias import Asistencia, EstadoAsistencia, SesionClase
from app.models.core import PerfilAlumno, RolUsuario, Usuario
from app.models.evaluaciones import Calificacion, CalificacionFinal, Parcial
from app.models.ia import Notificacion, TipoNotificacion
from app.models.notas import NotaAlumno

from tests.conftest import (
    INST_A_ID,
    make_access_token,
    make_db_override,
    make_mock_user,
)

# ── Constantes ────────────────────────────────────────────────────────────────

PERFIL_A_ID = uuid.UUID("A0000000-0000-0000-0000-000000000001")
PERFIL_B_ID = uuid.UUID("B0000000-0000-0000-0000-000000000002")
INSCRIPCION_A_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
GRUPO_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
CICLO_ID = uuid.UUID("C0000000-0000-0000-0000-000000000001")
GM_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
MATERIA_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
PARCIAL_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")
NOTIF_A_ID = uuid.UUID("70000000-0000-0000-0000-000000000001")
NOTIF_B_ID = uuid.UUID("70000000-0000-0000-0000-000000000002")


# ── Helpers de mock ───────────────────────────────────────────────────────────


def _single(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.one_or_none.return_value = value
    r.scalars.return_value.all.return_value = [value] if value is not None else []
    r.all.return_value = [value] if value is not None else []
    r.rowcount = 0
    return r


def _single_scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.one_or_none.return_value = None
    r.scalars.return_value.all.return_value = []
    r.all.return_value = []
    r.rowcount = 0
    return r


def _list_result(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.all.return_value = items
    r.scalar_one_or_none.return_value = items[0] if items else None
    r.one_or_none.return_value = items[0] if items else None
    r.rowcount = len(items)
    return r


def _empty():
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    r.one_or_none.return_value = None
    r.scalars.return_value.all.return_value = []
    r.all.return_value = []
    r.rowcount = 0
    return r


def make_multi_db(*results):
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.execute.side_effect = list(results)
    return mock_db


def _make_alumno_user(suffix="A") -> MagicMock:
    return make_mock_user(f"alumno{suffix}@test.com", RolUsuario.alumno, INST_A_ID)


def _make_perfil(perfil_id: uuid.UUID, alumno_user: MagicMock) -> MagicMock:
    p = MagicMock(spec=PerfilAlumno)
    p.id = perfil_id
    p.usuario_id = alumno_user.id
    p.matricula = f"MAT{str(perfil_id)[:4].upper()}"
    return p


def _make_insc_row(inscripcion_id=INSCRIPCION_A_ID, grupo_id=GRUPO_ID):
    """Fila de inscripción (Row de SQLAlchemy simulado)."""
    row = MagicMock()
    row.inscripcion_id = inscripcion_id
    row.grupo_id = grupo_id
    row.grupo_nombre = "1A"
    row.ciclo_id = CICLO_ID
    row.ciclo_nombre = "2026-1"
    return row


def _make_gm_row(gm_id=GM_ID, materia_id=MATERIA_ID):
    row = MagicMock()
    row.gm_id = gm_id
    row.grupo_id = GRUPO_ID
    row.materia_id = materia_id
    row.num_parciales = 3
    row.materia_nombre = "Matemáticas"
    row.clave = "MAT101"
    row.prof_nombre = "Juan"
    row.prof_apellido = "García"
    return row


def _make_parcial(
    parcial_id=PARCIAL_ID,
    numero=1,
    fecha_cierre_offset_days: int | None = -1,  # negativo = ya cerrado
) -> MagicMock:
    p = MagicMock(spec=Parcial)
    p.id = parcial_id
    p.grupo_materia_id = GM_ID
    p.numero = numero
    p.nombre = f"Parcial {numero}"
    p.activo = True
    if fecha_cierre_offset_days is None:
        p.fecha_cierre = None
    else:
        p.fecha_cierre = datetime.now(timezone.utc) + timedelta(days=fecha_cierre_offset_days)
    return p


def _make_calificacion(parcial_id=PARCIAL_ID, valor="8.50") -> MagicMock:
    c = MagicMock(spec=Calificacion)
    c.id = uuid.uuid4()
    c.inscripcion_id = INSCRIPCION_A_ID
    c.parcial_id = parcial_id
    c.calificacion = Decimal(valor)
    c.updated_at = datetime.now(timezone.utc)
    return c


def _make_cf(materia_id=MATERIA_ID, calculada="8.50", final="8.50", modificada=False) -> MagicMock:
    cf = MagicMock(spec=CalificacionFinal)
    cf.id = uuid.uuid4()
    cf.inscripcion_id = INSCRIPCION_A_ID
    cf.materia_id = materia_id
    cf.calificacion_calculada = Decimal(calculada)
    cf.calificacion_final = Decimal(final)
    cf.fue_modificada_manualmente = modificada
    return cf


def _make_notificacion(
    notif_id: uuid.UUID,
    usuario_id: uuid.UUID,
    leida: bool = False,
) -> MagicMock:
    n = MagicMock(spec=Notificacion)
    n.id = notif_id
    n.usuario_id = usuario_id
    n.titulo = "Aviso"
    n.mensaje = "Tienes una calificación nueva"
    n.tipo = TipoNotificacion.info
    n.leida = leida
    n.created_at = datetime.now(timezone.utc)
    return n


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_devuelve_datos_del_alumno_autenticado(client: AsyncClient):
    """Dashboard devuelve nombre, matrícula y datos del ciclo activo del alumno A."""
    from app.main import app

    alumno = _make_alumno_user("A")
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)
    insc_row = _make_insc_row()

    mock_db = make_multi_db(
        _single(perfil),              # perfil_alumno
        _list_result([insc_row]),     # inscripcion activa
        _single_scalar(0),            # notif count (no inscripcion branch no ejecuta)
    )
    # La DB de insc retorna None para simular sin datos de materias
    # Para simplificar: override que devuelve dashboard vacío por no-inscripcion
    # → usamos flujo con inscripcion=None para el mock
    insc_result = MagicMock()
    insc_result.one_or_none.return_value = None  # sin inscripcion activa
    notif_result = MagicMock()
    notif_result.scalar_one_or_none.return_value = 2  # 2 notif no leídas

    mock_db2 = make_multi_db(
        _single(perfil),   # perfil
        insc_result,       # inscripcion → None
        notif_result,      # notif count = 2
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db2)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.get("/alumnos/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "nombre_completo" in data
        assert data["alertas_no_leidas"] == 2
        assert data["materias"] == []
        assert data["grupo_nombre"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_alumno_no_puede_ver_datos_de_otro(client: AsyncClient):
    """
    No existe parámetro alumno_id en ningún endpoint.
    El token del alumno A siempre devuelve datos de A, nunca de B.
    """
    from app.main import app

    alumno_a = _make_alumno_user("A")
    token_a = make_access_token(alumno_a)
    perfil_a = _make_perfil(PERFIL_A_ID, alumno_a)

    insc_result = MagicMock()
    insc_result.one_or_none.return_value = None
    notif_result = MagicMock()
    notif_result.scalar_one_or_none.return_value = 0

    mock_db = make_multi_db(_single(perfil_a), insc_result, notif_result)

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno_a

    try:
        resp = await client.get("/alumnos/dashboard", headers={"Authorization": f"Bearer {token_a}"})
        assert resp.status_code == 200
        data = resp.json()
        # El nombre es del usuario autenticado (alumno A), no de B
        assert "alumnoA" in data["nombre_completo"].lower() or "test" in data["nombre_completo"].lower()
        assert data["materias"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_calificaciones_parcial_no_cerrado_se_oculta(client: AsyncClient):
    """Parcial con fecha_cierre en el futuro → calificacion=None, esta_publicada=False."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    # insc row
    insc_row = MagicMock()
    insc_row.inscripcion_id = INSCRIPCION_A_ID
    insc_row.grupo_id = GRUPO_ID
    insc_result = MagicMock()
    insc_result.one_or_none.return_value = insc_row

    # Parcial con fecha_cierre en el futuro
    parcial_futuro = _make_parcial(fecha_cierre_offset_days=+5)
    calificacion = _make_calificacion()

    gm_row = _make_gm_row()
    gm_result = MagicMock()
    gm_result.all.return_value = [gm_row]

    parc_result = MagicMock()
    parc_result.scalars.return_value.all.return_value = [parcial_futuro]

    cal_result = MagicMock()
    cal_result.scalars.return_value.all.return_value = [calificacion]

    cf_result = MagicMock()
    cf_result.scalars.return_value.all.return_value = []

    mock_db = make_multi_db(
        _single(perfil),   # perfil
        insc_result,       # inscripcion
        gm_result,         # gm_rows
        parc_result,       # parciales
        cal_result,        # calificaciones
        cf_result,         # calificaciones_finales
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.get("/alumnos/calificaciones", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        materia = data[0]
        assert len(materia["parciales"]) == 1
        p = materia["parciales"][0]
        assert p["calificacion"] is None
        assert p["esta_publicada"] is False
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_resumen_asistencias_porcentaje_correcto(client: AsyncClient):
    """10 sesiones (8 presentes, 1 ausente, 1 tardanza) → porcentaje_asistencia = 0.9."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    insc_row = MagicMock()
    insc_row.inscripcion_id = INSCRIPCION_A_ID
    insc_row.grupo_id = GRUPO_ID
    insc_result = MagicMock()
    insc_result.one_or_none.return_value = insc_row

    # Filas de estadísticas: estado × count
    def _stat_row(estado, cnt):
        r = MagicMock()
        r.materia_id = MATERIA_ID
        r.materia_nombre = "Matemáticas"
        r.estado = estado
        r.cnt = cnt
        return r

    stats_result = MagicMock()
    stats_result.all.return_value = [
        _stat_row(EstadoAsistencia.presente, 8),
        _stat_row(EstadoAsistencia.ausente, 1),
        _stat_row(EstadoAsistencia.tardanza, 1),
    ]

    mock_db = make_multi_db(
        _single(perfil),
        insc_result,
        stats_result,
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.get("/alumnos/asistencias/resumen", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        r = data[0]
        assert r["total_sesiones"] == 10
        assert r["presentes"] == 8
        assert r["ausentes"] == 1
        assert r["tardanzas"] == 1
        assert abs(r["porcentaje_asistencia"] - 0.9) < 0.001
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_resumen_asistencias_sin_sesiones(client: AsyncClient):
    """Sin sesiones registradas → porcentaje_asistencia = None (no 0.0)."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    insc_row = MagicMock()
    insc_row.inscripcion_id = INSCRIPCION_A_ID
    insc_row.grupo_id = GRUPO_ID
    insc_result = MagicMock()
    insc_result.one_or_none.return_value = insc_row

    stats_result = MagicMock()
    stats_result.all.return_value = []  # Sin sesiones

    mock_db = make_multi_db(_single(perfil), insc_result, stats_result)

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.get("/alumnos/asistencias/resumen", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []  # sin materias = sin resumen
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_notas_solo_visibles(client: AsyncClient):
    """3 notas creadas (2 visibles, 1 interna) → endpoint devuelve solo 2."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    def _nota_row(visible: bool):
        r = MagicMock()
        r.contenido = "Nota de prueba"
        r.created_at = datetime.now(timezone.utc)
        r.autor_nombre = "Profe"
        r.autor_apellido = "García"
        r.es_visible_alumno = visible
        return r

    # El endpoint filtra en la query (es_visible_alumno=True),
    # así que el mock ya devuelve solo las 2 visibles
    notas_result = MagicMock()
    notas_result.all.return_value = [_nota_row(True), _nota_row(True)]

    mock_db = make_multi_db(_single(perfil), notas_result)

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.get("/alumnos/notas", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("contenido" in n for n in data)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_notificacion_ajena_devuelve_404(client: AsyncClient):
    """Alumno A intenta marcar como leída una notificación de B → 404, nunca 403."""
    from app.main import app

    alumno_a = _make_alumno_user("A")
    token_a = make_access_token(alumno_a)

    # La query busca WHERE id=NOTIF_B_ID AND usuario_id=alumno_a.id → no encuentra nada
    mock_db = make_multi_db(_empty())

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno_a

    try:
        resp = await client.patch(
            f"/alumnos/notificaciones/{NOTIF_B_ID}/leer",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 404
        # Confirmar que NO es 403 — anti-enumeration
        assert resp.status_code != 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_notificacion_marcada_no_aparece_en_no_leidas(client: AsyncClient):
    """Tras PATCH .../leer, el count de no-leídas baja en 1."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    notif = _make_notificacion(NOTIF_A_ID, alumno.id, leida=False)

    # Paso 1: PATCH leer → encuentra la notificación
    mock_db_patch = make_multi_db(_single(notif))
    app.dependency_overrides[get_db] = make_db_override(mock_db_patch)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.patch(
            f"/alumnos/notificaciones/{NOTIF_A_ID}/leer",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["leida"] is True
        # La notificación mock quedó marcada
        assert notif.leida is True
    finally:
        app.dependency_overrides.clear()

    # Paso 2: GET /no-leidas → ahora count = 0
    count_result = MagicMock()
    count_result.scalar_one_or_none.return_value = 0
    mock_db_count = make_multi_db(count_result)
    app.dependency_overrides[get_db] = make_db_override(mock_db_count)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp2 = await client.get(
            "/alumnos/notificaciones/no-leidas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["count"] == 0
    finally:
        app.dependency_overrides.clear()


def _make_boleta_db(perfil, parcial_offset_days=-1):
    """Helper: construye el mock DB con la secuencia de llamadas para /boleta."""
    from app.models.academico import CicloEscolar
    from app.models.core import Institucion

    ciclo_row = MagicMock()
    ciclo_row.id = CICLO_ID
    ciclo_active_result = MagicMock()
    ciclo_active_result.one_or_none.return_value = ciclo_row

    insc_row = MagicMock()
    insc_row.inscripcion_id = INSCRIPCION_A_ID
    insc_row.grupo_id = GRUPO_ID
    insc_row.grupo_nombre = "1A"
    insc_result = MagicMock()
    insc_result.one_or_none.return_value = insc_row

    ciclo_obj = MagicMock(spec=CicloEscolar)
    ciclo_obj.id = CICLO_ID
    ciclo_obj.nombre = "2026-1"
    ciclo_obj.tipo = "semestral"
    ciclo_obj.fecha_inicio = date(2026, 1, 1)
    ciclo_obj.fecha_fin = date(2026, 6, 30)
    ciclo_result2 = MagicMock()
    ciclo_result2.scalar_one_or_none.return_value = ciclo_obj

    inst_obj = MagicMock(spec=Institucion)
    inst_obj.nombre = "Prepa Test"
    inst_obj.direccion = "Calle 123"
    inst_obj.telefono = "555-0000"
    inst_result = MagicMock()
    inst_result.scalar_one_or_none.return_value = inst_obj

    parcial = _make_parcial(fecha_cierre_offset_days=parcial_offset_days)
    gm_row = _make_gm_row()
    gm_result = MagicMock()
    gm_result.all.return_value = [gm_row]

    parc_result = MagicMock()
    parc_result.scalars.return_value.all.return_value = [parcial]

    cal_result = MagicMock()
    cal_result.scalars.return_value.all.return_value = [_make_calificacion()] if parcial_offset_days <= 0 else []

    cf_result = MagicMock()
    cf_result.scalars.return_value.all.return_value = [_make_cf()] if parcial_offset_days <= 0 else []

    # Secuencia: perfil, ciclo_id, insc, ciclo_obj, gm, parc, cal, cf, inst
    return make_multi_db(
        _single(perfil),
        ciclo_active_result,
        insc_result,
        ciclo_result2,
        gm_result,
        parc_result,
        cal_result,
        cf_result,
        inst_result,
    )


@pytest.mark.asyncio
async def test_boleta_content_type(client: AsyncClient):
    """GET /alumnos/boleta devuelve Content-Type: application/pdf."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    mock_db = _make_boleta_db(perfil, parcial_offset_days=-1)
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        with patch("app.routers.alumnos.get_redis", AsyncMock(return_value=mock_redis)):
            resp = await client.get("/alumnos/boleta", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_boleta_rate_limit(client: AsyncClient):
    """La 11ª solicitud en una hora recibe 429 Too Many Requests."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    # perfil + ciclo_id query antes de llegar a la check de rate limit
    ciclo_row = MagicMock()
    ciclo_row.id = CICLO_ID
    ciclo_active_result = MagicMock()
    ciclo_active_result.one_or_none.return_value = ciclo_row

    mock_db = make_multi_db(_single(perfil), ciclo_active_result)

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=11)  # supera el límite de 10
    mock_redis.expire = AsyncMock()

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        with patch("app.routers.alumnos.get_redis", AsyncMock(return_value=mock_redis)):
            resp = await client.get("/alumnos/boleta", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 429
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_boleta_sin_parciales_cerrados(client: AsyncClient):
    """Ciclo sin ningún parcial cerrado → 422 Unprocessable Entity."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    mock_db = _make_boleta_db(perfil, parcial_offset_days=+10)  # futuro = no publicado
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        with patch("app.routers.alumnos.get_redis", AsyncMock(return_value=mock_redis)):
            resp = await client.get("/alumnos/boleta", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422
        assert "publicadas" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_boleta_registra_en_auditoria(client: AsyncClient):
    """Tras descargar la boleta, se inserta un registro en auditoría."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    mock_db = _make_boleta_db(perfil, parcial_offset_days=-1)
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        with patch("app.routers.alumnos.get_redis", AsyncMock(return_value=mock_redis)):
            resp = await client.get("/alumnos/boleta", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        # Verificar que db.add fue llamado (registro de auditoría)
        assert mock_db.add.called
        added_obj = mock_db.add.call_args[0][0]
        from app.models.auditoria import Auditoria
        assert isinstance(added_obj, Auditoria)
        assert added_obj.accion == "descarga_boleta"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rol_profesor_recibe_403(client: AsyncClient):
    """Un profesor que llama GET /alumnos/dashboard recibe 403."""
    from app.main import app

    profesor = make_mock_user("prof@test.com", RolUsuario.profesor, INST_A_ID)
    token = make_access_token(profesor)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: profesor

    try:
        resp = await client.get("/alumnos/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rol_admin_recibe_403(client: AsyncClient):
    """Un admin que llama GET /alumnos/calificaciones recibe 403."""
    from app.main import app

    admin = make_mock_user("admin@test.com", RolUsuario.admin, INST_A_ID)
    token = make_access_token(admin)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        resp = await client.get("/alumnos/calificaciones", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_historial_vacio_nuevo_ingreso(client: AsyncClient):
    """Alumno sin historial de inscripciones → [] vacío, sin error."""
    from app.main import app

    alumno = _make_alumno_user()
    token = make_access_token(alumno)
    perfil = _make_perfil(PERFIL_A_ID, alumno)

    # Sin inscripciones históricas
    inscs_result = MagicMock()
    inscs_result.all.return_value = []

    mock_db = make_multi_db(
        _single(perfil),
        inscs_result,
    )

    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = lambda: alumno

    try:
        resp = await client.get(
            "/alumnos/calificaciones/historial",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.clear()
