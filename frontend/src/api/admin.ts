import apiClient from "./client"
import type {
  AdminDashboard,
  AuditoriaEntry,
  CicloEscolar,
  Grupo,
  Inscripcion,
  Materia,
  Parcial,
  PaginatedParams,
  Usuario,
} from "@/types"

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getAdminDashboard = () =>
  apiClient.get<AdminDashboard>("/admin/dashboard").then((r) => r.data)

// ── Ciclos ────────────────────────────────────────────────────────────────────
export const getCiclos = () =>
  apiClient.get<CicloEscolar[]>("/admin/ciclos").then((r) => r.data)

export const createCiclo = (body: Omit<CicloEscolar, "id" | "created_at">) =>
  apiClient.post<CicloEscolar>("/admin/ciclos", body).then((r) => r.data)

export const updateCiclo = (id: string, body: Partial<CicloEscolar>) =>
  apiClient.put<CicloEscolar>(`/admin/ciclos/${id}`, body).then((r) => r.data)

export const deleteCiclo = (id: string) =>
  apiClient.delete(`/admin/ciclos/${id}`)

// ── Grupos ────────────────────────────────────────────────────────────────────
export const getGrupos = (cicloId?: string) =>
  apiClient
    .get<Grupo[]>("/admin/grupos", { params: cicloId ? { ciclo_id: cicloId } : {} })
    .then((r) => r.data)

export const createGrupo = (body: Omit<Grupo, "id">) =>
  apiClient.post<Grupo>("/admin/grupos", body).then((r) => r.data)

export const updateGrupo = (id: string, body: Partial<Grupo>) =>
  apiClient.put<Grupo>(`/admin/grupos/${id}`, body).then((r) => r.data)

export const deleteGrupo = (id: string) => apiClient.delete(`/admin/grupos/${id}`)

// ── Materias ──────────────────────────────────────────────────────────────────
export const getMaterias = () =>
  apiClient.get<Materia[]>("/admin/materias").then((r) => r.data)

export const createMateria = (body: Omit<Materia, "id">) =>
  apiClient.post<Materia>("/admin/materias", body).then((r) => r.data)

export const updateMateria = (id: string, body: Partial<Materia>) =>
  apiClient.put<Materia>(`/admin/materias/${id}`, body).then((r) => r.data)

export const deleteMateria = (id: string) =>
  apiClient.delete(`/admin/materias/${id}`)

// ── Usuarios ──────────────────────────────────────────────────────────────────
export const getUsuarios = (params?: { rol?: string; activo?: boolean }) =>
  apiClient.get<Usuario[]>("/admin/usuarios", { params }).then((r) => r.data)

export const createUsuario = (body: Omit<Usuario, "id" | "ultimo_acceso"> & { password: string }) =>
  apiClient.post<Usuario>("/admin/usuarios", body).then((r) => r.data)

export const updateUsuario = (id: string, body: Partial<Usuario>) =>
  apiClient.put<Usuario>(`/admin/usuarios/${id}`, body).then((r) => r.data)

export const deleteUsuario = (id: string) =>
  apiClient.delete(`/admin/usuarios/${id}`)

// ── Inscripciones ─────────────────────────────────────────────────────────────
export const getInscripciones = (params?: { grupo_id?: string; ciclo_id?: string }) =>
  apiClient.get<Inscripcion[]>("/admin/inscripciones", { params }).then((r) => r.data)

export const createInscripcion = (body: {
  alumno_id: string
  grupo_id: string
  ciclo_escolar_id: string
}) => apiClient.post<Inscripcion>("/admin/inscripciones", body).then((r) => r.data)

export const deleteInscripcion = (id: string) =>
  apiClient.delete(`/admin/inscripciones/${id}`)

// ── Parciales ─────────────────────────────────────────────────────────────────
export const getParciales = (grupoMateriaId: string) =>
  apiClient
    .get<Parcial[]>(`/admin/parciales`, { params: { grupo_materia_id: grupoMateriaId } })
    .then((r) => r.data)

export const updateParcial = (id: string, body: Partial<Parcial>) =>
  apiClient.put<Parcial>(`/admin/parciales/${id}`, body).then((r) => r.data)

// ── Auditoría ─────────────────────────────────────────────────────────────────
export const getAuditoria = (params?: PaginatedParams & { accion?: string }) =>
  apiClient.get<AuditoriaEntry[]>("/admin/auditoria", { params }).then((r) => r.data)
