import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Download, FileText } from "lucide-react"
import { getDashboardAlumno, descargarBoleta, getHistorial } from "@/api/alumno"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Spinner } from "@/components/ui/Spinner"

export function BoletaAlumnoPage() {
  const [downloading, setDownloading] = useState<string | null>(null)

  const { data: dashboard, isLoading: loadingDash } = useQuery({
    queryKey: ["alumno-dashboard"],
    queryFn: getDashboardAlumno,
  })

  const { data: historial = [], isLoading: loadingHist } = useQuery({
    queryKey: ["historial"],
    queryFn: getHistorial,
  })

  const download = async (cicloId?: string) => {
    const key = cicloId ?? "current"
    setDownloading(key)
    try {
      await descargarBoleta(cicloId)
    } catch (e: unknown) {
      const err = e as { response?: { status: number } }
      if (err?.response?.status === 422) {
        alert("Aún no hay calificaciones publicadas para este ciclo.")
      } else if (err?.response?.status === 429) {
        alert("Límite de descargas alcanzado. Intenta más tarde.")
      }
    } finally {
      setDownloading(null)
    }
  }

  if (loadingDash || loadingHist) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Boleta</h2>

      {/* Current cycle */}
      {dashboard?.ciclo_nombre && (
        <Card>
          <CardContent className="flex items-center justify-between py-4 px-4">
            <div className="flex items-center gap-3">
              <FileText className="h-8 w-8 text-primary" />
              <div>
                <p className="font-semibold">Ciclo actual</p>
                <p className="text-sm text-gray-500">{dashboard.ciclo_nombre} · Grupo {dashboard.grupo_nombre}</p>
              </div>
            </div>
            <Button
              onClick={() => download()}
              loading={downloading === "current"}
            >
              <Download className="h-4 w-4" /> Descargar PDF
            </Button>
          </CardContent>
        </Card>
      )}

      {/* History */}
      {historial.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-semibold text-gray-700">Ciclos anteriores</h3>
          {historial.map(ciclo => (
            <Card key={ciclo.ciclo_id}>
              <CardContent className="flex items-center justify-between py-3 px-4">
                <div>
                  <p className="font-medium text-sm">{ciclo.ciclo_nombre}</p>
                  <p className="text-xs text-gray-500">{ciclo.fecha_inicio} — {ciclo.fecha_fin}</p>
                  {ciclo.promedio_ciclo && (
                    <p className="text-xs text-gray-500">Promedio: {ciclo.promedio_ciclo}</p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => download(ciclo.ciclo_id)}
                  loading={downloading === ciclo.ciclo_id}
                >
                  <Download className="h-4 w-4" /> PDF
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 text-center">
        Máximo 10 descargas por hora. Documento informativo — no constituye documento oficial.
      </p>
    </div>
  )
}
