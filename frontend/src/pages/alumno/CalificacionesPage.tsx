import { useQuery } from "@tanstack/react-query"
import { getCalificacionesAlumno } from "@/api/alumno"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Spinner } from "@/components/ui/Spinner"

export function CalificacionesAlumnoPage() {
  const { data: materias = [], isLoading } = useQuery({
    queryKey: ["mis-calificaciones"],
    queryFn: getCalificacionesAlumno,
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Mis calificaciones</h2>
      {materias.length === 0 && (
        <p className="text-sm text-gray-500">No hay calificaciones en el ciclo activo.</p>
      )}
      <div className="space-y-4">
        {materias.map(m => (
          <Card key={m.materia_id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">{m.materia_nombre}</CardTitle>
                  {m.profesor_nombre && <p className="text-sm text-gray-500">{m.profesor_nombre}</p>}
                </div>
                <div className="text-right">
                  {m.calificacion_final && (
                    <Badge variant={parseFloat(m.calificacion_final) >= 6 ? "success" : "destructive"} className="text-sm">
                      Final: {m.calificacion_final}
                      {m.fue_modificada_manualmente && " *"}
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3 flex-wrap">
                {m.parciales.map(p => (
                  <div
                    key={p.parcial_numero}
                    className={`flex flex-col items-center p-3 rounded-lg border min-w-16 ${
                      p.esta_publicada ? "bg-gray-50 border-gray-200" : "bg-gray-100 border-gray-200 opacity-60"
                    }`}
                  >
                    <p className="text-xs text-gray-500">{p.parcial_nombre ?? `P${p.parcial_numero}`}</p>
                    <p className="text-lg font-bold text-gray-900">
                      {p.esta_publicada && p.calificacion != null ? p.calificacion : "—"}
                    </p>
                  </div>
                ))}
                {m.calificacion_calculada && (
                  <div className="flex flex-col items-center p-3 rounded-lg border border-primary-200 bg-primary-50 min-w-16">
                    <p className="text-xs text-primary-700">Promedio</p>
                    <p className="text-lg font-bold text-primary-800">{m.calificacion_calculada}</p>
                  </div>
                )}
              </div>
              {m.fue_modificada_manualmente && (
                <p className="text-xs text-gray-400 mt-2">* Calificación ajustada por administración</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
