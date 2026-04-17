"""
Router de profesores.
Expone los endpoints bajo /profesores/*: pase de lista, calificaciones, notas.
Todos los endpoints requieren rol 'profesor'.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.rbac import require_roles
from app.middleware.tenant import get_tenant_id
from app.models.academico import Grupo, GrupoMateria, Inscripcion, ProfesorGrupoMateria
from app.models.asistencias import Asistencia, SesionClase
from app.models.evaluaciones import Calificacion, Parcial
from app.models.notas import NotaAlumno
from app.models.core import Usuario
from app.schemas.asistencias import (
    AsistenciaRead,
    AsistenciaUpdate,
    ListaAsistenciaCreate,
    SesionClaseCreate,
    SesionClaseRead,
)
from app.schemas.evaluaciones import (
    CalificacionCreate,
    CalificacionRead,
    CalificacionUpdate,
    DashboardProfesorRead,
    MiGrupoRead,
)
from app.schemas.academico import InscripcionRead
from app.schemas.notas import NotaCreate, NotaRead, NotaUpdate
from app.services.calificaciones_service import recalcular_y_guardar

router = APIRouter(prefix="/profesores", tags=["profesores"])


# ── Mis grupos ────────────────────────────────────────────────────────────────

@router.get("/mis-grupos", response_model=list[MiGrupoRead])
async def mis_grupos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[MiGrupoRead]:
    """Lista los grupo-materia asignados al profesor en la institución."""
    from app.models.academico import Materia  # local import to avoid circular
    result = await db.execute(
        select(
            GrupoMateria.id.label("grupo_materia_id"),
            GrupoMateria.materia_id,
            Materia.nombre.label("materia_nombre"),
            GrupoMateria.grupo_id,
            Grupo.nombre.label("grupo_nombre"),
            GrupoMateria.num_parciales,
        )
        .join(ProfesorGrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .where(
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    rows = result.all()
    return [
        MiGrupoRead(
            grupo_materia_id=row.grupo_materia_id,
            materia_id=row.materia_id,
            materia_nombre=row.materia_nombre,
            grupo_id=row.grupo_id,
            grupo_nombre=row.grupo_nombre,
            num_parciales=row.num_parciales,
        )
        for row in rows
    ]


@router.get("/mis-grupos/{grupo_materia_id}/alumnos", response_model=list[InscripcionRead])
async def listar_alumnos_grupo(
    grupo_materia_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[InscripcionRead]:
    """Lista los alumnos inscritos en el grupo asociado al grupo-materia."""
    # Verificar que el profesor tiene acceso
    result = await db.execute(
        select(GrupoMateria)
        .join(ProfesorGrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            GrupoMateria.id == grupo_materia_id,
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    gm = result.scalar_one_or_none()
    if gm is None:
        raise HTTPException(status_code=404, detail="Grupo-materia no encontrado o sin acceso")

    result2 = await db.execute(
        select(Inscripcion).where(
            Inscripcion.grupo_id == gm.grupo_id,
            Inscripcion.activa == True,
        )
    )
    inscripciones = result2.scalars().all()
    return [
        InscripcionRead(
            id=insc.id,
            alumno_id=insc.alumno_id,
            grupo_id=insc.grupo_id,
            ciclo_escolar_id=insc.ciclo_escolar_id,
            fecha_inscripcion=insc.fecha_inscripcion,
            activa=insc.activa,
            created_at=insc.created_at,
        )
        for insc in inscripciones
    ]


# ── Sesiones de clase ─────────────────────────────────────────────────────────

@router.post("/sesiones", response_model=SesionClaseRead, status_code=status.HTTP_201_CREATED)
async def crear_sesion(
    data: SesionClaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> SesionClaseRead:
    """Crea una nueva sesión de clase para un grupo-materia asignado."""
    result = await db.execute(
        select(ProfesorGrupoMateria)
        .join(GrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            ProfesorGrupoMateria.grupo_materia_id == data.grupo_materia_id,
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    pgm = result.scalar_one_or_none()
    if pgm is None:
        raise HTTPException(status_code=404, detail="Grupo-materia no encontrado o sin acceso")

    sesion = SesionClase(
        id=uuid.uuid4(),
        grupo_materia_id=data.grupo_materia_id,
        profesor_id=current_user.id,
        fecha=data.fecha,
        hora_inicio=data.hora_inicio,
        hora_fin=data.hora_fin,
        tema=data.tema,
    )
    db.add(sesion)
    await db.flush()

    return SesionClaseRead(
        id=sesion.id,
        grupo_materia_id=sesion.grupo_materia_id,
        profesor_id=sesion.profesor_id,
        fecha=sesion.fecha,
        hora_inicio=sesion.hora_inicio,
        hora_fin=sesion.hora_fin,
        tema=sesion.tema,
        created_at=sesion.created_at,
    )


@router.get("/sesiones/{grupo_materia_id}", response_model=list[SesionClaseRead])
async def listar_sesiones(
    grupo_materia_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[SesionClaseRead]:
    """Lista las sesiones de clase de un grupo-materia."""
    result = await db.execute(
        select(GrupoMateria)
        .join(ProfesorGrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            GrupoMateria.id == grupo_materia_id,
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    gm = result.scalar_one_or_none()
    if gm is None:
        raise HTTPException(status_code=404, detail="Grupo-materia no encontrado o sin acceso")

    result2 = await db.execute(
        select(SesionClase)
        .where(
            SesionClase.grupo_materia_id == grupo_materia_id,
            SesionClase.profesor_id == current_user.id,
        )
        .order_by(SesionClase.fecha.desc())
    )
    sesiones = result2.scalars().all()
    return [
        SesionClaseRead(
            id=s.id,
            grupo_materia_id=s.grupo_materia_id,
            profesor_id=s.profesor_id,
            fecha=s.fecha,
            hora_inicio=s.hora_inicio,
            hora_fin=s.hora_fin,
            tema=s.tema,
            created_at=s.created_at,
        )
        for s in sesiones
    ]


# ── Asistencias ───────────────────────────────────────────────────────────────

@router.post(
    "/sesiones/{sesion_id}/asistencia",
    response_model=list[AsistenciaRead],
    status_code=status.HTTP_201_CREATED,
)
async def registrar_asistencia(
    sesion_id: uuid.UUID,
    data: ListaAsistenciaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[AsistenciaRead]:
    """Registra o actualiza la lista de asistencia de una sesión (upsert por alumno)."""
    # Verificar que la sesión pertenece al profesor y a la institución
    result = await db.execute(
        select(SesionClase)
        .join(GrupoMateria, SesionClase.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            SesionClase.id == sesion_id,
            SesionClase.profesor_id == current_user.id,
            Grupo.institucion_id == tenant_id,
        )
    )
    sesion = result.scalar_one_or_none()
    if sesion is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o sin acceso")

    # Obtener asistencias existentes para hacer upsert
    result2 = await db.execute(
        select(Asistencia).where(Asistencia.sesion_id == sesion_id)
    )
    existing_list = result2.scalars().all()
    existing = {a.alumno_id: a for a in existing_list}

    registradas: list[Asistencia] = []
    for item in data.asistencias:
        if item.alumno_id in existing:
            asistencia = existing[item.alumno_id]
            asistencia.estado = item.estado
        else:
            asistencia = Asistencia(
                id=uuid.uuid4(),
                sesion_id=sesion_id,
                alumno_id=item.alumno_id,
                estado=item.estado,
                registrado_por=current_user.id,
            )
            db.add(asistencia)
        registradas.append(asistencia)
    await db.flush()

    return [
        AsistenciaRead(
            id=a.id,
            sesion_id=a.sesion_id,
            alumno_id=a.alumno_id,
            estado=a.estado,
            registrado_por=a.registrado_por,
            created_at=a.created_at,
        )
        for a in registradas
    ]


@router.patch("/asistencias/{asistencia_id}", response_model=AsistenciaRead)
async def actualizar_asistencia(
    asistencia_id: uuid.UUID,
    data: AsistenciaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> AsistenciaRead:
    """Actualiza el estado de una asistencia. Solo válido dentro de las primeras 48 horas."""
    result = await db.execute(
        select(Asistencia)
        .join(SesionClase, Asistencia.sesion_id == SesionClase.id)
        .join(GrupoMateria, SesionClase.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            Asistencia.id == asistencia_id,
            SesionClase.profesor_id == current_user.id,
            Grupo.institucion_id == tenant_id,
        )
    )
    asistencia = result.scalar_one_or_none()
    if asistencia is None:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")

    # Ventana de 48 horas
    if asistencia.created_at is not None:
        limite = datetime.now(timezone.utc) - timedelta(hours=48)
        if asistencia.created_at < limite:
            raise HTTPException(
                status_code=403,
                detail="No se puede modificar una asistencia con más de 48 horas",
            )

    asistencia.estado = data.estado
    await db.flush()

    return AsistenciaRead(
        id=asistencia.id,
        sesion_id=asistencia.sesion_id,
        alumno_id=asistencia.alumno_id,
        estado=asistencia.estado,
        registrado_por=asistencia.registrado_por,
        created_at=asistencia.created_at,
    )


@router.get("/sesiones/{sesion_id}/asistencia", response_model=list[AsistenciaRead])
async def obtener_asistencia_sesion(
    sesion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[AsistenciaRead]:
    """Obtiene la lista de asistencia registrada para una sesión."""
    result = await db.execute(
        select(SesionClase)
        .join(GrupoMateria, SesionClase.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            SesionClase.id == sesion_id,
            SesionClase.profesor_id == current_user.id,
            Grupo.institucion_id == tenant_id,
        )
    )
    sesion = result.scalar_one_or_none()
    if sesion is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o sin acceso")

    result2 = await db.execute(
        select(Asistencia).where(Asistencia.sesion_id == sesion_id)
    )
    asistencias = result2.scalars().all()
    return [
        AsistenciaRead(
            id=a.id,
            sesion_id=a.sesion_id,
            alumno_id=a.alumno_id,
            estado=a.estado,
            registrado_por=a.registrado_por,
            created_at=a.created_at,
        )
        for a in asistencias
    ]


# ── Calificaciones ────────────────────────────────────────────────────────────

@router.post("/calificaciones", response_model=CalificacionRead, status_code=status.HTTP_201_CREATED)
async def registrar_calificacion(
    data: CalificacionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> CalificacionRead:
    """Registra una calificación de parcial para un alumno."""
    # Verificar acceso al parcial vía grupo-materia asignado
    result = await db.execute(
        select(Parcial)
        .join(GrupoMateria, Parcial.grupo_materia_id == GrupoMateria.id)
        .join(ProfesorGrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            Parcial.id == data.parcial_id,
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    parcial = result.scalar_one_or_none()
    if parcial is None:
        raise HTTPException(status_code=404, detail="Parcial no encontrado o sin acceso")

    # Verificar que la inscripción existe en esta institución
    result2 = await db.execute(
        select(Inscripcion)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .where(
            Inscripcion.id == data.inscripcion_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    inscripcion = result2.scalar_one_or_none()
    if inscripcion is None:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    cal = Calificacion(
        id=uuid.uuid4(),
        inscripcion_id=data.inscripcion_id,
        parcial_id=data.parcial_id,
        calificacion=data.calificacion,
        registrado_por=current_user.id,
    )
    db.add(cal)
    await db.flush()

    await recalcular_y_guardar(
        inscripcion_id=data.inscripcion_id,
        materia_id=inscripcion.grupo_id,  # se recalcula internamente por grupo_materia
        grupo_materia_id=parcial.grupo_materia_id,
        db=db,
    )

    return CalificacionRead(
        id=cal.id,
        inscripcion_id=cal.inscripcion_id,
        parcial_id=cal.parcial_id,
        calificacion=cal.calificacion,
        registrado_por=cal.registrado_por,
        created_at=cal.created_at,
        updated_at=cal.updated_at,
    )


@router.put("/calificaciones/{calificacion_id}", response_model=CalificacionRead)
async def actualizar_calificacion(
    calificacion_id: uuid.UUID,
    data: CalificacionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> CalificacionRead:
    """Actualiza la calificación de un parcial."""
    result = await db.execute(
        select(Calificacion)
        .join(Parcial, Calificacion.parcial_id == Parcial.id)
        .join(GrupoMateria, Parcial.grupo_materia_id == GrupoMateria.id)
        .join(ProfesorGrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            Calificacion.id == calificacion_id,
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    cal = result.scalar_one_or_none()
    if cal is None:
        raise HTTPException(status_code=404, detail="Calificación no encontrada o sin acceso")

    cal.calificacion = data.calificacion
    await db.flush()

    # Recalcular calificación final
    result2 = await db.execute(
        select(Inscripcion)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .where(
            Inscripcion.id == cal.inscripcion_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    inscripcion = result2.scalar_one_or_none()
    if inscripcion is not None:
        result3 = await db.execute(
            select(Parcial).where(Parcial.id == cal.parcial_id)
        )
        parcial = result3.scalar_one_or_none()
        if parcial is not None:
            await recalcular_y_guardar(
                inscripcion_id=cal.inscripcion_id,
                materia_id=inscripcion.grupo_id,
                grupo_materia_id=parcial.grupo_materia_id,
                db=db,
            )

    return CalificacionRead(
        id=cal.id,
        inscripcion_id=cal.inscripcion_id,
        parcial_id=cal.parcial_id,
        calificacion=cal.calificacion,
        registrado_por=cal.registrado_por,
        created_at=cal.created_at,
        updated_at=cal.updated_at,
    )


@router.get("/calificaciones/{grupo_materia_id}/{parcial_id}", response_model=list[CalificacionRead])
async def listar_calificaciones(
    grupo_materia_id: uuid.UUID,
    parcial_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[CalificacionRead]:
    """Lista las calificaciones de un parcial para todos los alumnos del grupo."""
    # Verificar acceso al grupo-materia
    result = await db.execute(
        select(ProfesorGrupoMateria)
        .join(GrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            ProfesorGrupoMateria.grupo_materia_id == grupo_materia_id,
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    pgm = result.scalar_one_or_none()
    if pgm is None:
        raise HTTPException(status_code=404, detail="Grupo-materia no encontrado o sin acceso")

    result2 = await db.execute(
        select(Calificacion).where(Calificacion.parcial_id == parcial_id)
    )
    cals = result2.scalars().all()
    return [
        CalificacionRead(
            id=c.id,
            inscripcion_id=c.inscripcion_id,
            parcial_id=c.parcial_id,
            calificacion=c.calificacion,
            registrado_por=c.registrado_por,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cals
    ]


# ── Notas de alumno ───────────────────────────────────────────────────────────

@router.post("/notas", response_model=NotaRead, status_code=status.HTTP_201_CREATED)
async def crear_nota(
    data: NotaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> NotaRead:
    """Crea una nota sobre un alumno."""
    nota = NotaAlumno(
        id=uuid.uuid4(),
        alumno_id=data.alumno_id,
        autor_id=current_user.id,
        institucion_id=tenant_id,
        contenido=data.contenido,
        es_visible_alumno=data.es_visible_alumno,
    )
    db.add(nota)
    await db.flush()

    return NotaRead(
        id=nota.id,
        alumno_id=nota.alumno_id,
        autor_id=nota.autor_id,
        institucion_id=nota.institucion_id,
        contenido=nota.contenido,
        es_visible_alumno=nota.es_visible_alumno,
        created_at=nota.created_at,
        updated_at=nota.updated_at,
    )


@router.get("/notas/{alumno_id}", response_model=list[NotaRead])
async def listar_notas_alumno(
    alumno_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[NotaRead]:
    """Lista las notas escritas por este profesor sobre un alumno."""
    result = await db.execute(
        select(NotaAlumno).where(
            NotaAlumno.alumno_id == alumno_id,
            NotaAlumno.autor_id == current_user.id,
            NotaAlumno.institucion_id == tenant_id,
        )
    )
    notas = result.scalars().all()
    return [
        NotaRead(
            id=n.id,
            alumno_id=n.alumno_id,
            autor_id=n.autor_id,
            institucion_id=n.institucion_id,
            contenido=n.contenido,
            es_visible_alumno=n.es_visible_alumno,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notas
    ]


@router.patch("/notas/{nota_id}", response_model=NotaRead)
async def actualizar_nota(
    nota_id: uuid.UUID,
    data: NotaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> NotaRead:
    """Actualiza el contenido o visibilidad de una nota."""
    result = await db.execute(
        select(NotaAlumno).where(
            NotaAlumno.id == nota_id,
            NotaAlumno.autor_id == current_user.id,
            NotaAlumno.institucion_id == tenant_id,
        )
    )
    nota = result.scalar_one_or_none()
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    if data.contenido is not None:
        nota.contenido = data.contenido
    if data.es_visible_alumno is not None:
        nota.es_visible_alumno = data.es_visible_alumno
    await db.flush()

    return NotaRead(
        id=nota.id,
        alumno_id=nota.alumno_id,
        autor_id=nota.autor_id,
        institucion_id=nota.institucion_id,
        contenido=nota.contenido,
        es_visible_alumno=nota.es_visible_alumno,
        created_at=nota.created_at,
        updated_at=nota.updated_at,
    )


@router.delete("/notas/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_nota(
    nota_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> Response:
    """Elimina una nota del alumno."""
    result = await db.execute(
        select(NotaAlumno).where(
            NotaAlumno.id == nota_id,
            NotaAlumno.autor_id == current_user.id,
            NotaAlumno.institucion_id == tenant_id,
        )
    )
    nota = result.scalar_one_or_none()
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    await db.delete(nota)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardProfesorRead)
async def dashboard_profesor(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles("profesor")),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> DashboardProfesorRead:
    """Resumen del profesor: grupos activos, sesiones de hoy y total de alumnos."""
    r1 = await db.execute(
        select(func.count(ProfesorGrupoMateria.id))
        .join(GrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
        )
    )
    grupos_activos: int = r1.scalar_one_or_none() or 0

    hoy = date.today()
    r2 = await db.execute(
        select(func.count(SesionClase.id)).where(
            SesionClase.profesor_id == current_user.id,
            SesionClase.fecha == hoy,
        )
    )
    sesiones_hoy: int = r2.scalar_one_or_none() or 0

    r3 = await db.execute(
        select(func.count(Inscripcion.id))
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .join(GrupoMateria, GrupoMateria.grupo_id == Grupo.id)
        .join(ProfesorGrupoMateria, ProfesorGrupoMateria.grupo_materia_id == GrupoMateria.id)
        .where(
            ProfesorGrupoMateria.usuario_id == current_user.id,
            ProfesorGrupoMateria.activo == True,
            Grupo.institucion_id == tenant_id,
            Inscripcion.activa == True,
        )
    )
    alumnos_totales: int = r3.scalar_one_or_none() or 0

    return DashboardProfesorRead(
        grupos_activos=grupos_activos,
        sesiones_hoy=sesiones_hoy,
        alumnos_totales=alumnos_totales,
    )
