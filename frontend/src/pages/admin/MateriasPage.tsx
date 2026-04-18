import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { getMaterias, createMateria, updateMateria, deleteMateria } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Badge } from "@/components/ui/Badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog"
import type { Materia } from "@/types"

const schema = z.object({
  nombre: z.string().min(1),
  clave: z.string().nullable().optional(),
  creditos: z.coerce.number().int().min(0).nullable().optional(),
  activa: z.boolean(),
})
type FormData = z.infer<typeof schema>

export function MateriasPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<Materia | null>(null)
  const [open, setOpen] = useState(false)

  const { data: materias = [], isLoading } = useQuery({ queryKey: ["materias"], queryFn: getMaterias })
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema) as never,
    defaultValues: { activa: true },
  })

  const create = useMutation({ mutationFn: createMateria, onSuccess: () => { qc.invalidateQueries({ queryKey: ["materias"] }); close() } })
  const update = useMutation({ mutationFn: ({ id, body }: { id: string; body: Partial<Materia> }) => updateMateria(id, body), onSuccess: () => { qc.invalidateQueries({ queryKey: ["materias"] }); close() } })
  const remove = useMutation({ mutationFn: deleteMateria, onSuccess: () => qc.invalidateQueries({ queryKey: ["materias"] }) })

  const openCreate = () => { reset({ activa: true }); setEditing(null); setOpen(true) }
  const openEdit = (m: Materia) => { reset({ nombre: m.nombre, clave: m.clave, creditos: m.creditos, activa: m.activa }); setEditing(m); setOpen(true) }
  const close = () => { setOpen(false); setEditing(null) }

  const onSubmit = (data: FormData) => {
    if (editing) update.mutate({ id: editing.id, body: data })
    else create.mutate(data as Omit<Materia, "id">)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Materias</h2>
        <Button size="sm" onClick={openCreate}><Plus className="h-4 w-4" /> Nueva materia</Button>
      </div>
      <Card><CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{["Nombre", "Clave", "Créditos", "Estado", ""].map(h => <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                : materias.map(m => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{m.nombre}</td>
                    <td className="px-4 py-3">{m.clave ?? "—"}</td>
                    <td className="px-4 py-3">{m.creditos ?? "—"}</td>
                    <td className="px-4 py-3"><Badge variant={m.activa ? "success" : "secondary"}>{m.activa ? "Activa" : "Inactiva"}</Badge></td>
                    <td className="px-4 py-3"><div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(m)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => remove.mutate(m.id)}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                    </div></td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </CardContent></Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar materia" : "Nueva materia"}</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-1">Nombre</label><Input placeholder="Matemáticas" error={errors.nombre?.message} {...register("nombre")} /></div>
            <div><label className="block text-sm font-medium mb-1">Clave</label><Input placeholder="MAT101" {...register("clave")} /></div>
            <div><label className="block text-sm font-medium mb-1">Créditos</label><Input type="number" {...register("creditos")} /></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...register("activa")} /> Materia activa</label>
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
