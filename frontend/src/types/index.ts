// ── Auth ──────────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string
  token_type: string
  user: import("@/stores/authStore").AuthUser
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export interface CicloEscolar {
  id: string
  nombre: string
  tipo: "semestral" | "cuatrimestral"
  fecha_inicio: string
  fecha_fin: string
  activo: boolean
  created_at: string
}

export interface Grupo {
  id: string
  nombre: string
  ciclo_escolar_id: string
  ciclo_nombre?: string
  turno: "matutino" | "vespertino" | "mixto"
  capacidad_maxima: number
  activo: boolean
}

export interface Materia {
  id: string
  nombre: string
  clave: string | null
  creditos: number | null
  activa: boolean
}

export interface Usuario {
  id: string
  nombre: string
  apellido_paterno: string
  apellido_materno?: string
  email: string
  rol: "superadmin" | "admin" | "profesor" | "alumno"
  activo: boolean
  ultimo_acceso?: string
  matricula?: string
  numero_empleado?: string
}

export interface Inscripcion {
  id: string
  alumno_id: string
  alumno_nombre: string
  matricula?: string
  grupo_id: string
  grupo_nombre: string
  ciclo_nombre: string
  fecha_inscripcion: string
  activa: boolean
}

export interface Parcial {
  id: string
  grupo_materia_id: string
  numero: number
  nombre: string
  fecha_apertura?: string
  fecha_cierre?: string
  activo: boolean
}

export interface AdminDashboard {
  total_alumnos: number
  total_profesores: number
  grupos_activos: number
  ciclo_activo?: CicloEscolar
  alertas_no_leidas: number
  materias_en_riesgo: number
}

export interface AuditoriaEntry {
  id: string
  accion: string
  tabla_afectada: string
  registro_id?: string
  valor_anterior?: Record<string, unknown>
  valor_nuevo?: Record<string, unknown>
  ip_address?: string
  user_agent?: string
  created_at: string
  usuario_nombre?: string
}

// ── Profesor ──────────────────────────────────────────────────────────────────
export interface GrupoProfesor {
  grupo_id: string
  grupo_nombre: string
  materia_id: string
  materia_nombre: string
  materia_clave?: string
  ciclo_nombre: string
  num_alumnos: number
  num_parciales: number
  grupo_materia_id: string
}

export interface AlumnoGrupo {
  alumno_id: string
  nombre_completo: string
  matricula?: string
  inscripcion_id: string
}

export interface SesionClase {
  id: string
  fecha: string
  hora_inicio: string
  hora_fin: string
  tema?: string
  grupo_materia_id: string
}

export interface AsistenciaRegistro {
  alumno_id: string
  nombre_completo: string
  matricula?: string
  estado: "presente" | "ausente" | "tardanza" | "justificada"
}

export interface CalificacionProfesor {
  alumno_id: string
  nombre_completo: string
  matricula?: string
  calificacion?: number
  calificacion_id?: string
}

export interface NotaAlumno {
  id: string
  alumno_id: string
  alumno_nombre?: string
  contenido: string
  es_visible_alumno: boolean
  created_at: string
}

// ── Alumno ────────────────────────────────────────────────────────────────────
export interface MiCalificacionParcial {
  parcial_numero: number
  parcial_nombre?: string
  calificacion?: string
  fecha_registro?: string
  esta_publicada: boolean
}

export interface MiMateria {
  materia_id: string
  materia_nombre: string
  clave?: string
  profesor_nombre?: string
  num_parciales: number
  parciales: MiCalificacionParcial[]
  calificacion_calculada?: string
  calificacion_final?: string
  fue_modificada_manualmente: boolean
}

export interface DashboardAlumno {
  nombre_completo: string
  matricula?: string
  grupo_nombre?: string
  ciclo_nombre?: string
  ciclo_id?: string
  promedio_general?: string
  materias_en_riesgo: number
  alertas_no_leidas: number
  materias: MiMateria[]
}

export interface HistorialCiclo {
  ciclo_id: string
  ciclo_nombre: string
  ciclo_tipo: string
  fecha_inicio: string
  fecha_fin: string
  materias: MiMateria[]
  promedio_ciclo?: string
}

export interface MiAsistencia {
  sesion_fecha: string
  sesion_hora_inicio: string
  materia_nombre: string
  estado: "presente" | "ausente" | "tardanza" | "justificada"
  justificante_descripcion?: string
}

export interface ResumenAsistencia {
  materia_id: string
  materia_nombre: string
  total_sesiones: number
  presentes: number
  ausentes: number
  tardanzas: number
  justificadas: number
  porcentaje_asistencia?: number
}

export interface MiHorario {
  dia_semana: string
  hora_inicio: string
  hora_fin: string
  materia_nombre: string
  profesor_nombre?: string
  aula?: string
}

export interface MiNota {
  contenido: string
  autor_nombre_completo: string
  created_at: string
}

export interface Notificacion {
  id: string
  titulo: string
  mensaje: string
  tipo: "info" | "alerta" | "aviso"
  leida: boolean
  created_at: string
}

export interface PaginatedParams {
  limit?: number
  offset?: number
}
