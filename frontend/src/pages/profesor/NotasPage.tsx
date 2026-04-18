import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Eye, EyeOff } from "lucide-react"
import { getAlumnosGrupo, getNotas, crearNota, actualizarNota } from "@/api/profesor"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog"
import { useForm } from "react-hook-form"

export function NotasPage() {
  const { grupoId } = useParams<{ grupoId: string }>()
  const qc = useQueryClient()
  const [selectedAlumno, setSelectedAlumno] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  const { data: alumnos = [] } = useQuery({
    queryKey: ["alumnos-grupo", grupoId],
    queryFn: () => getAlumnosGrupo(grupoId!),
    enabled: !!grupoId,
  })

  const { data: notas = [] } = useQuery({
    queryKey: ["notas-alumno", selectedAlumno],
    queryFn: () => getNotas(selectedAlumno!),
    enabled: !!selectedAlumno,
  })

  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<{
    contenido: string; es_visible_alumno: boolean
  }>({ defaultValues: { es_visible_alumno: false } })

  const crear = useMutation({
    mutationFn: crearNota,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notas-alumno", selectedAlumno] }); setOpen(false); reset() },
  })

  const toggleVisible = useMutation({
    mutationFn: ({ id, es_visible_alumno }: { id: string; es_visible_alumno: boolean }) =>
      actualizarNota(id, { es_visible_alumno }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notas-alumno", selectedAlumno] }),
  })

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Notas de alumnos</h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Alumno list */}
        <Card>
          <CardContent className="p-0">
            <div className="divide-y max-h-96 overflow-y-auto">
              {alumnos.map(a => (
                <button
                  key={a.alumno_id}
                  onClick={() => setSelectedAlumno(a.alumno_id)}
                  className={`w-full text-left px-4 py-3 text-sm hover:bg-gray-50 ${
                    selectedAlumno === a.alumno_id ? "bg-primary-50 font-semibold" : ""
                  }`}
                >
                  {a.nombre_completo}
                  {a.matricula && <span className="text-gray-400 ml-1">({a.matricula})</span>}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Notas panel */}
        <div className="md:col-span-2 space-y-3">
          {selectedAlumno && (
            <>
              <div className="flex justify-between items-center">
                <p className="font-medium text-sm">Notas del alumno</p>
                <Button size="sm" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Nueva nota</Button>
              </div>
              <div className="space-y-2">
                {notas.map(n => (
                  <Card key={n.id}>
                    <CardContent className="py-3 px-4 flex items-start justify-between gap-3">
                      <p className="text-sm flex-1">{n.contenido}</p>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant={n.es_visible_alumno ? "success" : "secondary"} className="text-xs">
                          {n.es_visible_alumno ? "Visible" : "Privada"}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => toggleVisible.mutate({ id: n.id, es_visible_alumno: !n.es_visible_alumno })}
                          title={n.es_visible_alumno ? "Ocultar al alumno" : "Mostrar al alumno"}
                        >
                          {n.es_visible_alumno ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {notas.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-6">Sin notas para este alumno.</p>
                )}
              </div>
            </>
          )}
          {!selectedAlumno && (
            <p className="text-sm text-gray-400 text-center py-12">Selecciona un alumno de la lista.</p>
          )}
        </div>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nueva nota</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(data => crear.mutate({ alumno_id: selectedAlumno!, ...data }))} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Contenido</label>
              <textarea
                className="w-full rounded-md border border-gray-300 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                rows={4}
                placeholder="Observación sobre el alumno..."
                {...register("contenido")}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("es_visible_alumno")} />
              Visible para el alumno
            </label>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button type="submit" loading={isSubmitting}>Guardar</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
