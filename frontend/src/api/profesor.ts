import apiClient from "./client"
import type {
  AlumnoGrupo,
  AsistenciaRegistro,
  CalificacionProfesor,
  GrupoProfesor,
  NotaAlumno,
  SesionClase,
} from "@/types"

export const getMisGrupos = () =>
  apiClient.get<GrupoProfesor[]>("/profesores/grupos").then((r) => r.data)

export const getAlumnosGrupo = (grupoMateriaId: string) =>
  apiClient
    .get<AlumnoGrupo[]>(`/profesores/grupos/${grupoMateriaId}/alumnos`)
    .then((r) => r.data)

// ── Sesiones ──────────────────────────────────────────────────────────────────
export const getSesiones = (grupoMateriaId: string) =>
  apiClient
    .get<SesionClase[]>(`/profesores/grupos/${grupoMateriaId}/sesiones`)
    .then((r) => r.data)

export const crearSesion = (body: Omit<SesionClase, "id">) =>
  apiClient.post<SesionClase>("/profesores/sesiones", body).then((r) => r.data)

// ── Asistencias ───────────────────────────────────────────────────────────────
export const getAsistenciasSesion = (sesionId: string) =>
  apiClient
    .get<AsistenciaRegistro[]>(`/profesores/sesiones/${sesionId}/asistencias`)
    .then((r) => r.data)

export const registrarAsistencias = (
  sesionId: string,
  asistencias: Array<{ alumno_id: string; estado: string }>,
) =>
  apiClient
    .post(`/profesores/sesiones/${sesionId}/asistencias`, { asistencias })
    .then((r) => r.data)

export const actualizarAsistencia = (
  sesionId: string,
  alumnoId: string,
  estado: string,
) =>
  apiClient
    .patch(`/profesores/sesiones/${sesionId}/asistencias/${alumnoId}`, { estado })
    .then((r) => r.data)

// ── Calificaciones ────────────────────────────────────────────────────────────
export const getCalificacionesParcial = (parcialId: string) =>
  apiClient
    .get<CalificacionProfesor[]>(`/profesores/parciales/${parcialId}/calificaciones`)
    .then((r) => r.data)

export const guardarCalificacion = (body: {
  inscripcion_id: string
  parcial_id: string
  calificacion: number
}) => apiClient.post("/profesores/calificaciones", body).then((r) => r.data)

export const actualizarCalificacion = (id: string, calificacion: number) =>
  apiClient.put(`/profesores/calificaciones/${id}`, { calificacion }).then((r) => r.data)

// ── Notas ─────────────────────────────────────────────────────────────────────
export const getNotas = (alumnoId: string) =>
  apiClient.get<NotaAlumno[]>(`/profesores/alumnos/${alumnoId}/notas`).then((r) => r.data)

export const crearNota = (body: {
  alumno_id: string
  contenido: string
  es_visible_alumno: boolean
}) => apiClient.post<NotaAlumno>("/profesores/notas", body).then((r) => r.data)

export const actualizarNota = (id: string, body: Partial<NotaAlumno>) =>
  apiClient.put<NotaAlumno>(`/profesores/notas/${id}`, body).then((r) => r.data)

export const eliminarNota = (id: string) =>
  apiClient.delete(`/profesores/notas/${id}`)
