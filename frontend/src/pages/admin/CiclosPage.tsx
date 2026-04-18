import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { getCiclos, createCiclo, updateCiclo, deleteCiclo } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Badge } from "@/components/ui/Badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog"
import type { CicloEscolar } from "@/types"

const schema = z.object({
  nombre: z.string().min(1, "Requerido"),
  tipo: z.enum(["semestral", "cuatrimestral"]),
  fecha_inicio: z.string().min(1, "Requerido"),
  fecha_fin: z.string().min(1, "Requerido"),
  activo: z.boolean(),
})
type FormData = z.infer<typeof schema>

export function CiclosPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<CicloEscolar | null>(null)
  const [open, setOpen] = useState(false)

  const { data: ciclos = [], isLoading } = useQuery({
    queryKey: ["ciclos"],
    queryFn: getCiclos,
  })

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { tipo: "semestral", activo: true },
  })

  const create = useMutation({
    mutationFn: createCiclo,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ciclos"] }); close() },
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<CicloEscolar> }) =>
      updateCiclo(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ciclos"] }); close() },
  })

  const remove = useMutation({
    mutationFn: deleteCiclo,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ciclos"] }),
  })

  const openCreate = () => { reset({ tipo: "semestral", activo: true }); setEditing(null); setOpen(true) }
  const openEdit = (c: CicloEscolar) => {
    reset({ nombre: c.nombre, tipo: c.tipo, fecha_inicio: c.fecha_inicio, fecha_fin: c.fecha_fin, activo: c.activo })
    setEditing(c)
    setOpen(true)
  }
  const close = () => { setOpen(false); setEditing(null) }

  const onSubmit = (data: FormData) => {
    if (editing) update.mutate({ id: editing.id, body: data })
    else create.mutate(data as Omit<CicloEscolar, "id" | "created_at">)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Ciclos escolares</h2>
        <Button size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4" /> Nuevo ciclo
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {["Nombre", "Tipo", "Inicio", "Fin", "Estado", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {isLoading ? (
                  <tr><td colSpan={6} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                ) : ciclos.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{c.nombre}</td>
                    <td className="px-4 py-3 capitalize">{c.tipo}</td>
                    <td className="px-4 py-3">{c.fecha_inicio}</td>
                    <td className="px-4 py-3">{c.fecha_fin}</td>
                    <td className="px-4 py-3">
                      <Badge variant={c.activo ? "success" : "secondary"}>
                        {c.activo ? "Activo" : "Cerrado"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon-sm" onClick={() => openEdit(c)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => remove.mutate(c.id)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
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
          <DialogHeader>
            <DialogTitle>{editing ? "Editar ciclo" : "Nuevo ciclo"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nombre</label>
              <Input placeholder="2026-1" error={errors.nombre?.message} {...register("nombre")} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Tipo</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("tipo")}>
                <option value="semestral">Semestral</option>
                <option value="cuatrimestral">Cuatrimestral</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">Fecha inicio</label>
                <Input type="date" error={errors.fecha_inicio?.message} {...register("fecha_inicio")} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Fecha fin</label>
                <Input type="date" error={errors.fecha_fin?.message} {...register("fecha_fin")} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("activo")} />
              Ciclo activo
            </label>
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
