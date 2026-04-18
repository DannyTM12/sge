import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { ClipboardList, GraduationCap } from "lucide-react"
import { getMisGrupos } from "@/api/profesor"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Spinner } from "@/components/ui/Spinner"

export function ProfesorDashboardPage() {
  const navigate = useNavigate()
  const { data: grupos = [], isLoading } = useQuery({
    queryKey: ["mis-grupos"],
    queryFn: getMisGrupos,
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Mis grupos</h2>
      {grupos.length === 0 && (
        <p className="text-gray-500 text-sm">No tienes grupos asignados en el ciclo activo.</p>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {grupos.map(g => (
          <Card key={g.grupo_materia_id} className="hover:shadow-md transition-shadow">
            <CardContent className="pt-6 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{g.grupo_nombre}</p>
                  <p className="text-sm text-primary font-medium">{g.materia_nombre}</p>
                  {g.materia_clave && <p className="text-xs text-gray-500">{g.materia_clave}</p>}
                </div>
                <GraduationCap className="h-5 w-5 text-gray-400" />
              </div>
              <p className="text-xs text-gray-500">{g.ciclo_nombre} · {g.num_alumnos} alumnos</p>
              <div className="flex gap-2 pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 text-xs"
                  onClick={() => navigate(`/profesor/grupos/${g.grupo_materia_id}/pase-lista`)}
                >
                  <ClipboardList className="h-3.5 w-3.5" /> Pase de lista
                </Button>
                <Button
                  size="sm"
                  className="flex-1 text-xs"
                  onClick={() => navigate(`/profesor/grupos/${g.grupo_materia_id}/calificaciones`)}
                >
                  Calificaciones
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
