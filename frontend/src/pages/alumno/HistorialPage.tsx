import { useQuery } from "@tanstack/react-query"
import { getHistorial } from "@/api/alumno"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Spinner } from "@/components/ui/Spinner"

export function HistorialPage() {
  const { data: historial = [], isLoading } = useQuery({
    queryKey: ["historial"],
    queryFn: getHistorial,
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Historial académico</h2>
      {historial.length === 0 && (
        <p className="text-sm text-gray-500">No hay historial de ciclos anteriores.</p>
      )}
      {historial.map(ciclo => (
        <Card key={ciclo.ciclo_id}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{ciclo.ciclo_nombre}</CardTitle>
              {ciclo.promedio_ciclo && (
                <Badge variant={parseFloat(ciclo.promedio_ciclo) >= 7 ? "success" : "warning"}>
                  Promedio: {ciclo.promedio_ciclo}
                </Badge>
              )}
            </div>
            <p className="text-xs text-gray-500">{ciclo.fecha_inicio} — {ciclo.fecha_fin}</p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-xs">
                    <th className="text-left pb-2">Materia</th>
                    {ciclo.materias[0]?.parciales.map(p => (
                      <th key={p.parcial_numero} className="text-center pb-2 w-14">P{p.parcial_numero}</th>
                    ))}
                    <th className="text-center pb-2 w-16">Final</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {ciclo.materias.map(m => (
                    <tr key={m.materia_id} className="py-1">
                      <td className="py-2 pr-4">{m.materia_nombre}</td>
                      {m.parciales.map(p => (
                        <td key={p.parcial_numero} className="text-center py-2 text-gray-600">
                          {p.esta_publicada && p.calificacion != null ? p.calificacion : "—"}
                        </td>
                      ))}
                      <td className="text-center py-2 font-semibold">
                        {m.calificacion_final ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
