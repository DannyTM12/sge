import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { MessageSquare } from "lucide-react"
import { getAlumnosGrupo } from "@/api/profesor"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Spinner } from "@/components/ui/Spinner"

export function AlumnosGrupoPage() {
  const { grupoId } = useParams<{ grupoId: string }>()
  const navigate = useNavigate()

  const { data: alumnos = [], isLoading } = useQuery({
    queryKey: ["alumnos-grupo", grupoId],
    queryFn: () => getAlumnosGrupo(grupoId!),
    enabled: !!grupoId,
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Alumnos del grupo</h2>
      <Card>
        <CardContent className="p-0">
          <div className="divide-y">
            {alumnos.map(a => (
              <div key={a.alumno_id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium text-sm">{a.nombre_completo}</p>
                  {a.matricula && <p className="text-xs text-gray-500">{a.matricula}</p>}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate(`/profesor/grupos/${grupoId}/notas`)}
                >
                  <MessageSquare className="h-4 w-4 mr-1" /> Notas
                </Button>
              </div>
            ))}
            {alumnos.length === 0 && (
              <p className="text-center text-gray-400 py-8 text-sm">No hay alumnos en este grupo.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
