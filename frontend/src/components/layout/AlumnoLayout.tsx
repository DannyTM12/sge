import { Outlet, useNavigate } from "react-router-dom"
import {
  Bell,
  BookOpen,
  Calendar,
  ClipboardList,
  FileText,
  LayoutDashboard,
  MessageSquare,
} from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { Sidebar, type NavItem } from "./Sidebar"
import { Topbar } from "./Topbar"
import { getNoLeidas } from "@/api/alumno"

const NAV_ITEMS: NavItem[] = [
  { to: "/alumno", label: "Inicio", icon: LayoutDashboard },
  { to: "/alumno/calificaciones", label: "Calificaciones", icon: BookOpen },
  { to: "/alumno/historial", label: "Historial", icon: ClipboardList },
  { to: "/alumno/asistencias", label: "Asistencias", icon: Calendar },
  { to: "/alumno/horario", label: "Horario", icon: Calendar },
  { to: "/alumno/notas", label: "Notas", icon: MessageSquare },
  { to: "/alumno/notificaciones", label: "Notificaciones", icon: Bell },
  { to: "/alumno/boleta", label: "Boleta", icon: FileText },
]

export function AlumnoLayout() {
  const navigate = useNavigate()
  const { data } = useQuery({
    queryKey: ["notif-count"],
    queryFn: getNoLeidas,
    refetchInterval: 30_000,
  })

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar items={NAV_ITEMS} title="SGE Alumno" />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar
          title="Portal Alumno"
          notifCount={data?.count}
          onNotifClick={() => navigate("/alumno/notificaciones")}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
