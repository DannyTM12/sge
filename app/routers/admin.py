"""
Router de administración institucional.
Todos los endpoints requieren rol admin o superadmin.
Cada query filtra por tenant_id para garantizar el aislamiento entre instituciones.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.auth import get_current_user
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
from app.models.asistencias import Justificante
from app.models.auditoria import Auditoria
from app.models.core import PerfilAlumno, PerfilProfesor, RolUsuario, Usuario
from app.models.evaluaciones import CalificacionFinal, Parcial
from app.models.ia import Alerta, NivelRiesgo, PrediccionRiesgo
from app.schemas.academico import (
    AsignarProfesorRequest,
    CicloEscolarCreate,
    CicloEscolarRead,
    GrupoCreate,
    GrupoDetailRead,
    GrupoMateriaCreate,
    GrupoMateriaRead,
    GrupoRead,
    InscripcionCreate,
    InscripcionRead,
    MateriaCreate,
    MateriaRead,
    MateriaUpdate,
    ProfesorGrupoMateriaRead,
    TransferirInscripcionRequest,
)
from app.schemas.asistencias import JustificanteCreate, JustificanteRead
from app.schemas.evaluaciones import (
    CalificacionFinalRead,
    CalificacionFinalUpdate,
    ParcialCreate,
    ParcialRead,
)
from app.schemas.usuario import (
    EstadoUsuarioUpdate,
    UserRead,
    UsuarioAdminCreate,
    UsuarioListRead,
)
from app.services.calificaciones_service import recalcular_y_guardar
from app.utils.audit import registrar_auditoria
from app.utils.security import hash_password

router = APIRouter(prefix="/admin", tags=["Administración"])

# Dependencia reutilizable que verifica rol Y devuelve el usuario actual
_admin_dep = Depends(require_roles("admin", "superadmin"))


# ── Ciclos escolares ──────────────────────────────────────────────────────────

@router.post("/ciclos", response_model=CicloEscolarRead, status_code=status.HTTP_201_CREATED)
async def crear_ciclo(
    data: CicloEscolarCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> CicloEscolarRead:
    ciclo = CicloEscolar(
        id=uuid.uuid4(),
        institucion_id=tenant_id,
        nombre=data.nombre,
        tipo=data.tipo,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
        activo=True,
    )
    db.add(ciclo)
    await db.flush()
    return CicloEscolarRead(
        id=ciclo.id,
        institucion_id=ciclo.institucion_id,
        nombre=ciclo.nombre,
        tipo=ciclo.tipo,
        fecha_inicio=ciclo.fecha_inicio,
        fecha_fin=ciclo.fecha_fin,
        activo=ciclo.activo,
    )


@router.get("/ciclos", response_model=list[CicloEscolarRead])
async def listar_ciclos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> list[CicloEscolarRead]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(CicloEscolar)
        .where(CicloEscolar.institucion_id == tenant_id)
        .order_by(CicloEscolar.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    ciclos = result.scalars().all()
    return [CicloEscolarRead.model_validate(c) for c in ciclos]


@router.patch("/ciclos/{ciclo_id}/cerrar", response_model=CicloEscolarRead)
async def cerrar_ciclo(
    ciclo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> CicloEscolarRead:
    result = await db.execute(
        select(CicloEscolar).where(
            CicloEscolar.id == ciclo_id,
            CicloEscolar.institucion_id == tenant_id,
        )
    )
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciclo escolar no encontrado")
    ciclo.activo = False
    await db.flush()
    return CicloEscolarRead.model_validate(ciclo)


# ── Materias ──────────────────────────────────────────────────────────────────

@router.post("/materias", response_model=MateriaRead, status_code=status.HTTP_201_CREATED)
async def crear_materia(
    data: MateriaCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> MateriaRead:
    materia = Materia(
        id=uuid.uuid4(),
        institucion_id=tenant_id,
        nombre=data.nombre,
        clave=data.clave,
        creditos=data.creditos,
        activa=True,
    )
    db.add(materia)
    await db.flush()
    return MateriaRead(
        id=materia.id,
        institucion_id=materia.institucion_id,
        nombre=materia.nombre,
        clave=materia.clave,
        creditos=materia.creditos,
        activa=materia.activa,
    )


@router.get("/materias", response_model=list[MateriaRead])
async def listar_materias(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> list[MateriaRead]:
    result = await db.execute(
        select(Materia).where(
            Materia.institucion_id == tenant_id,
            Materia.activa == True,  # noqa: E712
        ).order_by(Materia.nombre)
    )
    return [MateriaRead.model_validate(m) for m in result.scalars().all()]


@router.patch("/materias/{materia_id}", response_model=MateriaRead)
async def editar_materia(
    materia_id: uuid.UUID,
    data: MateriaUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> MateriaRead:
    result = await db.execute(
        select(Materia).where(
            Materia.id == materia_id,
            Materia.institucion_id == tenant_id,
        )
    )
    materia = result.scalar_one_or_none()
    if not materia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
    if data.nombre is not None:
        materia.nombre = data.nombre
    if data.clave is not None:
        materia.clave = data.clave
    if data.creditos is not None:
        materia.creditos = data.creditos
    await db.flush()
    return MateriaRead.model_validate(materia)


@router.delete("/materias/{materia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desactivar_materia(
    materia_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> None:
    result = await db.execute(
        select(Materia).where(
            Materia.id == materia_id,
            Materia.institucion_id == tenant_id,
        )
    )
    materia = result.scalar_one_or_none()
    if not materia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
    materia.activa = False
    await db.flush()


# ── Grupos ────────────────────────────────────────────────────────────────────

@router.post("/grupos", response_model=GrupoRead, status_code=status.HTTP_201_CREATED)
async def crear_grupo(
    data: GrupoCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> GrupoRead:
    # Verificar que el ciclo pertenece a la institución
    result = await db.execute(
        select(CicloEscolar).where(
            CicloEscolar.id == data.ciclo_escolar_id,
            CicloEscolar.institucion_id == tenant_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciclo escolar no encontrado")

    grupo = Grupo(
        id=uuid.uuid4(),
        institucion_id=tenant_id,
        ciclo_escolar_id=data.ciclo_escolar_id,
        nombre=data.nombre,
        tipo_periodo=data.tipo_periodo,
        turno=data.turno,
        capacidad_maxima=data.capacidad_maxima,
        activo=True,
    )
    db.add(grupo)
    await db.flush()
    return GrupoRead(
        id=grupo.id,
        institucion_id=grupo.institucion_id,
        ciclo_escolar_id=grupo.ciclo_escolar_id,
        nombre=grupo.nombre,
        tipo_periodo=grupo.tipo_periodo,
        turno=grupo.turno,
        capacidad_maxima=grupo.capacidad_maxima,
        activo=grupo.activo,
    )


@router.get("/grupos", response_model=list[GrupoRead])
async def listar_grupos(
    ciclo_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> list[GrupoRead]:
    stmt = select(Grupo).where(
        Grupo.institucion_id == tenant_id,
        Grupo.activo == True,  # noqa: E712
    )
    if ciclo_id:
        stmt = stmt.where(Grupo.ciclo_escolar_id == ciclo_id)
    result = await db.execute(stmt.order_by(Grupo.nombre))
    return [GrupoRead.model_validate(g) for g in result.scalars().all()]


@router.get("/grupos/{grupo_id}", response_model=GrupoDetailRead)
async def detalle_grupo(
    grupo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> GrupoDetailRead:
    result = await db.execute(
        select(Grupo).where(
            Grupo.id == grupo_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    grupo = result.scalar_one_or_none()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo no encontrado")

    # Obtener materias asignadas
    gm_result = await db.execute(
        select(GrupoMateria, Materia)
        .join(Materia, GrupoMateria.materia_id == Materia.id)
        .where(GrupoMateria.grupo_id == grupo_id)
    )
    materias_list = [
        GrupoMateriaRead(
            id=gm.id,
            grupo_id=gm.grupo_id,
            materia_id=gm.materia_id,
            num_parciales=gm.num_parciales,
            created_at=gm.created_at,
            materia_nombre=mat.nombre,
            grupo_nombre=grupo.nombre,
        )
        for gm, mat in gm_result.all()
    ]

    # Obtener inscripciones activas con nombre del alumno
    ins_result = await db.execute(
        select(Inscripcion, PerfilAlumno, Usuario)
        .join(PerfilAlumno, Inscripcion.alumno_id == PerfilAlumno.id)
        .join(Usuario, PerfilAlumno.usuario_id == Usuario.id)
        .where(Inscripcion.grupo_id == grupo_id, Inscripcion.activa == True)  # noqa: E712
    )
    alumnos_list = [
        InscripcionRead(
            id=ins.id,
            alumno_id=ins.alumno_id,
            grupo_id=ins.grupo_id,
            ciclo_escolar_id=ins.ciclo_escolar_id,
            fecha_inscripcion=ins.fecha_inscripcion,
            activa=ins.activa,
            created_at=ins.created_at,
            alumno_nombre_completo=f"{u.nombre} {u.apellido_paterno}",
        )
        for ins, perfil, u in ins_result.all()
    ]

    return GrupoDetailRead(
        id=grupo.id,
        institucion_id=grupo.institucion_id,
        ciclo_escolar_id=grupo.ciclo_escolar_id,
        nombre=grupo.nombre,
        tipo_periodo=grupo.tipo_periodo,
        turno=grupo.turno,
        capacidad_maxima=grupo.capacidad_maxima,
        activo=grupo.activo,
        created_at=grupo.created_at,
        materias=materias_list,
        alumnos_inscritos=alumnos_list,
    )


@router.post("/grupos/{grupo_id}/materias", response_model=GrupoMateriaRead, status_code=status.HTTP_201_CREATED)
async def asignar_materia_a_grupo(
    grupo_id: uuid.UUID,
    data: GrupoMateriaCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> GrupoMateriaRead:
    # Verificar que el grupo pertenece al tenant
    g_result = await db.execute(
        select(Grupo).where(Grupo.id == grupo_id, Grupo.institucion_id == tenant_id)
    )
    grupo = g_result.scalar_one_or_none()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo no encontrado")

    # Verificar que la materia pertenece al tenant
    m_result = await db.execute(
        select(Materia).where(
            Materia.id == data.materia_id,
            Materia.institucion_id == tenant_id,
            Materia.activa == True,  # noqa: E712
        )
    )
    materia = m_result.scalar_one_or_none()
    if not materia:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")

    # Verificar que no existe ya la asignación
    existing = await db.execute(
        select(GrupoMateria).where(
            GrupoMateria.grupo_id == grupo_id,
            GrupoMateria.materia_id == data.materia_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La materia ya está asignada a este grupo")

    gm = GrupoMateria(
        id=uuid.uuid4(),
        grupo_id=grupo_id,
        materia_id=data.materia_id,
        num_parciales=data.num_parciales,
    )
    db.add(gm)
    await db.flush()
    return GrupoMateriaRead(
        id=gm.id,
        grupo_id=gm.grupo_id,
        materia_id=gm.materia_id,
        num_parciales=gm.num_parciales,
        created_at=gm.created_at,
        materia_nombre=materia.nombre,
        grupo_nombre=grupo.nombre,
    )


@router.delete("/grupos/{grupo_id}/materias/{gm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def quitar_materia_de_grupo(
    grupo_id: uuid.UUID,
    gm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> None:
    result = await db.execute(
        select(GrupoMateria)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            GrupoMateria.id == gm_id,
            GrupoMateria.grupo_id == grupo_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    gm = result.scalar_one_or_none()
    if not gm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asignación no encontrada")
    await db.delete(gm)


@router.post("/grupos/{grupo_id}/materias/{gm_id}/profesor", response_model=ProfesorGrupoMateriaRead, status_code=status.HTTP_201_CREATED)
async def asignar_profesor(
    grupo_id: uuid.UUID,
    gm_id: uuid.UUID,
    data: AsignarProfesorRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> ProfesorGrupoMateriaRead:
    # Verificar que el grupo_materia pertenece al tenant
    gm_result = await db.execute(
        select(GrupoMateria)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(GrupoMateria.id == gm_id, Grupo.institucion_id == tenant_id)
    )
    gm = gm_result.scalar_one_or_none()
    if not gm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asignación grupo-materia no encontrada")

    # Verificar que el profesor pertenece al tenant y tiene rol profesor
    u_result = await db.execute(
        select(Usuario).where(
            Usuario.id == data.usuario_id,
            Usuario.institucion_id == tenant_id,
            Usuario.rol == RolUsuario.profesor,
            Usuario.activo == True,  # noqa: E712
        )
    )
    if not u_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesor no encontrado")

    # Desactivar asignación anterior si existe
    await db.execute(
        update(ProfesorGrupoMateria)
        .where(ProfesorGrupoMateria.grupo_materia_id == gm_id, ProfesorGrupoMateria.activo == True)  # noqa: E712
        .values(activo=False)
    )

    pgm = ProfesorGrupoMateria(
        id=uuid.uuid4(),
        usuario_id=data.usuario_id,
        grupo_materia_id=gm_id,
        activo=True,
    )
    db.add(pgm)
    await db.flush()
    return ProfesorGrupoMateriaRead(
        id=pgm.id,
        usuario_id=pgm.usuario_id,
        grupo_materia_id=pgm.grupo_materia_id,
        activo=pgm.activo,
    )


# ── Usuarios e inscripciones ──────────────────────────────────────────────────

@router.post("/usuarios", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    data: UsuarioAdminCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> UserRead:
    # Verificar email único
    existing = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    user = Usuario(
        id=uuid.uuid4(),
        institucion_id=tenant_id,
        nombre=data.nombre,
        apellido_paterno=data.apellido_paterno,
        apellido_materno=data.apellido_materno,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol,
        activo=True,
    )
    db.add(user)
    await db.flush()

    # Crear perfil según rol
    if data.rol == RolUsuario.alumno:
        db.add(PerfilAlumno(
            id=uuid.uuid4(),
            usuario_id=user.id,
            matricula=data.matricula,
            fecha_nacimiento=data.fecha_nacimiento,
            curp=data.curp,
            telefono_tutor=data.telefono_tutor,
            nombre_tutor=data.nombre_tutor,
            email_tutor=data.email_tutor,
        ))
    elif data.rol == RolUsuario.profesor:
        db.add(PerfilProfesor(
            id=uuid.uuid4(),
            usuario_id=user.id,
            numero_empleado=data.numero_empleado,
            especialidad=data.especialidad,
            telefono=data.telefono,
        ))

    await db.flush()
    return UserRead(
        id=user.id,
        nombre=user.nombre,
        apellido_paterno=user.apellido_paterno,
        email=user.email,
        rol=user.rol,
        institucion_id=user.institucion_id,
    )


@router.get("/usuarios", response_model=list[UsuarioListRead])
async def listar_usuarios(
    rol: Optional[RolUsuario] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> list[UsuarioListRead]:
    offset = (page - 1) * page_size
    stmt = select(Usuario).where(Usuario.institucion_id == tenant_id)
    if rol:
        stmt = stmt.where(Usuario.rol == rol)
    result = await db.execute(
        stmt.order_by(Usuario.apellido_paterno, Usuario.nombre).offset(offset).limit(page_size)
    )
    return [UsuarioListRead.model_validate(u) for u in result.scalars().all()]


@router.patch("/usuarios/{usuario_id}/estado", response_model=UserRead)
async def cambiar_estado_usuario(
    usuario_id: uuid.UUID,
    data: EstadoUsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> UserRead:
    result = await db.execute(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.institucion_id == tenant_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    user.activo = data.activo
    await db.flush()
    return UserRead.model_validate(user)


@router.post("/inscripciones", response_model=InscripcionRead, status_code=status.HTTP_201_CREATED)
async def inscribir_alumno(
    data: InscripcionCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> InscripcionRead:
    # Verificar que el perfil de alumno pertenece al tenant
    pa_result = await db.execute(
        select(PerfilAlumno)
        .join(Usuario, PerfilAlumno.usuario_id == Usuario.id)
        .where(
            PerfilAlumno.id == data.alumno_id,
            Usuario.institucion_id == tenant_id,
        )
    )
    perfil = pa_result.scalar_one_or_none()
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")

    # Verificar que el grupo pertenece al tenant
    g_result = await db.execute(
        select(Grupo).where(Grupo.id == data.grupo_id, Grupo.institucion_id == tenant_id)
    )
    grupo = g_result.scalar_one_or_none()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo no encontrado")

    # Verificar inscripción duplicada
    dup = await db.execute(
        select(Inscripcion).where(
            Inscripcion.alumno_id == data.alumno_id,
            Inscripcion.grupo_id == data.grupo_id,
            Inscripcion.ciclo_escolar_id == grupo.ciclo_escolar_id,
            Inscripcion.activa == True,  # noqa: E712
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El alumno ya está inscrito en este grupo")

    inscripcion = Inscripcion(
        id=uuid.uuid4(),
        alumno_id=data.alumno_id,
        grupo_id=data.grupo_id,
        ciclo_escolar_id=grupo.ciclo_escolar_id,
        fecha_inscripcion=date.today(),
        activa=True,
    )
    db.add(inscripcion)
    await db.flush()

    # Obtener nombre del alumno
    u_result = await db.execute(
        select(Usuario).where(Usuario.id == perfil.usuario_id)
    )
    usuario = u_result.scalar_one_or_none()
    nombre_completo = f"{usuario.nombre} {usuario.apellido_paterno}" if usuario else ""

    return InscripcionRead(
        id=inscripcion.id,
        alumno_id=inscripcion.alumno_id,
        grupo_id=inscripcion.grupo_id,
        ciclo_escolar_id=inscripcion.ciclo_escolar_id,
        fecha_inscripcion=inscripcion.fecha_inscripcion,
        activa=inscripcion.activa,
        alumno_nombre_completo=nombre_completo,
    )


@router.patch("/inscripciones/{inscripcion_id}/transferir", response_model=InscripcionRead)
async def transferir_alumno(
    inscripcion_id: uuid.UUID,
    data: TransferirInscripcionRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> InscripcionRead:
    # Obtener inscripción actual con verificación de tenant
    result = await db.execute(
        select(Inscripcion)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .where(
            Inscripcion.id == inscripcion_id,
            Grupo.institucion_id == tenant_id,
            Inscripcion.activa == True,  # noqa: E712
        )
    )
    inscripcion_actual = result.scalar_one_or_none()
    if not inscripcion_actual:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscripción no encontrada")

    # Verificar grupo destino
    g_result = await db.execute(
        select(Grupo).where(Grupo.id == data.nuevo_grupo_id, Grupo.institucion_id == tenant_id)
    )
    nuevo_grupo = g_result.scalar_one_or_none()
    if not nuevo_grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo destino no encontrado")

    # Marcar inscripción actual como inactiva
    inscripcion_actual.activa = False

    # Crear nueva inscripción
    nueva = Inscripcion(
        id=uuid.uuid4(),
        alumno_id=inscripcion_actual.alumno_id,
        grupo_id=data.nuevo_grupo_id,
        ciclo_escolar_id=nuevo_grupo.ciclo_escolar_id,
        fecha_inscripcion=date.today(),
        activa=True,
    )
    db.add(nueva)
    await db.flush()

    return InscripcionRead(
        id=nueva.id,
        alumno_id=nueva.alumno_id,
        grupo_id=nueva.grupo_id,
        ciclo_escolar_id=nueva.ciclo_escolar_id,
        fecha_inscripcion=nueva.fecha_inscripcion,
        activa=nueva.activa,
    )


# ── Parciales ─────────────────────────────────────────────────────────────────

@router.post("/parciales", response_model=ParcialRead, status_code=status.HTTP_201_CREATED)
async def crear_parcial(
    data: ParcialCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> ParcialRead:
    # Verificar que grupo_materia pertenece al tenant
    gm_result = await db.execute(
        select(GrupoMateria)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(
            GrupoMateria.id == data.grupo_materia_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    if not gm_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo-materia no encontrado")

    parcial = Parcial(
        id=uuid.uuid4(),
        grupo_materia_id=data.grupo_materia_id,
        numero=data.numero,
        nombre=data.nombre,
        fecha_apertura=data.fecha_apertura,
        fecha_cierre=data.fecha_cierre,
        activo=True,
    )
    db.add(parcial)
    await db.flush()
    return ParcialRead(
        id=parcial.id,
        grupo_materia_id=parcial.grupo_materia_id,
        numero=parcial.numero,
        nombre=parcial.nombre,
        fecha_apertura=parcial.fecha_apertura,
        fecha_cierre=parcial.fecha_cierre,
        activo=parcial.activo,
    )


@router.patch("/parciales/{parcial_id}/abrir", response_model=ParcialRead)
async def abrir_parcial(
    parcial_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> ParcialRead:
    result = await db.execute(
        select(Parcial)
        .join(GrupoMateria, Parcial.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(Parcial.id == parcial_id, Grupo.institucion_id == tenant_id)
    )
    parcial = result.scalar_one_or_none()
    if not parcial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcial no encontrado")
    parcial.activo = True
    parcial.fecha_apertura = datetime.now(timezone.utc)
    await db.flush()
    return ParcialRead.model_validate(parcial)


@router.patch("/parciales/{parcial_id}/cerrar", response_model=ParcialRead)
async def cerrar_parcial(
    parcial_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> ParcialRead:
    # Obtener parcial con verificación de tenant
    result = await db.execute(
        select(Parcial)
        .join(GrupoMateria, Parcial.grupo_materia_id == GrupoMateria.id)
        .join(Grupo, GrupoMateria.grupo_id == Grupo.id)
        .where(Parcial.id == parcial_id, Grupo.institucion_id == tenant_id)
    )
    parcial = result.scalar_one_or_none()
    if not parcial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcial no encontrado")

    # Obtener materia_id desde grupo_materia
    gm_result = await db.execute(
        select(GrupoMateria).where(GrupoMateria.id == parcial.grupo_materia_id)
    )
    gm = gm_result.scalar_one_or_none()

    # Cerrar período
    parcial.activo = False
    parcial.fecha_cierre = datetime.now(timezone.utc)

    if gm:
        # Obtener todas las inscripciones activas del grupo
        ins_result = await db.execute(
            select(Inscripcion).where(
                Inscripcion.grupo_id == gm.grupo_id,
                Inscripcion.activa == True,  # noqa: E712
            )
        )
        inscripciones = ins_result.scalars().all()

        # Recalcular calificación final para cada alumno
        for ins in inscripciones:
            await recalcular_y_guardar(
                inscripcion_id=ins.id,
                materia_id=gm.materia_id,
                grupo_materia_id=gm.id,
                db=db,
            )

    await db.flush()
    return ParcialRead(
        id=parcial.id,
        grupo_materia_id=parcial.grupo_materia_id,
        numero=parcial.numero,
        nombre=parcial.nombre,
        fecha_apertura=parcial.fecha_apertura,
        fecha_cierre=parcial.fecha_cierre,
        activo=parcial.activo,
    )


# ── Calificaciones — override manual ─────────────────────────────────────────

@router.patch("/calificaciones-finales/{cf_id}", response_model=CalificacionFinalRead)
async def override_calificacion_final(
    cf_id: uuid.UUID,
    data: CalificacionFinalUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> CalificacionFinalRead:
    # Obtener calificacion_final con verificación de tenant a través de inscripcion → grupo
    result = await db.execute(
        select(CalificacionFinal)
        .join(Inscripcion, CalificacionFinal.inscripcion_id == Inscripcion.id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .where(
            CalificacionFinal.id == cf_id,
            Grupo.institucion_id == tenant_id,
        )
    )
    cf = result.scalar_one_or_none()
    if not cf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calificación final no encontrada")

    valor_anterior = {"calificacion_final": str(cf.calificacion_final)}

    cf.calificacion_final = data.calificacion_final
    cf.fue_modificada_manualmente = True
    cf.modificado_por = current_user.id
    cf.fecha_modificacion = datetime.now(timezone.utc)

    valor_nuevo = {"calificacion_final": str(data.calificacion_final)}

    await registrar_auditoria(
        db=db,
        usuario_id=current_user.id,
        institucion_id=tenant_id,
        accion="override_calificacion_final",
        tabla="calificaciones_finales",
        registro_id=cf.id,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        request=request,
    )

    await db.flush()
    return CalificacionFinalRead.model_validate(cf)


# ── Justificantes ─────────────────────────────────────────────────────────────

@router.post("/justificantes", response_model=JustificanteRead, status_code=status.HTTP_201_CREATED)
async def registrar_justificante(
    data: JustificanteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> JustificanteRead:
    # Verificar que el alumno pertenece al tenant
    pa_result = await db.execute(
        select(PerfilAlumno)
        .join(Usuario, PerfilAlumno.usuario_id == Usuario.id)
        .where(PerfilAlumno.id == data.alumno_id, Usuario.institucion_id == tenant_id)
    )
    if not pa_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")

    justificante = Justificante(
        id=uuid.uuid4(),
        alumno_id=data.alumno_id,
        asistencia_id=data.asistencia_id,
        institucion_id=tenant_id,
        descripcion=data.descripcion,
        documento_url=data.documento_url,
        registrado_por=current_user.id,
        fecha_justificante=data.fecha_justificante,
    )
    db.add(justificante)

    await registrar_auditoria(
        db=db,
        usuario_id=current_user.id,
        institucion_id=tenant_id,
        accion="crear_justificante",
        tabla="justificantes",
        registro_id=None,
        valor_anterior=None,
        valor_nuevo={"alumno_id": str(data.alumno_id), "descripcion": data.descripcion},
        request=request,
    )

    await db.flush()
    return JustificanteRead(
        id=justificante.id,
        alumno_id=justificante.alumno_id,
        asistencia_id=justificante.asistencia_id,
        institucion_id=justificante.institucion_id,
        descripcion=justificante.descripcion,
        documento_url=justificante.documento_url,
        registrado_por=justificante.registrado_por,
        fecha_justificante=justificante.fecha_justificante,
    )


@router.get("/justificantes", response_model=list[JustificanteRead])
async def listar_justificantes(
    alumno_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> list[JustificanteRead]:
    offset = (page - 1) * page_size
    stmt = select(Justificante).where(Justificante.institucion_id == tenant_id)
    if alumno_id:
        stmt = stmt.where(Justificante.alumno_id == alumno_id)
    result = await db.execute(
        stmt.order_by(Justificante.created_at.desc()).offset(offset).limit(page_size)
    )
    return [JustificanteRead.model_validate(j) for j in result.scalars().all()]


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> dict:
    total_alumnos = await db.scalar(
        select(func.count()).select_from(Usuario).where(
            Usuario.institucion_id == tenant_id,
            Usuario.rol == RolUsuario.alumno,
            Usuario.activo == True,  # noqa: E712
        )
    ) or 0

    total_grupos = await db.scalar(
        select(func.count()).select_from(Grupo).where(
            Grupo.institucion_id == tenant_id,
            Grupo.activo == True,  # noqa: E712
        )
    ) or 0

    total_profesores = await db.scalar(
        select(func.count()).select_from(Usuario).where(
            Usuario.institucion_id == tenant_id,
            Usuario.rol == RolUsuario.profesor,
            Usuario.activo == True,  # noqa: E712
        )
    ) or 0

    promedio_raw = await db.scalar(
        select(func.avg(CalificacionFinal.calificacion_final))
        .join(Inscripcion, CalificacionFinal.inscripcion_id == Inscripcion.id)
        .join(Grupo, Inscripcion.grupo_id == Grupo.id)
        .where(Grupo.institucion_id == tenant_id)
    )
    promedio_institucional = float(promedio_raw) if promedio_raw is not None else 0.0

    total_predicciones = await db.scalar(
        select(func.count()).select_from(PrediccionRiesgo)
        .join(CicloEscolar, PrediccionRiesgo.ciclo_escolar_id == CicloEscolar.id)
        .where(CicloEscolar.institucion_id == tenant_id)
    ) or 0

    en_riesgo = await db.scalar(
        select(func.count()).select_from(PrediccionRiesgo)
        .join(CicloEscolar, PrediccionRiesgo.ciclo_escolar_id == CicloEscolar.id)
        .where(
            CicloEscolar.institucion_id == tenant_id,
            PrediccionRiesgo.nivel_riesgo.in_([NivelRiesgo.alto, NivelRiesgo.critico]),
        )
    ) or 0

    porcentaje_riesgo = (en_riesgo / total_predicciones * 100) if total_predicciones > 0 else 0.0

    alertas_no_leidas = await db.scalar(
        select(func.count()).select_from(Alerta).where(
            Alerta.institucion_id == tenant_id,
            Alerta.leida == False,  # noqa: E712
        )
    ) or 0

    return {
        "total_alumnos": total_alumnos,
        "total_grupos": total_grupos,
        "total_profesores": total_profesores,
        "promedio_institucional": promedio_institucional,
        "porcentaje_riesgo": float(porcentaje_riesgo),
        "alertas_no_leidas": alertas_no_leidas,
    }


# ── Auditoría ─────────────────────────────────────────────────────────────────

@router.get("/auditoria")
async def listar_auditoria(
    tabla_afectada: Optional[str] = Query(None),
    usuario_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(require_roles("admin", "superadmin")),
) -> dict:
    offset = (page - 1) * page_size
    stmt = select(Auditoria).where(Auditoria.institucion_id == tenant_id)
    if tabla_afectada:
        stmt = stmt.where(Auditoria.tabla_afectada == tabla_afectada)
    if usuario_id:
        stmt = stmt.where(Auditoria.usuario_id == usuario_id)

    total_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = total_result.scalar() or 0

    items_result = await db.execute(
        stmt.order_by(Auditoria.created_at.desc()).offset(offset).limit(page_size)
    )
    items = items_result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(a.id),
                "usuario_id": str(a.usuario_id),
                "accion": a.accion,
                "tabla_afectada": a.tabla_afectada,
                "registro_id": str(a.registro_id) if a.registro_id else None,
                "valor_anterior": a.valor_anterior,
                "valor_nuevo": a.valor_nuevo,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ],
    }
