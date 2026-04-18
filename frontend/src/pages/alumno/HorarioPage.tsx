import { useQuery } from "@tanstack/react-query"
import { getHorario } from "@/api/alumno"
import { Card, CardContent } from "@/components/ui/Card"
import { Spinner } from "@/components/ui/Spinner"

const DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]

export function HorarioPage() {
  const { data: horario = [], isLoading } = useQuery({
    queryKey: ["mi-horario"],
    queryFn: getHorario,
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  const byDia = DIAS.reduce<Record<string, typeof horario>>((acc, dia) => {
    acc[dia] = horario.filter(h => h.dia_semana === dia)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Mi horario</h2>
      {horario.length === 0 && (
        <p className="text-sm text-gray-500">No hay horario asignado para el ciclo activo.</p>
      )}
      <div className="space-y-3">
        {DIAS.filter(d => byDia[d].length > 0).map(dia => (
          <Card key={dia}>
            <CardContent className="py-3 px-4">
              <p className="font-semibold text-primary capitalize mb-2">{dia === "miercoles" ? "Miércoles" : dia.charAt(0).toUpperCase() + dia.slice(1)}</p>
              <div className="space-y-2">
                {byDia[dia].map((h, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <div className="text-gray-500 w-28 shrink-0">
                      {h.hora_inicio.slice(0, 5)} – {h.hora_fin.slice(0, 5)}
                    </div>
                    <div className="flex-1">
                      <span className="font-medium">{h.materia_nombre}</span>
                      {h.aula && <span className="text-gray-400 ml-2 text-xs">{h.aula}</span>}
                    </div>
                    {h.profesor_nombre && (
                      <span className="text-xs text-gray-400 hidden sm:block">{h.profesor_nombre}</span>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
