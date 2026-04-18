import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { getCiclos, getGrupos, getUsuarios, getInscripciones, createInscripcion, deleteInscripcion } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog"

export function InscripcionesPage() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [cicloFilter, setCicloFilter] = useState("")

  const { data: inscripciones = [], isLoading } = useQuery({
    queryKey: ["inscripciones", cicloFilter],
    queryFn: () => getInscripciones(cicloFilter ? { ciclo_id: cicloFilter } : {}),
  })
  const { data: ciclos = [] } = useQuery({ queryKey: ["ciclos"], queryFn: getCiclos })
  const { data: grupos = [] } = useQuery({ queryKey: ["grupos"], queryFn: () => getGrupos() })
  const { data: alumnos = [] } = useQuery({ queryKey: ["usuarios-alumno"], queryFn: () => getUsuarios({ rol: "alumno" }) })

  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<{
    alumno_id: string; grupo_id: string; ciclo_escolar_id: string
  }>()

  const create = useMutation({ mutationFn: createInscripcion, onSuccess: () => { qc.invalidateQueries({ queryKey: ["inscripciones"] }); setOpen(false); reset() } })
  const remove = useMutation({ mutationFn: deleteInscripcion, onSuccess: () => qc.invalidateQueries({ queryKey: ["inscripciones"] }) })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-xl font-bold">Inscripciones</h2>
        <div className="flex gap-2">
          <select
            className="h-9 rounded-md border border-gray-300 px-3 text-sm"
            value={cicloFilter}
            onChange={(e) => setCicloFilter(e.target.value)}
          >
            <option value="">Todos los ciclos</option>
            {ciclos.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Inscribir</Button>
        </div>
      </div>

      <Card><CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{["Alumno", "Matrícula", "Grupo", "Ciclo", "Fecha", "Estado", ""].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? <tr><td colSpan={7} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                : inscripciones.map(i => (
                  <tr key={i.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{i.alumno_nombre}</td>
                    <td className="px-4 py-3">{i.matricula ?? "—"}</td>
                    <td className="px-4 py-3">{i.grupo_nombre}</td>
                    <td className="px-4 py-3">{i.ciclo_nombre}</td>
                    <td className="px-4 py-3">{i.fecha_inscripcion}</td>
                    <td className="px-4 py-3"><Badge variant={i.activa ? "success" : "secondary"}>{i.activa ? "Activa" : "Baja"}</Badge></td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="icon-sm" onClick={() => remove.mutate(i.id)}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </CardContent></Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nueva inscripción</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit((data) => create.mutate(data))} className="space-y-4">
            <div><label className="block text-sm font-medium mb-1">Alumno</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("alumno_id")}>
                <option value="">Seleccionar alumno...</option>
                {alumnos.map(a => <option key={a.id} value={a.id}>{a.nombre} {a.apellido_paterno}</option>)}
              </select>
            </div>
            <div><label className="block text-sm font-medium mb-1">Ciclo escolar</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("ciclo_escolar_id")}>
                <option value="">Seleccionar ciclo...</option>
                {ciclos.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              </select>
            </div>
            <div><label className="block text-sm font-medium mb-1">Grupo</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("grupo_id")}>
                <option value="">Seleccionar grupo...</option>
                {grupos.map(g => <option key={g.id} value={g.id}>{g.nombre}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button type="submit" loading={isSubmitting}>Inscribir</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
