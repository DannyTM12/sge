import apiClient from "./client"
import type {
  DashboardAlumno,
  HistorialCiclo,
  MiAsistencia,
  MiHorario,
  MiMateria,
  MiNota,
  Notificacion,
  PaginatedParams,
  ResumenAsistencia,
} from "@/types"

export const getDashboardAlumno = () =>
  apiClient.get<DashboardAlumno>("/alumnos/dashboard").then((r) => r.data)

export const getCalificacionesAlumno = () =>
  apiClient.get<MiMateria[]>("/alumnos/calificaciones").then((r) => r.data)

export const getHistorial = () =>
  apiClient.get<HistorialCiclo[]>("/alumnos/calificaciones/historial").then((r) => r.data)

export const getAsistencias = (params?: PaginatedParams) =>
  apiClient.get<MiAsistencia[]>("/alumnos/asistencias", { params }).then((r) => r.data)

export const getResumenAsistencias = () =>
  apiClient.get<ResumenAsistencia[]>("/alumnos/asistencias/resumen").then((r) => r.data)

export const getHorario = () =>
  apiClient.get<MiHorario[]>("/alumnos/horario").then((r) => r.data)

export const getNotasAlumno = (params?: PaginatedParams) =>
  apiClient.get<MiNota[]>("/alumnos/notas", { params }).then((r) => r.data)

// ── Notificaciones ────────────────────────────────────────────────────────────
export const getNotificaciones = (
  params?: PaginatedParams & { solo_no_leidas?: boolean },
) =>
  apiClient.get<Notificacion[]>("/alumnos/notificaciones", { params }).then((r) => r.data)

export const getNoLeidas = () =>
  apiClient
    .get<{ count: number }>("/alumnos/notificaciones/no-leidas")
    .then((r) => r.data)

export const marcarLeida = (id: string) =>
  apiClient
    .patch<Notificacion>(`/alumnos/notificaciones/${id}/leer`)
    .then((r) => r.data)

export const marcarTodasLeidas = () =>
  apiClient
    .patch<{ actualizadas: number }>("/alumnos/notificaciones/marcar-todas-leidas")
    .then((r) => r.data)

// ── Boleta ────────────────────────────────────────────────────────────────────
export const descargarBoleta = async (cicloId?: string) => {
  const url = cicloId ? `/alumnos/boleta/${cicloId}` : "/alumnos/boleta"
  const response = await apiClient.get(url, { responseType: "blob" })
  const blob = new Blob([response.data], { type: "application/pdf" })
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = blobUrl
  const cd = response.headers["content-disposition"] ?? ""
  const match = cd.match(/filename="?([^"]+)"?/)
  a.download = match ? match[1] : "boleta.pdf"
  a.click()
  URL.revokeObjectURL(blobUrl)
}
