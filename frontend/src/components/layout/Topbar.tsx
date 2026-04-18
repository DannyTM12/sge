import { Bell, LogOut, Menu } from "lucide-react"
import { useState } from "react"
import { useAuthStore } from "@/stores/authStore"
import { Button } from "@/components/ui/Button"

interface TopbarProps {
  title?: string
  notifCount?: number
  onNotifClick?: () => void
  onMenuClick?: () => void
}

export function Topbar({ title, notifCount, onNotifClick, onMenuClick }: TopbarProps) {
  const { user, logout } = useAuthStore()
  const [loggingOut, setLoggingOut] = useState(false)

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
  }

  const initials = user
    ? `${user.nombre[0] ?? ""}${user.apellido_paterno[0] ?? ""}`.toUpperCase()
    : "?"

  return (
    <header className="flex items-center justify-between h-14 px-4 border-b border-gray-200 bg-white">
      <div className="flex items-center gap-3">
        <button
          className="md:hidden p-2 rounded hover:bg-gray-100"
          onClick={onMenuClick}
          aria-label="Abrir menú"
        >
          <Menu className="h-5 w-5 text-gray-600" />
        </button>
        {title && <h1 className="font-semibold text-gray-800 text-sm hidden sm:block">{title}</h1>}
      </div>

      <div className="flex items-center gap-2">
        {onNotifClick && (
          <button
            onClick={onNotifClick}
            className="relative p-2 rounded-full hover:bg-gray-100"
            aria-label="Notificaciones"
          >
            <Bell className="h-5 w-5 text-gray-600" />
            {notifCount !== undefined && notifCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-white">
                {notifCount > 99 ? "99+" : notifCount}
              </span>
            )}
          </button>
        )}

        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-700 text-white text-xs font-bold">
          {initials}
        </div>

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={handleLogout}
          loading={loggingOut}
          aria-label="Cerrar sesión"
        >
          <LogOut className="h-4 w-4 text-gray-600" />
        </Button>
      </div>
    </header>
  )
}
