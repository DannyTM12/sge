import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { BookOpen, Bell, AlertTriangle, TrendingUp } from "lucide-react"
import { getDashboardAlumno } from "@/api/alumno"
import { Card, CardContent } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Spinner } from "@/components/ui/Spinner"

export function AlumnoDashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ["alumno-dashboard"],
    queryFn: getDashboardAlumno,
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">{data?.nombre_completo}</h2>
        <p className="text-sm text-gray-500">
          {data?.grupo_nombre
            ? `Grupo ${data.grupo_nombre} · ${data.ciclo_nombre}`
            : "Sin inscripción activa"}
          {data?.matricula && ` · Matrícula: ${data.matricula}`}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="text-center">
          <CardContent className="pt-4 pb-3">
            <TrendingUp className="h-6 w-6 text-primary mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-900">{data?.promedio_general ?? "—"}</p>
            <p className="text-xs text-gray-500">Promedio</p>
          </CardContent>
        </Card>
        <Card className="text-center">
          <CardContent className="pt-4 pb-3">
            <BookOpen className="h-6 w-6 text-accent mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-900">{data?.materias.length ?? 0}</p>
            <p className="text-xs text-gray-500">Materias</p>
          </CardContent>
        </Card>
        <Card
          className="text-center cursor-pointer hover:shadow-md"
          onClick={() => navigate("/alumno/notificaciones")}
        >
          <CardContent className="pt-4 pb-3">
            <Bell className="h-6 w-6 text-blue-500 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-900">{data?.alertas_no_leidas ?? 0}</p>
            <p className="text-xs text-gray-500">Notificaciones</p>
          </CardContent>
        </Card>
        <Card className={`text-center ${(data?.materias_en_riesgo ?? 0) > 0 ? "border-red-300" : ""}`}>
          <CardContent className="pt-4 pb-3">
            <AlertTriangle className={`h-6 w-6 mx-auto mb-1 ${(data?.materias_en_riesgo ?? 0) > 0 ? "text-red-500" : "text-gray-300"}`} />
            <p className="text-2xl font-bold text-gray-900">{data?.materias_en_riesgo ?? 0}</p>
            <p className="text-xs text-gray-500">En riesgo</p>
          </CardContent>
        </Card>
      </div>

      {/* Materias summary */}
      {(data?.materias.length ?? 0) > 0 && (
        <div className="space-y-2">
          <h3 className="font-semibold text-gray-800">Mis materias</h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {data!.materias.map(m => (
              <Card key={m.materia_id} className="hover:shadow-sm cursor-pointer" onClick={() => navigate("/alumno/calificaciones")}>
                <CardContent className="py-3 px-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{m.materia_nombre}</p>
                    {m.profesor_nombre && <p className="text-xs text-gray-500">{m.profesor_nombre}</p>}
                  </div>
                  {m.calificacion_final ? (
                    <Badge variant={parseFloat(m.calificacion_final) >= 6 ? "success" : "destructive"}>
                      {m.calificacion_final}
                    </Badge>
                  ) : m.calificacion_calculada ? (
                    <Badge variant="secondary">{m.calificacion_calculada}</Badge>
                  ) : (
                    <Badge variant="secondary">—</Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
