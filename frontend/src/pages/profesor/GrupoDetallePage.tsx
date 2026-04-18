import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ClipboardList, FileText, Users } from "lucide-react"
import { getMisGrupos } from "@/api/profesor"
import { Card, CardContent } from "@/components/ui/Card"

export function GrupoDetallePage() {
  const { grupoId } = useParams<{ grupoId: string }>()
  const navigate = useNavigate()

  const { data: grupos = [] } = useQuery({ queryKey: ["mis-grupos"], queryFn: getMisGrupos })
  const grupo = grupos.find(g => g.grupo_materia_id === grupoId)

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">{grupo?.grupo_nombre ?? "Grupo"}</h2>
        <p className="text-primary font-medium">{grupo?.materia_nombre}</p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate(`/profesor/grupos/${grupoId}/pase-lista`)}>
          <CardContent className="flex items-center gap-3 pt-6">
            <ClipboardList className="h-8 w-8 text-primary" />
            <div><p className="font-semibold">Pase de lista</p><p className="text-xs text-gray-500">Registrar asistencias</p></div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate(`/profesor/grupos/${grupoId}/calificaciones`)}>
          <CardContent className="flex items-center gap-3 pt-6">
            <FileText className="h-8 w-8 text-accent" />
            <div><p className="font-semibold">Calificaciones</p><p className="text-xs text-gray-500">Capturar calificaciones</p></div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md" onClick={() => navigate(`/profesor/grupos/${grupoId}/alumnos`)}>
          <CardContent className="flex items-center gap-3 pt-6">
            <Users className="h-8 w-8 text-green-600" />
            <div><p className="font-semibold">Alumnos</p><p className="text-xs text-gray-500">Lista del grupo</p></div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
