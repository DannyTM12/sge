import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { getAuditoria } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"

export function AuditoriaPage() {
  const [offset, setOffset] = useState(0)
  const limit = 50

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["auditoria", offset],
    queryFn: () => getAuditoria({ limit, offset }),
  })

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Auditoría</h2>
      <Card><CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{["Acción", "Tabla", "Usuario", "IP", "Fecha"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                : entries.map(e => (
                  <tr key={e.id} className="hover:bg-gray-50 font-mono text-xs">
                    <td className="px-4 py-3">{e.accion}</td>
                    <td className="px-4 py-3">{e.tabla_afectada}</td>
                    <td className="px-4 py-3">{e.usuario_nombre ?? "—"}</td>
                    <td className="px-4 py-3">{e.ip_address ?? "—"}</td>
                    <td className="px-4 py-3">{new Date(e.created_at).toLocaleString("es-MX")}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-between px-4 py-3 border-t">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="text-sm text-primary disabled:opacity-40"
          >
            ← Anterior
          </button>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={entries.length < limit}
            className="text-sm text-primary disabled:opacity-40"
          >
            Siguiente →
          </button>
        </div>
      </CardContent></Card>
    </div>
  )
}
