import { createBrowserRouter } from "react-router-dom"
import { ProtectedRoute } from "./ProtectedRoute"
import { LoginPage } from "@/pages/auth/LoginPage"
import { RecoverPasswordPage } from "@/pages/auth/RecoverPasswordPage"
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage"

// Admin
import { AdminLayout } from "@/components/layout/AdminLayout"
import { AdminDashboardPage } from "@/pages/admin/DashboardPage"
import { CiclosPage } from "@/pages/admin/CiclosPage"
import { GruposPage } from "@/pages/admin/GruposPage"
import { MateriasPage } from "@/pages/admin/MateriasPage"
import { UsuariosPage } from "@/pages/admin/UsuariosPage"
import { InscripcionesPage } from "@/pages/admin/InscripcionesPage"
import { BoletasAdminPage } from "@/pages/admin/BoletasPage"
import { AlertasPage } from "@/pages/admin/AlertasPage"
import { AuditoriaPage } from "@/pages/admin/AuditoriaPage"

// Profesor
import { ProfesorLayout } from "@/components/layout/ProfesorLayout"
import { ProfesorDashboardPage } from "@/pages/profesor/DashboardPage"
import { GrupoDetallePage } from "@/pages/profesor/GrupoDetallePage"
import { PaseListaPage } from "@/pages/profesor/PaseListaPage"
import { CalificacionesProfesorPage } from "@/pages/profesor/CalificacionesPage"
import { NotasPage } from "@/pages/profesor/NotasPage"
import { AlumnosGrupoPage } from "@/pages/profesor/AlumnosGrupoPage"

// Alumno
import { AlumnoLayout } from "@/components/layout/AlumnoLayout"
import { AlumnoDashboardPage } from "@/pages/alumno/DashboardPage"
import { CalificacionesAlumnoPage } from "@/pages/alumno/CalificacionesPage"
import { HistorialPage } from "@/pages/alumno/HistorialPage"
import { AsistenciasPage } from "@/pages/alumno/AsistenciasPage"
import { HorarioPage } from "@/pages/alumno/HorarioPage"
import { NotasAlumnoPage } from "@/pages/alumno/NotasPage"
import { NotificacionesPage } from "@/pages/alumno/NotificacionesPage"
import { BoletaAlumnoPage } from "@/pages/alumno/BoletaPage"

export const router = createBrowserRouter([
  // Auth
  { path: "/login", element: <LoginPage /> },
  { path: "/recuperar-password", element: <RecoverPasswordPage /> },
  { path: "/reset-password", element: <ResetPasswordPage /> },

  // Admin
  {
    element: <ProtectedRoute allowedRoles={["admin", "superadmin"]} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { path: "/admin", element: <AdminDashboardPage /> },
          { path: "/admin/ciclos", element: <CiclosPage /> },
          { path: "/admin/grupos", element: <GruposPage /> },
          { path: "/admin/materias", element: <MateriasPage /> },
          { path: "/admin/usuarios", element: <UsuariosPage /> },
          { path: "/admin/inscripciones", element: <InscripcionesPage /> },
          { path: "/admin/boletas", element: <BoletasAdminPage /> },
          { path: "/admin/alertas", element: <AlertasPage /> },
          { path: "/admin/auditoria", element: <AuditoriaPage /> },
        ],
      },
    ],
  },

  // Profesor
  {
    element: <ProtectedRoute allowedRoles={["profesor"]} />,
    children: [
      {
        element: <ProfesorLayout />,
        children: [
          { path: "/profesor", element: <ProfesorDashboardPage /> },
          { path: "/profesor/grupos/:grupoId", element: <GrupoDetallePage /> },
          { path: "/profesor/grupos/:grupoId/pase-lista", element: <PaseListaPage /> },
          {
            path: "/profesor/grupos/:grupoId/calificaciones",
            element: <CalificacionesProfesorPage />,
          },
          { path: "/profesor/grupos/:grupoId/notas", element: <NotasPage /> },
          { path: "/profesor/grupos/:grupoId/alumnos", element: <AlumnosGrupoPage /> },
        ],
      },
    ],
  },

  // Alumno
  {
    element: <ProtectedRoute allowedRoles={["alumno"]} />,
    children: [
      {
        element: <AlumnoLayout />,
        children: [
          { path: "/alumno", element: <AlumnoDashboardPage /> },
          { path: "/alumno/calificaciones", element: <CalificacionesAlumnoPage /> },
          { path: "/alumno/historial", element: <HistorialPage /> },
          { path: "/alumno/asistencias", element: <AsistenciasPage /> },
          { path: "/alumno/horario", element: <HorarioPage /> },
          { path: "/alumno/notas", element: <NotasAlumnoPage /> },
          { path: "/alumno/notificaciones", element: <NotificacionesPage /> },
          { path: "/alumno/boleta", element: <BoletaAlumnoPage /> },
        ],
      },
    ],
  },

  // Catch-all redirect
  { path: "/", element: <LoginPage /> },
  { path: "*", element: <LoginPage /> },
])
