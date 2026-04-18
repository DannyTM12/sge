import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore, type Rol } from "@/stores/authStore"

interface Props {
  allowedRoles?: Rol[]
}

export function ProtectedRoute({ allowedRoles }: Props) {
  const { isAuthenticated, isHydrating, user } = useAuthStore()

  if (isHydrating) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />

  if (allowedRoles && user && !allowedRoles.includes(user.rol)) {
    return <Navigate to="/sin-acceso" replace />
  }

  return <Outlet />
}
