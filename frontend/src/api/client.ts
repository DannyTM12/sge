import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios"

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // send HttpOnly refresh-token cookie
})

// ── Token management ──────────────────────────────────────────────────────────
let accessToken: string | null = null

export const setAccessToken = (token: string | null) => {
  accessToken = token
}

export const getAccessToken = () => accessToken

// ── Request interceptor: attach Bearer token ─────────────────────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// ── Response interceptor: silent token refresh ───────────────────────────────
let isRefreshing = false
let refreshQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

const processQueue = (err: unknown, token: string | null) => {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (err) reject(err)
    else resolve(token as string)
  })
  refreshQueue = []
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        refreshQueue.push({ resolve, reject })
      })
        .then((token) => {
          original.headers.Authorization = `Bearer ${token}`
          return apiClient(original)
        })
        .catch(() => Promise.reject(error))
    }

    original._retry = true
    isRefreshing = true

    try {
      const { data } = await axios.post(
        `${BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true },
      )
      const newToken: string = data.access_token
      setAccessToken(newToken)
      processQueue(null, newToken)
      original.headers.Authorization = `Bearer ${newToken}`
      return apiClient(original)
    } catch (refreshErr) {
      processQueue(refreshErr, null)
      setAccessToken(null)
      window.dispatchEvent(new CustomEvent("auth:logout"))
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  },
)

export default apiClient
