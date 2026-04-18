import { Outlet } from "react-router-dom"
import { LayoutDashboard, BookOpen } from "lucide-react"
import { Sidebar, type NavItem } from "./Sidebar"
import { Topbar } from "./Topbar"

const NAV_ITEMS: NavItem[] = [
  { to: "/profesor", label: "Dashboard", icon: LayoutDashboard },
  { to: "/profesor/grupos", label: "Mis Grupos", icon: BookOpen },
]

export function ProfesorLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar items={NAV_ITEMS} title="SGE Profesor" />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar title="Portal Profesor" />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
