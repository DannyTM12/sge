"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-04-15 00:00:00.000000

Crea las 24 tablas del esquema inicial del SGE en orden correcto de FK.
También crea los 8 tipos ENUM de PostgreSQL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ── Enums ─────────────────────────────────────────────────────────────────────
rol_usuario_enum = postgresql.ENUM(
    "superadmin", "admin", "profesor", "alumno",
    name="rolusuario", create_type=False,
)
tipo_periodo_enum = postgresql.ENUM(
    "semestral", "cuatrimestral",
    name="tipoperiodo", create_type=False,
)
turno_grupo_enum = postgresql.ENUM(
    "matutino", "vespertino", "mixto",
    name="turnogrupo", create_type=False,
)
estado_asistencia_enum = postgresql.ENUM(
    "presente", "ausente", "tardanza", "justificada",
    name="estadoasistencia", create_type=False,
)
dia_semana_enum = postgresql.ENUM(
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
    name="diasemana", create_type=False,
)
nivel_riesgo_enum = postgresql.ENUM(
    "bajo", "medio", "alto", "critico",
    name="nivelriesgo", create_type=False,
)
tipo_alerta_enum = postgresql.ENUM(
    "riesgo_reprobacion", "faltas_excesivas", "calificacion_baja", "nota_profesor",
    name="tipoalerta", create_type=False,
)
tipo_notificacion_enum = postgresql.ENUM(
    "info", "alerta", "aviso",
    name="tiponotificacion", create_type=False,
)


