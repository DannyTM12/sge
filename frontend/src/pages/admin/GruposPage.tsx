import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { getCiclos, getGrupos, createGrupo, updateGrupo, deleteGrupo } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Badge } from "@/components/ui/Badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog"
import type { Grupo } from "@/types"

const schema = z.object({
  nombre: z.string().min(1, "Requerido"),
  ciclo_escolar_id: z.string().min(1, "Requerido"),
  turno: z.enum(["matutino", "vespertino", "mixto"]),
  capacidad_maxima: z.coerce.number().int().min(1),
  activo: z.boolean(),
})
type FormData = z.infer<typeof schema>

export function GruposPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<Grupo | null>(null)
  const [open, setOpen] = useState(false)

  const { data: grupos = [], isLoading } = useQuery({ queryKey: ["grupos"], queryFn: () => getGrupos() })
  const { data: ciclos = [] } = useQuery({ queryKey: ["ciclos"], queryFn: getCiclos })

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema) as never,
    defaultValues: { turno: "matutino", capacidad_maxima: 30, activo: true },
  })

  const create = useMutation({ mutationFn: createGrupo, onSuccess: () => { qc.invalidateQueries({ queryKey: ["grupos"] }); close() } })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Grupo> }) => updateGrupo(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["grupos"] }); close() },
  })
  const remove = useMutation({ mutationFn: deleteGrupo, onSuccess: () => qc.invalidateQueries({ queryKey: ["grupos"] }) })

  const openCreate = () => { reset({ turno: "matutino", capacidad_maxima: 30, activo: true }); setEditing(null); setOpen(true) }
  const openEdit = (g: Grupo) => {
    reset({ nombre: g.nombre, ciclo_escolar_id: g.ciclo_escolar_id, turno: g.turno, capacidad_maxima: g.capacidad_maxima, activo: g.activo })
    setEditing(g); setOpen(true)
  }
  const close = () => { setOpen(false); setEditing(null) }

  const onSubmit = (data: FormData) => {
    if (editing) update.mutate({ id: editing.id, body: data })
    else create.mutate(data as Omit<Grupo, "id">)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Grupos</h2>
        <Button size="sm" onClick={openCreate}><Plus className="h-4 w-4" /> Nuevo grupo</Button>
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>{["Nombre", "Ciclo", "Turno", "Cap.", "Estado", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y">
                {isLoading ? (
                  <tr><td colSpan={6} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                ) : grupos.map(g => (
                  <tr key={g.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{g.nombre}</td>
                    <td className="px-4 py-3">{g.ciclo_nombre ?? g.ciclo_escolar_id}</td>
                    <td className="px-4 py-3 capitalize">{g.turno}</td>
                    <td className="px-4 py-3">{g.capacidad_maxima}</td>
                    <td className="px-4 py-3"><Badge variant={g.activo ? "success" : "secondary"}>{g.activo ? "Activo" : "Inactivo"}</Badge></td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon-sm" onClick={() => openEdit(g)}><Pencil className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon-sm" onClick={() => remove.mutate(g.id)}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar grupo" : "Nuevo grupo"}</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-1">Nombre</label><Input placeholder="1A" error={errors.nombre?.message} {...register("nombre")} /></div>
            <div>
              <label className="block text-sm font-medium mb-1">Ciclo escolar</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("ciclo_escolar_id")}>
                <option value="">Seleccionar...</option>
                {ciclos.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              </select>
            </div>
            <div><label className="block text-sm font-medium mb-1">Turno</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("turno")}>
                <option value="matutino">Matutino</option>
                <option value="vespertino">Vespertino</option>
                <option value="mixto">Mixto</option>
              </select>
            </div>
            <div><label className="block text-sm font-medium mb-1">Capacidad máxima</label><Input type="number" {...register("capacidad_maxima")} /></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...register("activo")} /> Grupo activo</label>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={close}>Cancelar</Button>
              <Button type="submit" loading={isSubmitting}>Guardar</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
