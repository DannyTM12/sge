"""
Paquete de modelos SQLAlchemy.
Importa todos los modelos de los 7 dominios para que Alembic los detecte automáticamente
al hacer `from app.models import *` en alembic/env.py.
"""

# Dominio 1: Core / Multitenancy
from app.models.core import (
    Institucion,
    PerfilAlumno,
    PerfilProfesor,
    RolUsuario,
    SesionUsuario,
    TokenRecuperacion,
    Usuario,
)

# Dominio 2: Estructura académica
from app.models.academico import (
    CicloEscolar,
    Grupo,
    GrupoMateria,
    Inscripcion,
    Materia,
    ProfesorGrupoMateria,
    TipoPeriodo,
    TurnoGrupo,
)

# Dominio 3: Evaluaciones
from app.models.evaluaciones import (
    Calificacion,
    CalificacionFinal,
    Parcial,
)

# Dominio 4: Asistencias
from app.models.asistencias import (
    Asistencia,
    EstadoAsistencia,
    Justificante,
    SesionClase,
)

# Dominio 5: Notas y horarios
from app.models.notas import (
    DiaSemana,
    Horario,
    NotaAlumno,
)

# Dominio 6: IA y alertas
from app.models.ia import (
    Alerta,
    NivelRiesgo,
    Notificacion,
    PrediccionRiesgo,
    TipoAlerta,
    TipoNotificacion,
)

# Dominio 7: Auditoría
from app.models.auditoria import Auditoria

__all__ = [
    # Core
    "Institucion",
    "Usuario",
    "PerfilAlumno",
    "PerfilProfesor",
    "SesionUsuario",
    "TokenRecuperacion",
    "RolUsuario",
    # Académico
    "CicloEscolar",
    "Grupo",
    "Materia",
    "GrupoMateria",
    "ProfesorGrupoMateria",
    "Inscripcion",
    "TipoPeriodo",
    "TurnoGrupo",
    # Evaluaciones
    "Parcial",
    "Calificacion",
    "CalificacionFinal",
    # Asistencias
    "SesionClase",
    "Asistencia",
    "Justificante",
    "EstadoAsistencia",
    # Notas
    "NotaAlumno",
    "Horario",
    "DiaSemana",
    # IA
    "PrediccionRiesgo",
    "Alerta",
    "Notificacion",
    "NivelRiesgo",
    "TipoAlerta",
    "TipoNotificacion",
    # Auditoría
    "Auditoria",
]
