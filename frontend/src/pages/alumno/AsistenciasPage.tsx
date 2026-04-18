import { useQuery } from "@tanstack/react-query"
import { getAsistencias, getResumenAsistencias } from "@/api/alumno"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Spinner } from "@/components/ui/Spinner"

const ESTADO_VARIANT: Record<string, "success" | "warning" | "destructive" | "default"> = {
  presente: "success",
  tardanza: "warning",
  ausente: "destructive",
  justificada: "default",
}

export function AsistenciasPage() {
  const { data: resumen = [], isLoading: loadingResumen } = useQuery({
    queryKey: ["resumen-asistencias"],
    queryFn: getResumenAsistencias,
  })

  const { data: asistencias = [], isLoading: loadingLista } = useQuery({
    queryKey: ["mis-asistencias"],
    queryFn: () => getAsistencias({ limit: 100 }),
  })

  if (loadingResumen || loadingLista) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Mis asistencias</h2>

      {/* Resumen por materia */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {resumen.map(r => {
          const pct = r.porcentaje_asistencia != null ? Math.round(r.porcentaje_asistencia * 100) : null
          return (
            <Card key={r.materia_id} className={pct != null && pct < 80 ? "border-red-300" : ""}>
              <CardContent className="pt-4">
                <p className="font-medium text-sm">{r.materia_nombre}</p>
                <div className="mt-2 flex items-center justify-between">
                  <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
                    <div
                      className={`h-2 rounded-full ${pct != null && pct < 80 ? "bg-red-500" : "bg-green-500"}`}
                      style={{ width: `${pct ?? 0}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold">{pct != null ? `${pct}%` : "—"}</span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {r.presentes}P · {r.tardanzas}T · {r.ausentes}A · {r.justificadas}J / {r.total_sesiones}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Detalle */}
      <Card>
        <CardHeader><CardTitle className="text-base">Detalle de sesiones</CardTitle></CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Fecha", "Hora", "Materia", "Estado"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {asistencias.map((a, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{a.sesion_fecha}</td>
                    <td className="px-4 py-3">{a.sesion_hora_inicio}</td>
                    <td className="px-4 py-3">{a.materia_nombre}</td>
                    <td className="px-4 py-3">
                      <Badge variant={ESTADO_VARIANT[a.estado] ?? "default"}>{a.estado}</Badge>
                    </td>
                  </tr>
                ))}
                {asistencias.length === 0 && (
                  <tr><td colSpan={4} className="text-center py-8 text-gray-400">Sin sesiones registradas.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
