import { Outlet, useNavigate } from "react-router-dom"
import {
  BarChart3,
  BookOpen,
  Calendar,
  ClipboardList,
  FileText,
  GraduationCap,
  History,
  LayoutDashboard,
  Users,
} from "lucide-react"
import { Sidebar, type NavItem } from "./Sidebar"
import { Topbar } from "./Topbar"

const NAV_ITEMS: NavItem[] = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { to: "/admin/ciclos", label: "Ciclos", icon: Calendar },
  { to: "/admin/grupos", label: "Grupos", icon: BookOpen },
  { to: "/admin/materias", label: "Materias", icon: GraduationCap },
  { to: "/admin/usuarios", label: "Usuarios", icon: Users },
  { to: "/admin/inscripciones", label: "Inscripciones", icon: ClipboardList },
  { to: "/admin/boletas", label: "Boletas", icon: FileText },
  { to: "/admin/alertas", label: "Alertas IA", icon: BarChart3 },
  { to: "/admin/auditoria", label: "Auditoría", icon: History },
]

export function AdminLayout() {
  const navigate = useNavigate()

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar items={NAV_ITEMS} title="SGE Admin" />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar
          title="Sistema de Gestión Escolar"
          onNotifClick={() => navigate("/admin/alertas")}
        />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
