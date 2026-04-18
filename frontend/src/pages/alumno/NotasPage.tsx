import { useQuery } from "@tanstack/react-query"
import { getNotasAlumno } from "@/api/alumno"
import { Card, CardContent } from "@/components/ui/Card"
import { Spinner } from "@/components/ui/Spinner"

export function NotasAlumnoPage() {
  const { data: notas = [], isLoading } = useQuery({
    queryKey: ["mis-notas"],
    queryFn: () => getNotasAlumno({ limit: 50 }),
  })

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Notas de profesores</h2>
      {notas.length === 0 && (
        <p className="text-sm text-gray-500">No tienes notas visibles por parte de tus profesores.</p>
      )}
      <div className="space-y-3">
        {notas.map((n, i) => (
          <Card key={i}>
            <CardContent className="py-4 px-4">
              <p className="text-sm text-gray-900">{n.contenido}</p>
              <p className="text-xs text-gray-400 mt-2">
                {n.autor_nombre_completo} · {new Date(n.created_at).toLocaleDateString("es-MX")}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
