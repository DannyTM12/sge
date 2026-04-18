import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { CheckCheck } from "lucide-react"
import { getNotificaciones, marcarLeida, marcarTodasLeidas } from "@/api/alumno"
import { Card, CardContent } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { Spinner } from "@/components/ui/Spinner"
import type { Notificacion } from "@/types"

const TIPO_VARIANT: Record<string, "default" | "warning" | "destructive"> = {
  info: "default",
  aviso: "warning",
  alerta: "destructive",
}

export function NotificacionesPage() {
  const qc = useQueryClient()

  const { data: notificaciones = [], isLoading } = useQuery({
    queryKey: ["notificaciones"],
    queryFn: () => getNotificaciones({ limit: 100 }),
  })

  const leer = useMutation({
    mutationFn: marcarLeida,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notificaciones"] })
      qc.invalidateQueries({ queryKey: ["notif-count"] })
    },
  })

  const leerTodas = useMutation({
    mutationFn: marcarTodasLeidas,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notificaciones"] })
      qc.invalidateQueries({ queryKey: ["notif-count"] })
    },
  })

  const noLeidas = notificaciones.filter((n: Notificacion) => !n.leida).length

  if (isLoading) return <div className="flex justify-center pt-20"><Spinner /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Notificaciones</h2>
          {noLeidas > 0 && <p className="text-sm text-gray-500">{noLeidas} sin leer</p>}
        </div>
        {noLeidas > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => leerTodas.mutate()}
            loading={leerTodas.isPending}
          >
            <CheckCheck className="h-4 w-4" /> Marcar todas leídas
          </Button>
        )}
      </div>

      {notificaciones.length === 0 && (
        <p className="text-sm text-gray-500">No tienes notificaciones.</p>
      )}

      <div className="space-y-2">
        {notificaciones.map(n => (
          <Card
            key={n.id}
            className={`cursor-pointer transition-colors ${!n.leida ? "border-primary-200 bg-primary-50" : ""}`}
            onClick={() => !n.leida && leer.mutate(n.id)}
          >
            <CardContent className="py-3 px-4 flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={TIPO_VARIANT[n.tipo] ?? "default"} className="text-xs">{n.tipo}</Badge>
                  {!n.leida && (
                    <span className="inline-block h-2 w-2 rounded-full bg-primary flex-shrink-0" />
                  )}
                </div>
                <p className="font-medium text-sm">{n.titulo}</p>
                <p className="text-sm text-gray-600">{n.mensaje}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(n.created_at).toLocaleString("es-MX")}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
