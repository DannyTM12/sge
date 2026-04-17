"""
Tests del módulo administrador — SGE.
Cubre: grupos, materias, inscripciones, parciales, calificaciones, tenant isolation y RBAC.
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.academico import (
    CicloEscolar,
    Grupo,
    GrupoMateria,
    Inscripcion,
    Materia,
)
from app.models.core import RolUsuario
from app.models.evaluaciones import CalificacionFinal, Parcial

from tests.conftest import (
    INST_A_ID,
    INST_B_ID,
    make_db_override,
    make_mock_db,
    make_mock_user,
)

# ── Fixtures específicos del módulo admin ─────────────────────────────────────

CICLO_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
GRUPO_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
MATERIA_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
GM_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
INSCRIPCION_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
PARCIAL_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")
CF_ID = uuid.UUID("70000000-0000-0000-0000-000000000001")
ALUMNO_PERFIL_ID = uuid.UUID("80000000-0000-0000-0000-000000000001")
PROFESOR_ID = uuid.UUID("90000000-0000-0000-0000-000000000001")


def _make_ciclo(institucion_id=INST_A_ID):
    c = MagicMock(spec=CicloEscolar)
    c.id = CICLO_ID
    c.institucion_id = institucion_id
    c.nombre = "2024-1"
    c.activo = True
    return c


def _make_grupo(institucion_id=INST_A_ID):
    g = MagicMock(spec=Grupo)
    g.id = GRUPO_ID
    g.institucion_id = institucion_id
    g.ciclo_escolar_id = CICLO_ID
    g.nombre = "1-A"
    g.tipo_periodo = "semestral"
    g.turno = "matutino"
    g.capacidad_maxima = 30
    g.activo = True
    g.created_at = None
    return g


def _make_materia(institucion_id=INST_A_ID):
    m = MagicMock(spec=Materia)
    m.id = MATERIA_ID
    m.institucion_id = institucion_id
    m.nombre = "Matemáticas"
    m.clave = "MAT101"
    m.creditos = 5
    m.activa = True
    m.created_at = None
    return m


def _make_gm():
    gm = MagicMock(spec=GrupoMateria)
    gm.id = GM_ID
    gm.grupo_id = GRUPO_ID
    gm.materia_id = MATERIA_ID
    gm.num_parciales = 3
    gm.created_at = None
    return gm


def _make_inscripcion(activa=True, grupo_id=GRUPO_ID, alumno_id=ALUMNO_PERFIL_ID):
    ins = MagicMock(spec=Inscripcion)
    ins.id = INSCRIPCION_ID
    ins.alumno_id = alumno_id
    ins.grupo_id = grupo_id
    ins.ciclo_escolar_id = CICLO_ID
    ins.fecha_inscripcion = date.today()
    ins.activa = activa
    ins.created_at = None
    return ins


def _make_parcial(activo=True):
    p = MagicMock(spec=Parcial)
    p.id = PARCIAL_ID
    p.grupo_materia_id = GM_ID
    p.numero = 1
    p.nombre = "Primer parcial"
    p.fecha_apertura = None
    p.fecha_cierre = None
    p.activo = activo
    p.created_at = None
    return p


def _make_cf():
    cf = MagicMock(spec=CalificacionFinal)
    cf.id = CF_ID
    cf.inscripcion_id = INSCRIPCION_ID
    cf.materia_id = MATERIA_ID
    cf.calificacion_calculada = Decimal("8.00")
    cf.calificacion_final = Decimal("8.00")
    cf.fue_modificada_manualmente = False
    cf.modificado_por = None
    cf.fecha_modificacion = None
    cf.created_at = None
    cf.updated_at = None
    return cf


def _override_user(user):
    """Devuelve un override simple que retorna el usuario dado."""
    def _dep():
        return user
    return _dep


def _set_overrides(admin_user, mock_db):
    """Aplica dependency_overrides al app y devuelve un callable cleanup."""
    from app.main import app
    app.dependency_overrides[get_db] = make_db_override(mock_db)
    app.dependency_overrides[get_current_user] = _override_user(admin_user)

    def cleanup():
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    return cleanup


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Crear grupo y asignar materia exitosamente
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_grupo_exitoso(client: AsyncClient, admin_user):
    """POST /admin/grupos devuelve 201 con los datos del grupo creado."""
    ciclo = _make_ciclo()
    # DB: 1) verificar ciclo existente
    mock_db = make_mock_db(side_effects=[ciclo])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.post(
            "/admin/grupos",
            json={
                "nombre": "1-A",
                "ciclo_escolar_id": str(CICLO_ID),
                "tipo_periodo": "semestral",
                "turno": "matutino",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "1-A"
    assert data["turno"] == "matutino"


@pytest.mark.asyncio
async def test_asignar_materia_a_grupo(client: AsyncClient, admin_user):
    """POST /admin/grupos/{id}/materias crea la relación grupo-materia."""
    grupo = _make_grupo()
    materia = _make_materia()
    # DB calls: 1) get grupo, 2) get materia, 3) check existing gm (None)
    mock_db = make_mock_db(side_effects=[grupo, materia, None])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.post(
            f"/admin/grupos/{GRUPO_ID}/materias",
            json={
                "grupo_id": str(GRUPO_ID),
                "materia_id": str(MATERIA_ID),
                "num_parciales": 3,
            },
        )
    finally:
        cleanup()

    assert response.status_code == 201
    data = response.json()
    assert data["materia_id"] == str(MATERIA_ID)
    assert data["materia_nombre"] == "Matemáticas"


@pytest.mark.asyncio
async def test_asignar_materia_duplicada_devuelve_409(client: AsyncClient, admin_user):
    """Asignar la misma materia dos veces al mismo grupo devuelve 409."""
    grupo = _make_grupo()
    materia = _make_materia()
    gm_existente = _make_gm()
    # DB: 1) get grupo, 2) get materia, 3) check existing gm → ya existe
    mock_db = make_mock_db(side_effects=[grupo, materia, gm_existente])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.post(
            f"/admin/grupos/{GRUPO_ID}/materias",
            json={
                "grupo_id": str(GRUPO_ID),
                "materia_id": str(MATERIA_ID),
                "num_parciales": 3,
            },
        )
    finally:
        cleanup()

    assert response.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Inscribir alumno a grupo
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inscribir_alumno_exitoso(client: AsyncClient, admin_user):
    """POST /admin/inscripciones crea la inscripción y devuelve 201."""
    from app.models.core import PerfilAlumno, Usuario as UsuarioModel

    # Mocks de perfil y usuario del alumno
    perfil_alumno = MagicMock(spec=PerfilAlumno)
    perfil_alumno.id = ALUMNO_PERFIL_ID
    perfil_alumno.usuario_id = uuid.uuid4()

    usuario_alumno = MagicMock(spec=UsuarioModel)
    usuario_alumno.nombre = "Juan"
    usuario_alumno.apellido_paterno = "García"

    grupo = _make_grupo()
    grupo.ciclo_escolar_id = CICLO_ID

    # DB calls:
    # 1) verificar perfil_alumno (JOIN usuario)
    # 2) verificar grupo
    # 3) verificar inscripción duplicada → None
    # 4) obtener usuario para el nombre
    mock_db = make_mock_db(side_effects=[perfil_alumno, grupo, None, usuario_alumno])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.post(
            "/admin/inscripciones",
            json={
                "alumno_id": str(ALUMNO_PERFIL_ID),
                "grupo_id": str(GRUPO_ID),
            },
        )
    finally:
        cleanup()

    assert response.status_code == 201
    data = response.json()
    assert data["alumno_id"] == str(ALUMNO_PERFIL_ID)
    assert data["grupo_id"] == str(GRUPO_ID)
    assert data["activa"] is True
    assert "Juan García" in data["alumno_nombre_completo"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Transferir alumno entre grupos
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transferir_alumno_entre_grupos(client: AsyncClient, admin_user):
    """
    PATCH /admin/inscripciones/{id}/transferir debe:
    - Marcar la inscripción anterior como inactiva
    - Crear una nueva inscripción activa en el grupo destino
    """
    GRUPO_B_ID = uuid.uuid4()
    inscripcion_actual = _make_inscripcion(activa=True)

    grupo_destino = MagicMock(spec=Grupo)
    grupo_destino.id = GRUPO_B_ID
    grupo_destino.institucion_id = INST_A_ID
    grupo_destino.ciclo_escolar_id = CICLO_ID

    # DB calls:
    # 1) get inscripcion_actual (JOIN grupo)
    # 2) get grupo_destino
    mock_db = make_mock_db(side_effects=[inscripcion_actual, grupo_destino])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.patch(
            f"/admin/inscripciones/{INSCRIPCION_ID}/transferir",
            json={"nuevo_grupo_id": str(GRUPO_B_ID)},
        )
    finally:
        cleanup()

    assert response.status_code == 200
    data = response.json()
    # La nueva inscripción debe apuntar al grupo destino
    assert data["grupo_id"] == str(GRUPO_B_ID)
    assert data["activa"] is True

    # Verificar que la inscripción anterior fue marcada como inactiva
    assert inscripcion_actual.activa is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Crear parcial y cerrarlo → calificación final calculada
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_crear_parcial(client: AsyncClient, admin_user):
    """POST /admin/parciales crea el parcial y devuelve 201."""
    gm = _make_gm()
    # DB call: 1) verificar grupo_materia
    mock_db = make_mock_db(side_effects=[gm])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.post(
            "/admin/parciales",
            json={
                "grupo_materia_id": str(GM_ID),
                "numero": 1,
                "nombre": "Primer parcial",
            },
        )
    finally:
        cleanup()

    assert response.status_code == 201
    data = response.json()
    assert data["numero"] == 1
    assert data["activo"] is True


@pytest.mark.asyncio
async def test_cerrar_parcial_dispara_recalculo(client: AsyncClient, admin_user):
    """
    PATCH /admin/parciales/{id}/cerrar cierra el parcial y llama a
    recalcular_y_guardar para cada inscripción activa del grupo.
    """
    parcial = _make_parcial(activo=True)
    gm = _make_gm()
    inscripcion = _make_inscripcion()

    # DB calls:
    # 1) get parcial (JOIN gm → JOIN grupo)
    # 2) get grupo_materia
    # 3) get inscripciones activas del grupo
    mock_db = make_mock_db(side_effects=[parcial, gm])

    # Configurar el mock para que la lista de inscripciones devuelva una
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [inscripcion]
    extra_result = MagicMock()
    extra_result.scalars.return_value = scalars_mock
    mock_db.execute.side_effect = [
        _make_scalar_result(parcial),
        _make_scalar_result(gm),
        extra_result,
    ]

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        with patch(
            "app.routers.admin.recalcular_y_guardar",
            new_callable=AsyncMock,
        ) as mock_recalc:
            response = await client.patch(f"/admin/parciales/{PARCIAL_ID}/cerrar")
    finally:
        cleanup()

    assert response.status_code == 200
    data = response.json()
    assert data["activo"] is False

    # Debe haberse llamado recalcular_y_guardar para el alumno inscrito
    mock_recalc.assert_called_once_with(
        inscripcion_id=inscripcion.id,
        materia_id=gm.materia_id,
        grupo_materia_id=gm.id,
        db=mock_db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Override de calificación final genera auditoría
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_override_calificacion_genera_auditoria(client: AsyncClient, admin_user):
    """
    PATCH /admin/calificaciones-finales/{id} actualiza la calificación final
    y llama a registrar_auditoria con los valores anterior y nuevo.
    """
    cf = _make_cf()

    # DB call: 1) get CalificacionFinal (JOIN inscripcion → grupo)
    mock_db = make_mock_db(side_effects=[cf])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        with patch("app.routers.admin.registrar_auditoria", new_callable=AsyncMock) as mock_audit:
            response = await client.patch(
                f"/admin/calificaciones-finales/{CF_ID}",
                json={"calificacion_final": "9.50"},
            )
    finally:
        cleanup()

    assert response.status_code == 200
    data = response.json()
    assert data["fue_modificada_manualmente"] is True

    # Verificar que se llamó registrar_auditoria
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args.kwargs
    assert call_kwargs["accion"] == "override_calificacion_final"
    assert call_kwargs["tabla"] == "calificaciones_finales"
    assert call_kwargs["valor_anterior"]["calificacion_final"] == "8.00"
    assert Decimal(call_kwargs["valor_nuevo"]["calificacion_final"]) == Decimal("9.50")


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Tenant isolation — admin de institución A no accede a datos de B
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_inst_a_no_puede_ver_grupo_inst_b(client: AsyncClient, admin_user):
    """
    Un admin de la institución A buscando un grupo de la institución B
    debe recibir 404 (el query filtra por tenant_id y no encuentra el recurso).
    """
    # La consulta filtra por tenant_id = INST_A_ID, y el grupo pertenece a INST_B_ID
    # → el mock devuelve None (el grupo no existe para ese tenant)
    mock_db = make_mock_db(side_effects=[None])  # grupo not found for tenant A

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.get(f"/admin/grupos/{GRUPO_ID}")
    finally:
        cleanup()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_inst_a_no_puede_cerrar_ciclo_inst_b(client: AsyncClient, admin_user):
    """PATCH /admin/ciclos/{id}/cerrar devuelve 404 si el ciclo es de otra institución."""
    # El ciclo pertenece a inst B, la query filtra por inst A → no encontrado
    mock_db = make_mock_db(side_effects=[None])

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.patch(f"/admin/ciclos/{CICLO_ID}/cerrar")
    finally:
        cleanup()

    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Rol profesor intenta acceder a /admin/* → recibe 403
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profesor_no_puede_acceder_a_admin(client: AsyncClient, profesor_user):
    """Un usuario con rol 'profesor' debe recibir 403 en cualquier endpoint /admin."""
    mock_db = make_mock_db()
    cleanup = _set_overrides(profesor_user, mock_db)
    try:
        response = await client.get("/admin/grupos")
    finally:
        cleanup()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_alumno_no_puede_acceder_a_admin(client: AsyncClient, alumno_user):
    """Un alumno también debe recibir 403."""
    mock_db = make_mock_db()
    cleanup = _set_overrides(alumno_user, mock_db)
    try:
        response = await client.post(
            "/admin/materias",
            json={"nombre": "Física"},
        )
    finally:
        cleanup()

    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Tests de la capa de servicios (sin HTTP)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calcular_calificacion_final_sin_calificaciones():
    """Si no hay calificaciones, calcular_calificacion_final devuelve None."""
    from app.services.calificaciones_service import calcular_calificacion_final

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_mock

    resultado = await calcular_calificacion_final(INSCRIPCION_ID, GM_ID, mock_db)
    assert resultado is None


@pytest.mark.asyncio
async def test_calcular_calificacion_final_con_promedio():
    """calcular_calificacion_final devuelve el promedio como Decimal."""
    from app.services.calificaciones_service import calcular_calificacion_final

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = 8.5
    mock_db.execute.return_value = result_mock

    resultado = await calcular_calificacion_final(INSCRIPCION_ID, GM_ID, mock_db)
    assert resultado == Decimal("8.50")


@pytest.mark.asyncio
async def test_recalcular_no_sobreescribe_modificacion_manual():
    """
    recalcular_y_guardar no debe tocar calificacion_final si fue_modificada_manualmente = True.
    """
    from app.services.calificaciones_service import recalcular_y_guardar

    cf = _make_cf()
    cf.fue_modificada_manualmente = True
    cf.calificacion_final = Decimal("10.00")

    mock_db = AsyncMock()
    # Primera execute: avg → 7.0
    avg_result = MagicMock()
    avg_result.scalar_one_or_none.return_value = 7.0
    # Segunda execute: get CalificacionFinal existente
    cf_result = MagicMock()
    cf_result.scalar_one_or_none.return_value = cf
    mock_db.execute.side_effect = [avg_result, cf_result]

    await recalcular_y_guardar(INSCRIPCION_ID, MATERIA_ID, GM_ID, mock_db)

    # calificacion_calculada debe actualizarse
    assert cf.calificacion_calculada == Decimal("7.00")
    # calificacion_final NO debe cambiar (fue modificada manualmente)
    assert cf.calificacion_final == Decimal("10.00")


@pytest.mark.asyncio
async def test_recalcular_sincroniza_cuando_no_es_manual():
    """Si fue_modificada_manualmente = False, ambas columnas deben sincronizarse."""
    from app.services.calificaciones_service import recalcular_y_guardar

    cf = _make_cf()
    cf.fue_modificada_manualmente = False
    cf.calificacion_final = Decimal("8.00")

    mock_db = AsyncMock()
    avg_result = MagicMock()
    avg_result.scalar_one_or_none.return_value = 9.0
    cf_result = MagicMock()
    cf_result.scalar_one_or_none.return_value = cf
    mock_db.execute.side_effect = [avg_result, cf_result]

    await recalcular_y_guardar(INSCRIPCION_ID, MATERIA_ID, GM_ID, mock_db)

    assert cf.calificacion_calculada == Decimal("9.00")
    assert cf.calificacion_final == Decimal("9.00")


# ─────────────────────────────────────────────────────────────────────────────
# Test dashboard
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_devuelve_estructura_correcta(client: AsyncClient, admin_user):
    """GET /admin/dashboard devuelve las 6 métricas esperadas."""
    mock_db = make_mock_db()
    # db.scalar() es llamado 6 veces para las agregaciones
    mock_db.scalar.side_effect = [50, 10, 8, 7.8, 0, 5, 3, 2]

    cleanup = _set_overrides(admin_user, mock_db)
    try:
        response = await client.get("/admin/dashboard")
    finally:
        cleanup()

    assert response.status_code == 200
    data = response.json()
    assert "total_alumnos" in data
    assert "total_grupos" in data
    assert "total_profesores" in data
    assert "promedio_institucional" in data
    assert "porcentaje_riesgo" in data
    assert "alertas_no_leidas" in data


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos del test
# ─────────────────────────────────────────────────────────────────────────────

def _make_scalar_result(value):
    """Helper para crear un mock de resultado de db.execute() con scalar_one_or_none()."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r
