"""
Router de alumnos — /alumnos/*.
Toda la información es de solo lectura y siempre del alumno autenticado.
PRINCIPIO DE SEGURIDAD: alumno_id NUNCA viene por parámetro, siempre del token.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.middleware.rbac import require_roles
from app.middleware.tenant import get_tenant_id
from app.models.academico import (
    CicloEscolar,
    Grupo,
    GrupoMateria,
    Inscripcion,
    Materia,
    ProfesorGrupoMateria,
)
from app.models.asistencias import Asistencia, EstadoAsistencia, Justificante, SesionClase
from app.models.auditoria import Auditoria
from app.models.core import PerfilAlumno, Usuario
from app.models.evaluaciones import Calificacion, CalificacionFinal, Parcial
from app.models.ia import Notificacion
from app.models.notas import DiaSemana, Horario, NotaAlumno
from app.schemas.alumno import (
    DashboardAlumnoRead,
    HistorialCicloRead,
    MiAsistenciaRead,
    MiCalificacionParcialRead,
    MiHorarioRead,
    MiMateriaRead,
    MiNotaRead,
    NotificacionRead,
    ResumenAsistenciaRead,
)
from app.services.pdf_service import generar_boleta
from app.utils.audit import registrar_auditoria

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])

# ── Constantes ────────────────────────────────────────────────────────────────

_DIA_ORDEN = {
    DiaSemana.lunes: 0,
    DiaSemana.martes: 1,
    DiaSemana.miercoles: 2,
    DiaSemana.jueves: 3,
    DiaSemana.viernes: 4,
    DiaSemana.sabado: 5,
}

_BOLETA_RATE_LIMIT = 10
_BOLETA_WINDOW_SECS = 3600


# ── Helpers internos ──────────────────────────────────────────────────────────


async def _get_perfil(db: AsyncSession, current_user: Usuario) -> PerfilAlumno:
    """Resuelve el PerfilAlumno del usuario autenticado. 404 si no existe."""
    result = await db.execute(
        select(PerfilAlumno).where(PerfilAlumno.usuario_id == current_user.id)
    )
    perfil = result.scalar_one_or_none()
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil de alumno no encontrado")
    return perfil


def _nombre_completo(user: Usuario) -> str:
    partes = [user.nombre, user.apellido_paterno]
    if user.apellido_materno:
        partes.append(user.apellido_materno)
    return " ".join(partes)


def _is_publicado(parcial: Parcial, now: datetime) -> bool:
    """Regla de visibilidad: publicado sólo si fecha_cierre existe y ya pasó."""
    return parcial.fecha_cierre is not None and parcial.fecha_cierre <= now


async def _get_materias_del_ciclo(
    inscripcion_id: uuid.UUID,
    grupo_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    now: datetime,
) -> list[MiMateriaRead]:
    """
    Construye la lista de MiMateriaRead para una inscripción.
    Hace exactamente 4 execute() calls (gm_rows, parciales, calificaciones, cfs).
    """
    # ── Query 1: grupo_materias con materia y profesor ────────────────────────
    r1 = await db.execute(
        select(
            GrupoMateria.id.label("gm_id"),
            GrupoMateria.materia_id,
            GrupoMateria.num_parciales,
            Materia.nombre.label("materia_nombre"),
            Materia.clave,
            Usuario.nombre.label("prof_nombre"),
            Usuario.apellido_paterno.label("prof_apellido"),
        )
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .outerjoin(
            ProfesorGrupoMateria,
            (ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
            & (ProfesorGrupoMateria.activo.is_(True)),
        )
        .outerjoin(Usuario, ProfesorGrupoMateria.usuario_id == Usuario.id)
        .where(
            GrupoMateria.grupo_id == grupo_id,
            Materia.institucion_id == tenant_id,
        )
    )
    gm_rows_raw = r1.all()

    # Deduplicar por gm_id (outer join puede producir múltiples filas por profesor)
    seen: set[uuid.UUID] = set()
    gm_rows = []
    for row in gm_rows_raw:
        if row.gm_id not in seen:
            seen.add(row.gm_id)
            gm_rows.append(row)

    if not gm_rows:
        return []

    gm_ids = [row.gm_id for row in gm_rows]

    # ── Query 2: parciales ────────────────────────────────────────────────────
    r2 = await db.execute(
        select(Parcial)
        .where(Parcial.grupo_materia_id.in_(gm_ids))
        .order_by(Parcial.grupo_materia_id, Parcial.numero)
    )
    parciales = r2.scalars().all()
    parciales_by_gm: dict[uuid.UUID, list[Parcial]] = {}
    for p in parciales:
        parciales_by_gm.setdefault(p.grupo_materia_id, []).append(p)

    # ── Query 3: calificaciones ───────────────────────────────────────────────
    r3 = await db.execute(
        select(Calificacion).where(Calificacion.inscripcion_id == inscripcion_id)
    )
    cal_by_parcial: dict[uuid.UUID, Calificacion] = {
        c.parcial_id: c for c in r3.scalars().all()
    }

    # ── Query 4: calificaciones_finales ───────────────────────────────────────
    r4 = await db.execute(
        select(CalificacionFinal).where(CalificacionFinal.inscripcion_id == inscripcion_id)
    )
    cf_by_materia: dict[uuid.UUID, CalificacionFinal] = {
        cf.materia_id: cf for cf in r4.scalars().all()
    }

    # ── Construir resultado ───────────────────────────────────────────────────
    result: list[MiMateriaRead] = []
    for row in gm_rows:
        prof = None
        if row.prof_nombre:
            prof = f"{row.prof_nombre} {row.prof_apellido}".strip()

        parciales_read: list[MiCalificacionParcialRead] = []
        for p in parciales_by_gm.get(row.gm_id, []):
            publicado = _is_publicado(p, now)
            if publicado:
                cal = cal_by_parcial.get(p.id)
                parciales_read.append(
                    MiCalificacionParcialRead(
                        parcial_numero=p.numero,
                        parcial_nombre=p.nombre,
                        calificacion=cal.calificacion if cal else None,
                        fecha_registro=cal.updated_at if cal else None,
                        esta_publicada=True,
                    )
                )
            else:
                parciales_read.append(
                    MiCalificacionParcialRead(
                        parcial_numero=p.numero,
                        parcial_nombre=p.nombre,
                        calificacion=None,
                        fecha_registro=None,
                        esta_publicada=False,
                    )
                )

        cf = cf_by_materia.get(row.materia_id)
        result.append(
            MiMateriaRead(
                materia_id=row.materia_id,
                materia_nombre=row.materia_nombre,
                clave=row.clave,
                profesor_nombre=prof,
                num_parciales=row.num_parciales,
                parciales=parciales_read,
                calificacion_calculada=cf.calificacion_calculada if cf else None,
                calificacion_final=cf.calificacion_final if cf else None,
                fue_modificada_manualmente=cf.fue_modificada_manualmente if cf else False,
            )
        )

    return result


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardAlumnoRead)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> DashboardAlumnoRead:
    """Resumen completo del alumno: calificaciones, riesgo y notificaciones."""
    # 1. Perfil
    perfil = await _get_perfil(db, current_user)
    nombre = _nombre_completo(current_user)

    # 2. Inscripción activa con grupo y ciclo
    r_insc = await db.execute(
        select(
            Inscripcion.id.label("inscripcion_id"),
            Inscripcion.grupo_id,
            Grupo.nombre.label("grupo_nombre"),
            CicloEscolar.id.label("ciclo_id"),
            CicloEscolar.nombre.label("ciclo_nombre"),
        )
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.activo.is_(True),
            Grupo.institucion_id == tenant_id,
        )
    )
    insc = r_insc.one_or_none()

    # 3. Notificaciones no leídas (siempre se cuenta)
    r_notif = await db.execute(
        select(func.count(Notificacion.id)).where(
            Notificacion.usuario_id == current_user.id,
            Notificacion.leida.is_(False),
        )
    )
    notif_count: int = r_notif.scalar_one_or_none() or 0

    if insc is None:
        return DashboardAlumnoRead(
            nombre_completo=nombre,
            matricula=perfil.matricula,
            grupo_nombre=None,
            ciclo_nombre=None,
            ciclo_id=None,
            promedio_general=None,
            materias_en_riesgo=0,
            alertas_no_leidas=notif_count,
            materias=[],
        )

    now = datetime.now(timezone.utc)
    # 4-7. Materias (4 queries internas)
    materias = await _get_materias_del_ciclo(
        insc.inscripcion_id, insc.grupo_id, tenant_id, db, now
    )

    # 8. Estadísticas de asistencia por grupo_materia (para materias_en_riesgo)
    r_asist = await db.execute(
        select(
            SesionClase.grupo_materia_id,
            Asistencia.estado,
            func.count(Asistencia.id).label("cnt"),
        )
        .join(SesionClase, Asistencia.sesion_id == SesionClase.id)
        .where(
            Asistencia.alumno_id == perfil.id,
            SesionClase.grupo_materia_id.in_(
                select(GrupoMateria.id).where(GrupoMateria.grupo_id == insc.grupo_id)
            ),
        )
        .group_by(SesionClase.grupo_materia_id, Asistencia.estado)
    )
    asist_rows = r_asist.all()

    # asist_stats: {gm_id -> {estado -> count}}
    asist_stats: dict[uuid.UUID, dict[str, int]] = {}
    for row in asist_rows:
        asist_stats.setdefault(row.grupo_materia_id, {})[row.estado] = row.cnt

    # Calcular promedio_general y materias_en_riesgo
    califs_finales = [m.calificacion_final for m in materias if m.calificacion_final is not None]
    if califs_finales:
        promedio = Decimal(str(sum(califs_finales) / len(califs_finales))).quantize(Decimal("0.01"))
    else:
        promedio = None

    materias_en_riesgo = 0
    # Para el riesgo necesitamos mapear materia_id → gm_id; lo hacemos vía una query rápida
    # pero para no agregar más queries, calculamos sólo con calificacion_final < 6
    # y marcamos "sin final" siempre como neutro (asistencia check en dashboard simplificado)
    for m in materias:
        if m.calificacion_final is not None and m.calificacion_final < Decimal("6"):
            materias_en_riesgo += 1

    return DashboardAlumnoRead(
        nombre_completo=nombre,
        matricula=perfil.matricula,
        grupo_nombre=insc.grupo_nombre,
        ciclo_nombre=insc.ciclo_nombre,
        ciclo_id=insc.ciclo_id,
        promedio_general=promedio,
        materias_en_riesgo=materias_en_riesgo,
        alertas_no_leidas=notif_count,
        materias=materias,
    )


# ── Calificaciones ────────────────────────────────────────────────────────────


@router.get("/calificaciones", response_model=list[MiMateriaRead])
async def mis_calificaciones(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[MiMateriaRead]:
    """Calificaciones del ciclo activo con regla de visibilidad por fecha_cierre."""
    perfil = await _get_perfil(db, current_user)

    r_insc = await db.execute(
        select(Inscripcion.id.label("inscripcion_id"), Inscripcion.grupo_id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.activo.is_(True),
            Grupo.institucion_id == tenant_id,
        )
    )
    insc = r_insc.one_or_none()
    if insc is None:
        return []

    now = datetime.now(timezone.utc)
    return await _get_materias_del_ciclo(insc.inscripcion_id, insc.grupo_id, tenant_id, db, now)


@router.get("/calificaciones/historial", response_model=list[HistorialCicloRead])
async def historial_calificaciones(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[HistorialCicloRead]:
    """Historial de calificaciones agrupado por ciclo, ordenado descendente."""
    perfil = await _get_perfil(db, current_user)

    # Todas las inscripciones con ciclo y grupo
    r_inscs = await db.execute(
        select(
            Inscripcion.id.label("inscripcion_id"),
            Inscripcion.grupo_id,
            CicloEscolar.id.label("ciclo_id"),
            CicloEscolar.nombre.label("ciclo_nombre"),
            CicloEscolar.tipo.label("ciclo_tipo"),
            CicloEscolar.fecha_inicio,
            CicloEscolar.fecha_fin,
            CicloEscolar.activo.label("ciclo_activo"),
        )
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Grupo.institucion_id == tenant_id,
        )
        .order_by(CicloEscolar.fecha_inicio.desc())
    )
    insc_rows = r_inscs.all()
    if not insc_rows:
        return []

    insc_ids = [r.inscripcion_id for r in insc_rows]
    grupo_ids = list({r.grupo_id for r in insc_rows})

    # Batch: grupo_materias con materia y profesor para todos los grupos
    r_gm = await db.execute(
        select(
            GrupoMateria.id.label("gm_id"),
            GrupoMateria.grupo_id,
            GrupoMateria.materia_id,
            GrupoMateria.num_parciales,
            Materia.nombre.label("materia_nombre"),
            Materia.clave,
            Usuario.nombre.label("prof_nombre"),
            Usuario.apellido_paterno.label("prof_apellido"),
        )
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .outerjoin(
            ProfesorGrupoMateria,
            (ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
            & ProfesorGrupoMateria.activo.is_(True),
        )
        .outerjoin(Usuario, ProfesorGrupoMateria.usuario_id == Usuario.id)
        .where(
            GrupoMateria.grupo_id.in_(grupo_ids),
            Materia.institucion_id == tenant_id,
        )
    )
    # Deduplicar por gm_id
    seen_gm: set[uuid.UUID] = set()
    all_gm_rows = []
    for row in r_gm.all():
        if row.gm_id not in seen_gm:
            seen_gm.add(row.gm_id)
            all_gm_rows.append(row)

    gm_by_grupo: dict[uuid.UUID, list] = {}
    for row in all_gm_rows:
        gm_by_grupo.setdefault(row.grupo_id, []).append(row)

    all_gm_ids = [row.gm_id for row in all_gm_rows]

    # Batch: parciales
    r_parc = await db.execute(
        select(Parcial)
        .where(Parcial.grupo_materia_id.in_(all_gm_ids))
        .order_by(Parcial.grupo_materia_id, Parcial.numero)
    )
    parciales_by_gm: dict[uuid.UUID, list[Parcial]] = {}
    for p in r_parc.scalars().all():
        parciales_by_gm.setdefault(p.grupo_materia_id, []).append(p)

    # Batch: calificaciones
    r_cal = await db.execute(
        select(Calificacion).where(Calificacion.inscripcion_id.in_(insc_ids))
    )
    cal_by_insc_parcial: dict[tuple, Calificacion] = {}
    for c in r_cal.scalars().all():
        cal_by_insc_parcial[(c.inscripcion_id, c.parcial_id)] = c

    # Batch: calificaciones_finales
    r_cf = await db.execute(
        select(CalificacionFinal).where(CalificacionFinal.inscripcion_id.in_(insc_ids))
    )
    cf_by_insc_materia: dict[tuple, CalificacionFinal] = {}
    for cf in r_cf.scalars().all():
        cf_by_insc_materia[(cf.inscripcion_id, cf.materia_id)] = cf

    now = datetime.now(timezone.utc)
    from datetime import date as date_type
    today = date_type.today()

    historial: list[HistorialCicloRead] = []
    for insc in insc_rows:
        gm_rows = gm_by_grupo.get(insc.grupo_id, [])
        materias: list[MiMateriaRead] = []

        for row in gm_rows:
            prof = None
            if row.prof_nombre:
                prof = f"{row.prof_nombre} {row.prof_apellido}".strip()

            parciales_read: list[MiCalificacionParcialRead] = []
            for p in parciales_by_gm.get(row.gm_id, []):
                publicado = _is_publicado(p, now)
                cal = cal_by_insc_parcial.get((insc.inscripcion_id, p.id))
                parciales_read.append(
                    MiCalificacionParcialRead(
                        parcial_numero=p.numero,
                        parcial_nombre=p.nombre,
                        calificacion=cal.calificacion if (publicado and cal) else None,
                        fecha_registro=cal.updated_at if (publicado and cal) else None,
                        esta_publicada=publicado,
                    )
                )

            cf = cf_by_insc_materia.get((insc.inscripcion_id, row.materia_id))
            materias.append(
                MiMateriaRead(
                    materia_id=row.materia_id,
                    materia_nombre=row.materia_nombre,
                    clave=row.clave,
                    profesor_nombre=prof,
                    num_parciales=row.num_parciales,
                    parciales=parciales_read,
                    calificacion_calculada=cf.calificacion_calculada if cf else None,
                    calificacion_final=cf.calificacion_final if cf else None,
                    fue_modificada_manualmente=cf.fue_modificada_manualmente if cf else False,
                )
            )

        # Solo incluir ciclos cerrados o con calificaciones finales
        ciclo_cerrado = insc.fecha_fin < today
        tiene_cf = any(
            cf_by_insc_materia.get((insc.inscripcion_id, row.materia_id)) for row in gm_rows
        )
        if not ciclo_cerrado and not tiene_cf:
            continue

        califs = [m.calificacion_final for m in materias if m.calificacion_final is not None]
        promedio = (
            Decimal(str(sum(califs) / len(califs))).quantize(Decimal("0.01"))
            if califs
            else None
        )

        historial.append(
            HistorialCicloRead(
                ciclo_id=insc.ciclo_id,
                ciclo_nombre=insc.ciclo_nombre,
                ciclo_tipo=insc.ciclo_tipo,
                fecha_inicio=insc.fecha_inicio,
                fecha_fin=insc.fecha_fin,
                materias=materias,
                promedio_ciclo=promedio,
            )
        )

    return historial


# ── Asistencias ───────────────────────────────────────────────────────────────


@router.get("/asistencias", response_model=list[MiAsistenciaRead])
async def mis_asistencias(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[MiAsistenciaRead]:
    """Lista de asistencias del ciclo activo, ordenadas por fecha desc."""
    perfil = await _get_perfil(db, current_user)

    r_insc = await db.execute(
        select(Inscripcion.id.label("inscripcion_id"), Inscripcion.grupo_id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.activo.is_(True),
            Grupo.institucion_id == tenant_id,
        )
    )
    insc = r_insc.one_or_none()
    if insc is None:
        return []

    r_asist = await db.execute(
        select(
            SesionClase.fecha.label("sesion_fecha"),
            SesionClase.hora_inicio.label("sesion_hora_inicio"),
            Materia.nombre.label("materia_nombre"),
            Asistencia.estado,
            Asistencia.id.label("asistencia_id"),
        )
        .join(SesionClase, Asistencia.sesion_id == SesionClase.id)
        .join(GrupoMateria, SesionClase.grupo_materia_id == GrupoMateria.id)
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .where(
            Asistencia.alumno_id == perfil.id,
            GrupoMateria.grupo_id == insc.grupo_id,
        )
        .order_by(SesionClase.fecha.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = r_asist.all()

    # Justificantes en batch
    asist_ids = [r.asistencia_id for r in rows]
    justificantes_map: dict[uuid.UUID, str] = {}
    if asist_ids:
        r_just = await db.execute(
            select(Justificante.asistencia_id, Justificante.descripcion).where(
                Justificante.asistencia_id.in_(asist_ids)
            )
        )
        for just_row in r_just.all():
            if just_row.asistencia_id is not None:
                justificantes_map[just_row.asistencia_id] = just_row.descripcion

    return [
        MiAsistenciaRead(
            sesion_fecha=row.sesion_fecha,
            sesion_hora_inicio=row.sesion_hora_inicio,
            materia_nombre=row.materia_nombre,
            estado=row.estado,
            justificante_descripcion=justificantes_map.get(row.asistencia_id),
        )
        for row in rows
    ]


@router.get("/asistencias/resumen", response_model=list[ResumenAsistenciaRead])
async def resumen_asistencias(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[ResumenAsistenciaRead]:
    """Resumen de asistencias por materia, ordenado por porcentaje ascendente."""
    perfil = await _get_perfil(db, current_user)

    r_insc = await db.execute(
        select(Inscripcion.id.label("inscripcion_id"), Inscripcion.grupo_id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.activo.is_(True),
            Grupo.institucion_id == tenant_id,
        )
    )
    insc = r_insc.one_or_none()
    if insc is None:
        return []

    r_stats = await db.execute(
        select(
            GrupoMateria.materia_id,
            Materia.nombre.label("materia_nombre"),
            Asistencia.estado,
            func.count(Asistencia.id).label("cnt"),
        )
        .join(SesionClase, Asistencia.sesion_id == SesionClase.id)
        .join(GrupoMateria, SesionClase.grupo_materia_id == GrupoMateria.id)
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .where(
            Asistencia.alumno_id == perfil.id,
            GrupoMateria.grupo_id == insc.grupo_id,
        )
        .group_by(GrupoMateria.materia_id, Materia.nombre, Asistencia.estado)
    )
    rows = r_stats.all()

    # Agrupar por materia
    resumen: dict[uuid.UUID, dict] = {}
    for row in rows:
        mid = row.materia_id
        if mid not in resumen:
            resumen[mid] = {
                "materia_id": mid,
                "materia_nombre": row.materia_nombre,
                "presentes": 0,
                "ausentes": 0,
                "tardanzas": 0,
                "justificadas": 0,
            }
        estado = row.estado if isinstance(row.estado, str) else row.estado.value
        if estado == EstadoAsistencia.presente:
            resumen[mid]["presentes"] += row.cnt
        elif estado == EstadoAsistencia.ausente:
            resumen[mid]["ausentes"] += row.cnt
        elif estado == EstadoAsistencia.tardanza:
            resumen[mid]["tardanzas"] += row.cnt
        elif estado == EstadoAsistencia.justificada:
            resumen[mid]["justificadas"] += row.cnt

    result = []
    for d in resumen.values():
        total = d["presentes"] + d["ausentes"] + d["tardanzas"] + d["justificadas"]
        asistidos = d["presentes"] + d["tardanzas"] + d["justificadas"]
        pct = asistidos / total if total > 0 else None
        result.append(
            ResumenAsistenciaRead(
                materia_id=d["materia_id"],
                materia_nombre=d["materia_nombre"],
                total_sesiones=total,
                presentes=d["presentes"],
                ausentes=d["ausentes"],
                tardanzas=d["tardanzas"],
                justificadas=d["justificadas"],
                porcentaje_asistencia=pct,
            )
        )

    result.sort(key=lambda x: (x.porcentaje_asistencia is None, x.porcentaje_asistencia or 0))
    return result


# ── Horario ───────────────────────────────────────────────────────────────────


@router.get("/horario", response_model=list[MiHorarioRead])
async def mi_horario(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[MiHorarioRead]:
    """Horario del grupo activo, ordenado por día y hora."""
    perfil = await _get_perfil(db, current_user)

    r_insc = await db.execute(
        select(Inscripcion.grupo_id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.activo.is_(True),
            Grupo.institucion_id == tenant_id,
        )
    )
    insc = r_insc.one_or_none()
    if insc is None:
        return []

    r_horario = await db.execute(
        select(
            Horario.dia_semana,
            Horario.hora_inicio,
            Horario.hora_fin,
            Horario.aula,
            Materia.nombre.label("materia_nombre"),
            Usuario.nombre.label("prof_nombre"),
            Usuario.apellido_paterno.label("prof_apellido"),
        )
        .join(GrupoMateria, Horario.grupo_materia_id == GrupoMateria.id)
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .outerjoin(
            ProfesorGrupoMateria,
            (ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
            & ProfesorGrupoMateria.activo.is_(True),
        )
        .outerjoin(Usuario, ProfesorGrupoMateria.usuario_id == Usuario.id)
        .where(GrupoMateria.grupo_id == insc.grupo_id)
    )
    rows = r_horario.all()

    horarios = [
        MiHorarioRead(
            dia_semana=row.dia_semana if isinstance(row.dia_semana, str) else row.dia_semana.value,
            hora_inicio=row.hora_inicio,
            hora_fin=row.hora_fin,
            materia_nombre=row.materia_nombre,
            profesor_nombre=(
                f"{row.prof_nombre} {row.prof_apellido}".strip()
                if row.prof_nombre
                else None
            ),
            aula=row.aula,
        )
        for row in rows
    ]

    horarios.sort(
        key=lambda h: (
            _DIA_ORDEN.get(DiaSemana(h.dia_semana), 99),
            h.hora_inicio,
        )
    )
    return horarios


# ── Notas ─────────────────────────────────────────────────────────────────────


@router.get("/notas", response_model=list[MiNotaRead])
async def mis_notas(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[MiNotaRead]:
    """Notas visibles del alumno (es_visible_alumno=true), más recientes primero."""
    perfil = await _get_perfil(db, current_user)

    r_notas = await db.execute(
        select(
            NotaAlumno.contenido,
            NotaAlumno.created_at,
            Usuario.nombre.label("autor_nombre"),
            Usuario.apellido_paterno.label("autor_apellido"),
        )
        .join(Usuario, NotaAlumno.autor_id == Usuario.id)
        .where(
            NotaAlumno.alumno_id == perfil.id,
            NotaAlumno.institucion_id == tenant_id,
            NotaAlumno.es_visible_alumno.is_(True),
        )
        .order_by(NotaAlumno.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = r_notas.all()
    return [
        MiNotaRead(
            contenido=row.contenido,
            autor_nombre_completo=f"{row.autor_nombre} {row.autor_apellido}".strip(),
            created_at=row.created_at,
        )
        for row in rows
    ]


# ── Notificaciones ────────────────────────────────────────────────────────────


@router.get("/notificaciones/no-leidas", response_model=dict)
async def notificaciones_no_leidas_count(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
) -> dict:
    """Contador rápido de notificaciones no leídas — optimizado para polling (<50ms)."""
    r = await db.execute(
        select(func.count(Notificacion.id)).where(
            Notificacion.usuario_id == current_user.id,
            Notificacion.leida.is_(False),
        )
    )
    return {"count": r.scalar_one_or_none() or 0}


@router.patch("/notificaciones/marcar-todas-leidas", response_model=dict)
async def marcar_todas_leidas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
) -> dict:
    """Marca como leídas todas las notificaciones no leídas del alumno."""
    r = await db.execute(
        update(Notificacion)
        .where(
            Notificacion.usuario_id == current_user.id,
            Notificacion.leida.is_(False),
        )
        .values(leida=True)
    )
    await db.flush()
    return {"actualizadas": r.rowcount}


@router.get("/notificaciones", response_model=list[NotificacionRead])
async def mis_notificaciones(
    solo_no_leidas: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
) -> list[NotificacionRead]:
    """Lista paginada de notificaciones, más recientes primero."""
    q = select(Notificacion).where(Notificacion.usuario_id == current_user.id)
    if solo_no_leidas:
        q = q.where(Notificacion.leida.is_(False))
    q = q.order_by(Notificacion.created_at.desc()).limit(limit).offset(offset)

    r = await db.execute(q)
    notifs = r.scalars().all()
    return [
        NotificacionRead(
            id=n.id,
            titulo=n.titulo,
            mensaje=n.mensaje,
            tipo=n.tipo if isinstance(n.tipo, str) else n.tipo.value,
            leida=n.leida,
            created_at=n.created_at,
        )
        for n in notifs
    ]


@router.patch("/notificaciones/{notificacion_id}/leer", response_model=NotificacionRead)
async def marcar_notificacion_leida(
    notificacion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
) -> NotificacionRead:
    """
    Marca una notificación como leída.
    404 genérico si no existe o pertenece a otro usuario (anti-enumeration).
    """
    r = await db.execute(
        select(Notificacion).where(
            Notificacion.id == notificacion_id,
            Notificacion.usuario_id == current_user.id,
        )
    )
    notif = r.scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    notif.leida = True
    await db.flush()

    return NotificacionRead(
        id=notif.id,
        titulo=notif.titulo,
        mensaje=notif.mensaje,
        tipo=notif.tipo if isinstance(notif.tipo, str) else notif.tipo.value,
        leida=notif.leida,
        created_at=notif.created_at,
    )


# ── Boleta PDF ────────────────────────────────────────────────────────────────


async def _generar_boleta_para(
    perfil: PerfilAlumno,
    current_user: Usuario,
    ciclo_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    request: Request,
) -> Response:
    """Lógica compartida entre GET /boleta y GET /boleta/{ciclo_id}."""
    # Rate limiting en Redis
    redis = await get_redis()
    rate_key = f"rate:boleta:{perfil.id}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, _BOLETA_WINDOW_SECS)
    if count > _BOLETA_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite de descargas excedido. Intenta en una hora.",
        )

    # Inscripción del alumno en este ciclo
    r_insc = await db.execute(
        select(
            Inscripcion.id.label("inscripcion_id"),
            Inscripcion.grupo_id,
            Grupo.nombre.label("grupo_nombre"),
        )
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(CicloEscolar, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.id == ciclo_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    insc = r_insc.one_or_none()
    if insc is None:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    # Ciclo
    r_ciclo = await db.execute(
        select(CicloEscolar).where(CicloEscolar.id == ciclo_id)
    )
    ciclo = r_ciclo.scalar_one_or_none()
    if ciclo is None:
        raise HTTPException(status_code=404, detail="Ciclo no encontrado")

    now = datetime.now(timezone.utc)
    materias = await _get_materias_del_ciclo(insc.inscripcion_id, insc.grupo_id, tenant_id, db, now)

    # Validar que al menos un parcial esté cerrado
    tiene_publicados = any(
        p.esta_publicada for m in materias for p in m.parciales
    )
    if not tiene_publicados:
        raise HTTPException(
            status_code=422,
            detail="No hay calificaciones publicadas aún",
        )

    # Institución
    from app.models.core import Institucion
    r_inst = await db.execute(
        select(Institucion).where(Institucion.id == tenant_id)
    )
    institucion = r_inst.scalar_one_or_none()
    inst_data = {
        "nombre": institucion.nombre if institucion else "",
        "direccion": institucion.direccion if institucion else None,
        "telefono": institucion.telefono if institucion else None,
    }

    folio = str(uuid.uuid4())
    ciclo_data = {
        "nombre": ciclo.nombre,
        "tipo": ciclo.tipo,
        "fecha_inicio": str(ciclo.fecha_inicio),
        "fecha_fin": str(ciclo.fecha_fin),
    }
    alumno_data = {
        "nombre_completo": _nombre_completo(current_user),
        "matricula": perfil.matricula,
    }

    pdf_bytes = await generar_boleta(
        alumno_datos=alumno_data,
        institucion_datos=inst_data,
        ciclo_datos=ciclo_data,
        grupo_nombre=insc.grupo_nombre,
        materias=materias,
        folio=folio,
    )

    # Auditoría
    await registrar_auditoria(
        db=db,
        usuario_id=current_user.id,
        institucion_id=tenant_id,
        accion="descarga_boleta",
        tabla="calificaciones_finales",
        registro_id=insc.inscripcion_id,
        valor_anterior=None,
        valor_nuevo={"folio": folio, "ciclo_escolar_id": str(ciclo_id)},
        request=request,
    )
    await db.flush()

    ciclo_slug = ciclo.nombre.lower().replace(" ", "_")[:30]
    matricula = perfil.matricula or "alumno"
    filename = f"boleta_{matricula}_{ciclo_slug}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/boleta")
async def descargar_boleta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> Response:
    """Descarga la boleta del ciclo activo en PDF."""
    perfil = await _get_perfil(db, current_user)

    r_ciclo = await db.execute(
        select(CicloEscolar.id)
        .join(Inscripcion, Inscripcion.ciclo_escolar_id == CicloEscolar.id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .where(
            Inscripcion.alumno_id == perfil.id,
            Inscripcion.activa.is_(True),
            CicloEscolar.activo.is_(True),
            Grupo.institucion_id == tenant_id,
        )
    )
    ciclo_row = r_ciclo.one_or_none()
    if ciclo_row is None:
        raise HTTPException(status_code=404, detail="No hay ciclo activo para este alumno")

    ciclo_id = ciclo_row[0] if isinstance(ciclo_row, tuple) else ciclo_row.id

    return await _generar_boleta_para(perfil, current_user, ciclo_id, tenant_id, db, request)


@router.get("/boleta/{ciclo_id}")
async def descargar_boleta_ciclo(
    ciclo_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("alumno")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> Response:
    """Descarga la boleta de un ciclo específico del historial."""
    perfil = await _get_perfil(db, current_user)
    return await _generar_boleta_para(perfil, current_user, ciclo_id, tenant_id, db, request)
