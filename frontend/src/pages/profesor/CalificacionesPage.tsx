import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Save } from "lucide-react"
import { getMisGrupos, getAlumnosGrupo, getCalificacionesParcial, guardarCalificacion, actualizarCalificacion } from "@/api/profesor"
import { getParciales } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"

export function CalificacionesProfesorPage() {
  const { grupoId } = useParams<{ grupoId: string }>()
  const qc = useQueryClient()
  const [selectedParcial, setSelectedParcial] = useState<string | null>(null)
  const [califs, setCalifs] = useState<Record<string, string>>({})

  const { data: grupos = [] } = useQuery({ queryKey: ["mis-grupos"], queryFn: getMisGrupos })
  const grupo = grupos.find(g => g.grupo_materia_id === grupoId)

  const { data: parciales = [] } = useQuery({
    queryKey: ["parciales", grupoId],
    queryFn: () => getParciales(grupoId!),
    enabled: !!grupoId,
  })

  const { data: alumnos = [] } = useQuery({
    queryKey: ["alumnos-grupo", grupoId],
    queryFn: () => getAlumnosGrupo(grupoId!),
    enabled: !!grupoId,
  })

  const { data: existentes = [] } = useQuery({
    queryKey: ["calificaciones-parcial", selectedParcial],
    queryFn: () => getCalificacionesParcial(selectedParcial!),
    enabled: !!selectedParcial,
    select: (data) => {
      // Initialize editable map
      const map: Record<string, string> = {}
      data.forEach(c => {
        if (c.calificacion != null) map[c.alumno_id] = String(c.calificacion)
      })
      setCalifs(map)
      return data
    },
  })

  const guardarMutation = useMutation({
    mutationFn: guardarCalificacion,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calificaciones-parcial", selectedParcial] }),
  })

  const actualizarMutation = useMutation({
    mutationFn: ({ id, cal }: { id: string; cal: number }) => actualizarCalificacion(id, cal),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calificaciones-parcial", selectedParcial] }),
  })

  const guardarTodo = async () => {
    if (!selectedParcial) return
    for (const alumno of alumnos) {
      const val = califs[alumno.alumno_id]
      if (val === undefined || val === "") continue
      const num = parseFloat(val)
      if (isNaN(num) || num < 0 || num > 10) continue
      const existente = existentes.find(e => e.alumno_id === alumno.alumno_id)
      if (existente?.calificacion_id) {
        await actualizarMutation.mutateAsync({ id: existente.calificacion_id, cal: num })
      } else {
        await guardarMutation.mutateAsync({
          inscripcion_id: alumno.inscripcion_id,
          parcial_id: selectedParcial,
          calificacion: num,
        })
      }
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">{grupo?.grupo_nombre ?? "Grupo"} — Calificaciones</h2>
        <p className="text-sm text-primary">{grupo?.materia_nombre}</p>
      </div>

      {/* Parcial selector */}
      <div className="flex gap-2 flex-wrap">
        {parciales.map(p => (
          <button
            key={p.id}
            onClick={() => setSelectedParcial(p.id)}
            className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
              selectedParcial === p.id
                ? "bg-primary text-white border-primary"
                : "border-gray-300 hover:border-primary"
            }`}
          >
            {p.nombre}
          </button>
        ))}
      </div>

      {selectedParcial && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Alumno</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Matrícula</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Calificación (0–10)</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {alumnos.map(a => (
                    <tr key={a.alumno_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">{a.nombre_completo}</td>
                      <td className="px-4 py-3 text-gray-500">{a.matricula ?? "—"}</td>
                      <td className="px-4 py-2 w-32">
                        <Input
                          type="number"
                          min={0}
                          max={10}
                          step={0.1}
                          value={califs[a.alumno_id] ?? ""}
                          onChange={e => setCalifs(prev => ({ ...prev, [a.alumno_id]: e.target.value }))}
                          className="h-8 w-24"
                          placeholder="—"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t flex justify-end">
              <Button onClick={guardarTodo} loading={guardarMutation.isPending || actualizarMutation.isPending}>
                <Save className="h-4 w-4" /> Guardar calificaciones
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
