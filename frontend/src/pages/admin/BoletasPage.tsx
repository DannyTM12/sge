import { useQuery } from "@tanstack/react-query"
import { Download } from "lucide-react"
import { getInscripciones } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"

export function BoletasAdminPage() {
  const { data: inscripciones = [], isLoading } = useQuery({
    queryKey: ["inscripciones"],
    queryFn: () => getInscripciones(),
  })

  const downloadBoleta = (alumnoId: string, cicloId: string) => {
    window.open(`/api/admin/boletas/${alumnoId}/${cicloId}`, "_blank")
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Boletas</h2>
      <Card><CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{["Alumno", "Matrícula", "Grupo", "Ciclo", "Descargar"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                : inscripciones.filter(i => i.activa).map(i => (
                  <tr key={i.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{i.alumno_nombre}</td>
                    <td className="px-4 py-3">{i.matricula ?? "—"}</td>
                    <td className="px-4 py-3">{i.grupo_nombre}</td>
                    <td className="px-4 py-3">{i.ciclo_nombre}</td>
                    <td className="px-4 py-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => downloadBoleta(i.alumno_id, "")}
                      >
                        <Download className="h-4 w-4 mr-1" /> PDF
                      </Button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </CardContent></Card>
    </div>
  )
}
