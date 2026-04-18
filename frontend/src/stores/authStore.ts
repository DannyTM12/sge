import { create } from "zustand"
import { setAccessToken } from "@/api/client"
import apiClient from "@/api/client"

export type Rol = "superadmin" | "admin" | "profesor" | "alumno"

export interface AuthUser {
  id: string
  nombre: string
  apellido_paterno: string
  apellido_materno?: string
  email: string
  rol: Rol
  institucion_id: string
}

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isHydrating: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hydrate: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isHydrating: true,

  login: async (email, password) => {
    const params = new URLSearchParams()
    params.append("username", email)
    params.append("password", password)
    const { data } = await apiClient.post("/auth/login", params, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
    setAccessToken(data.access_token)
    set({ user: data.user, isAuthenticated: true })
  },

  logout: async () => {
    try {
      await apiClient.post("/auth/logout")
    } finally {
      setAccessToken(null)
      set({ user: null, isAuthenticated: false })
    }
  },

  hydrate: async () => {
    try {
      const { data } = await apiClient.post("/auth/refresh", {})
      setAccessToken(data.access_token)
      set({ user: data.user, isAuthenticated: true })
    } catch {
      setAccessToken(null)
      set({ user: null, isAuthenticated: false })
    } finally {
      set({ isHydrating: false })
    }
  },
}))
