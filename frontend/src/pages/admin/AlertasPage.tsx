import { useQuery } from "@tanstack/react-query"
import apiClient from "@/api/client"
import { Card, CardContent } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"

interface Alerta {
  id: string
  tipo: string
  mensaje: string
  leida: boolean
  created_at: string
  alumno_nombre?: string
}

export function AlertasPage() {
  const { data: alertas = [], isLoading } = useQuery({
    queryKey: ["alertas"],
    queryFn: () => apiClient.get<Alerta[]>("/admin/alertas").then(r => r.data),
  })

  const TIPO_VARIANT: Record<string, "destructive" | "warning" | "default"> = {
    riesgo_reprobacion: "destructive",
    faltas_excesivas: "warning",
    calificacion_baja: "destructive",
    nota_profesor: "default",
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Alertas IA</h2>
      <Card><CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{["Tipo", "Mensaje", "Alumno", "Fecha", "Estado"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                : alertas.map(a => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3"><Badge variant={TIPO_VARIANT[a.tipo] ?? "default"}>{a.tipo.replace(/_/g, " ")}</Badge></td>
                    <td className="px-4 py-3 max-w-xs truncate">{a.mensaje}</td>
                    <td className="px-4 py-3">{a.alumno_nombre ?? "—"}</td>
                    <td className="px-4 py-3">{new Date(a.created_at).toLocaleDateString("es-MX")}</td>
                    <td className="px-4 py-3"><Badge variant={a.leida ? "secondary" : "warning"}>{a.leida ? "Leída" : "Nueva"}</Badge></td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </CardContent></Card>
    </div>
  )
}