def upgrade() -> None:
    # ── Crear ENUMs ────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE rolusuario AS ENUM ('superadmin', 'admin', 'profesor', 'alumno')")
    op.execute("CREATE TYPE tipoperiodo AS ENUM ('semestral', 'cuatrimestral')")
    op.execute("CREATE TYPE turnogrupo AS ENUM ('matutino', 'vespertino', 'mixto')")
    op.execute("CREATE TYPE estadoasistencia AS ENUM ('presente', 'ausente', 'tardanza', 'justificada')")
    op.execute("CREATE TYPE diasemana AS ENUM ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado')")
    op.execute("CREATE TYPE nivelriesgo AS ENUM ('bajo', 'medio', 'alto', 'critico')")
    op.execute("CREATE TYPE tipoalerta AS ENUM ('riesgo_reprobacion', 'faltas_excesivas', 'calificacion_baja', 'nota_profesor')")
    op.execute("CREATE TYPE tiponotificacion AS ENUM ('info', 'alerta', 'aviso')")

    # ── 1. instituciones ───────────────────────────────────────────────────────
    op.create_table(
        "instituciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("direccion", sa.Text, nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("email_contacto", sa.String(200), nullable=True),
        sa.Column("activa", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("plan_suscripcion", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 2. usuarios ───────────────────────────────────────────────────────────
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellido_paterno", sa.String(100), nullable=False),
        sa.Column("apellido_materno", sa.String(100), nullable=True),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("rol", rol_usuario_enum, nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 3. perfiles_alumno ────────────────────────────────────────────────────
    op.create_table(
        "perfiles_alumno",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), unique=True, nullable=False),
        sa.Column("matricula", sa.String(50), nullable=True),
        sa.Column("fecha_nacimiento", sa.DateTime(timezone=False), nullable=True),
        sa.Column("curp", sa.String(18), nullable=True),
        sa.Column("telefono_tutor", sa.String(20), nullable=True),
        sa.Column("nombre_tutor", sa.String(200), nullable=True),
        sa.Column("email_tutor", sa.String(200), nullable=True),
    )

    # ── 4. perfiles_profesor ──────────────────────────────────────────────────
    op.create_table(
        "perfiles_profesor",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), unique=True, nullable=False),
        sa.Column("numero_empleado", sa.String(50), nullable=True),
        sa.Column("especialidad", sa.String(200), nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
    )

    # ── 5. sesiones_usuario ───────────────────────────────────────────────────
    op.create_table(
        "sesiones_usuario",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(500), unique=True, nullable=False),
        sa.Column("dispositivo", sa.String(500), nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activa", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 6. tokens_recuperacion ────────────────────────────────────────────────
    op.create_table(
        "tokens_recuperacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("token_hash", sa.String(500), unique=True, nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 7. ciclos_escolares ───────────────────────────────────────────────────
    op.create_table(
        "ciclos_escolares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("tipo", tipo_periodo_enum, nullable=False),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("fecha_fin", sa.Date, nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 8. grupos ─────────────────────────────────────────────────────────────
    op.create_table(
        "grupos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("ciclo_escolar_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ciclos_escolares.id"), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("tipo_periodo", tipo_periodo_enum, nullable=False),
        sa.Column("turno", turno_grupo_enum, nullable=False),
        sa.Column("capacidad_maxima", sa.Integer, nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 9. materias ───────────────────────────────────────────────────────────
    op.create_table(
        "materias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("clave", sa.String(50), nullable=True),
        sa.Column("creditos", sa.Integer, nullable=True),
        sa.Column("activa", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 10. grupo_materia ─────────────────────────────────────────────────────
    op.create_table(
        "grupo_materia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grupo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupos.id"), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materias.id"), nullable=False),
        sa.Column("num_parciales", sa.Integer, nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("grupo_id", "materia_id", name="uq_grupo_materia"),
    )

    # ── 11. profesor_grupo_materia ────────────────────────────────────────────
    op.create_table(
        "profesor_grupo_materia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("grupo_materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupo_materia.id"), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("usuario_id", "grupo_materia_id", name="uq_profesor_grupo_materia"),
    )

    # ── 12. inscripciones ─────────────────────────────────────────────────────
    op.create_table(
        "inscripciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perfiles_alumno.id"), nullable=False),
        sa.Column("grupo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupos.id"), nullable=False),
        sa.Column("ciclo_escolar_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ciclos_escolares.id"), nullable=False),
        sa.Column("fecha_inscripcion", sa.Date, nullable=False),
        sa.Column("activa", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("alumno_id", "grupo_id", "ciclo_escolar_id", name="uq_inscripcion"),
    )

    # ── 13. parciales ─────────────────────────────────────────────────────────
    op.create_table(
        "parciales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grupo_materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupo_materia.id"), nullable=False),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("nombre", sa.String(200), nullable=True),
        sa.Column("fecha_apertura", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("grupo_materia_id", "numero", name="uq_parcial_grupo_materia"),
    )

    # ── 14. calificaciones ────────────────────────────────────────────────────
    op.create_table(
        "calificaciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("inscripcion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inscripciones.id"), nullable=False),
        sa.Column("parcial_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parciales.id"), nullable=False),
        sa.Column("calificacion", sa.Numeric(5, 2), nullable=False),
        sa.Column("registrado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("inscripcion_id", "parcial_id", name="uq_calificacion"),
    )

    # ── 15. calificaciones_finales ────────────────────────────────────────────
    op.create_table(
        "calificaciones_finales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("inscripcion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inscripciones.id"), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materias.id"), nullable=False),
        sa.Column("calificacion_calculada", sa.Numeric(5, 2), nullable=False),
        sa.Column("calificacion_final", sa.Numeric(5, 2), nullable=False),
        sa.Column("fue_modificada_manualmente", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("modificado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("fecha_modificacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("inscripcion_id", "materia_id", name="uq_calificacion_final"),
    )

    # ── 16. sesiones_clase ────────────────────────────────────────────────────
    op.create_table(
        "sesiones_clase",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grupo_materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupo_materia.id"), nullable=False),
        sa.Column("profesor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("hora_inicio", sa.Time, nullable=False),
        sa.Column("hora_fin", sa.Time, nullable=False),
        sa.Column("tema", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 17. asistencias ───────────────────────────────────────────────────────
    op.create_table(
        "asistencias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sesion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sesiones_clase.id"), nullable=False),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perfiles_alumno.id"), nullable=False),
        sa.Column("estado", estado_asistencia_enum, nullable=False),
        sa.Column("registrado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("sesion_id", "alumno_id", name="uq_asistencia"),
    )

    # ── 18. justificantes ─────────────────────────────────────────────────────
    op.create_table(
        "justificantes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perfiles_alumno.id"), nullable=False),
        sa.Column("asistencia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asistencias.id"), nullable=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("documento_url", sa.Text, nullable=True),
        sa.Column("registrado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("fecha_justificante", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 19. notas_alumno ──────────────────────────────────────────────────────
    op.create_table(
        "notas_alumno",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perfiles_alumno.id"), nullable=False),
        sa.Column("autor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("contenido", sa.Text, nullable=False),
        sa.Column("es_visible_alumno", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 20. horarios ──────────────────────────────────────────────────────────
    op.create_table(
        "horarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grupo_materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupo_materia.id"), nullable=False),
        sa.Column("dia_semana", dia_semana_enum, nullable=False),
        sa.Column("hora_inicio", sa.Time, nullable=False),
        sa.Column("hora_fin", sa.Time, nullable=False),
        sa.Column("aula", sa.String(100), nullable=True),
    )

    # ── 21. predicciones_riesgo ───────────────────────────────────────────────
    op.create_table(
        "predicciones_riesgo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alumno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perfiles_alumno.id"), nullable=False),
        sa.Column("grupo_materia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grupo_materia.id"), nullable=False),
        sa.Column("ciclo_escolar_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ciclos_escolares.id"), nullable=False),
        sa.Column("probabilidad_reprobacion", sa.Numeric(5, 4), nullable=False),
        sa.Column("nivel_riesgo", nivel_riesgo_enum, nullable=False),
        sa.Column("factores", postgresql.JSONB, nullable=True),
        sa.Column("modelo_version", sa.String(50), nullable=True),
        sa.Column("fecha_prediccion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 22. alertas ───────────────────────────────────────────────────────────
    op.create_table(
        "alertas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("usuario_destino_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("tipo", tipo_alerta_enum, nullable=False),
        sa.Column("mensaje", sa.Text, nullable=False),
        sa.Column("leida", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("alumno_referencia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perfiles_alumno.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 23. notificaciones ────────────────────────────────────────────────────
    op.create_table(
        "notificaciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("mensaje", sa.Text, nullable=False),
        sa.Column("tipo", tipo_notificacion_enum, nullable=False),
        sa.Column("leida", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── 24. auditoria ─────────────────────────────────────────────────────────
    op.create_table(
        "auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instituciones.id"), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("accion", sa.String(100), nullable=False),
        sa.Column("tabla_afectada", sa.String(100), nullable=False),
        sa.Column("registro_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valor_anterior", postgresql.JSONB, nullable=True),
        sa.Column("valor_nuevo", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    # Eliminar en orden inverso de FK
    op.drop_table("auditoria")
    op.drop_table("notificaciones")
    op.drop_table("alertas")
    op.drop_table("predicciones_riesgo")
    op.drop_table("horarios")
    op.drop_table("notas_alumno")
    op.drop_table("justificantes")
    op.drop_table("asistencias")
    op.drop_table("sesiones_clase")
    op.drop_table("calificaciones_finales")
    op.drop_table("calificaciones")
    op.drop_table("parciales")
    op.drop_table("inscripciones")
    op.drop_table("profesor_grupo_materia")
    op.drop_table("grupo_materia")
    op.drop_table("materias")
    op.drop_table("grupos")
    op.drop_table("ciclos_escolares")
    op.drop_table("tokens_recuperacion")
    op.drop_table("sesiones_usuario")
    op.drop_table("perfiles_profesor")
    op.drop_table("perfiles_alumno")
    op.drop_table("usuarios")
    op.drop_table("instituciones")

    # Eliminar ENUMs
    op.execute("DROP TYPE IF EXISTS tiponotificacion")
    op.execute("DROP TYPE IF EXISTS tipoalerta")
    op.execute("DROP TYPE IF EXISTS nivelriesgo")
    op.execute("DROP TYPE IF EXISTS diasemana")
    op.execute("DROP TYPE IF EXISTS estadoasistencia")
    op.execute("DROP TYPE IF EXISTS turnogrupo")
    op.execute("DROP TYPE IF EXISTS tipoperiodo")
    op.execute("DROP TYPE IF EXISTS rolusuario")
