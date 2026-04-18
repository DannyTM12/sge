import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { getUsuarios, createUsuario, updateUsuario, deleteUsuario } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Badge } from "@/components/ui/Badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog"
import type { Usuario } from "@/types"

const createSchema = z.object({
  nombre: z.string().min(1),
  apellido_paterno: z.string().min(1),
  apellido_materno: z.string().optional(),
  email: z.string().email(),
  password: z.string().min(8),
  rol: z.enum(["admin", "profesor", "alumno"]),
  activo: z.boolean(),
})
const editSchema = createSchema.omit({ password: true }).extend({ password: z.string().optional() })

type CreateFormData = z.infer<typeof createSchema>

export function UsuariosPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<Usuario | null>(null)
  const [open, setOpen] = useState(false)

  const { data: usuarios = [], isLoading } = useQuery({ queryKey: ["usuarios"], queryFn: () => getUsuarios() })
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<CreateFormData>({
    resolver: zodResolver(editing ? editSchema : createSchema) as never,
    defaultValues: { rol: "alumno", activo: true },
  })

  const create = useMutation({ mutationFn: createUsuario, onSuccess: () => { qc.invalidateQueries({ queryKey: ["usuarios"] }); close() } })
  const update = useMutation({ mutationFn: ({ id, body }: { id: string; body: Partial<Usuario> }) => updateUsuario(id, body), onSuccess: () => { qc.invalidateQueries({ queryKey: ["usuarios"] }); close() } })
  const remove = useMutation({ mutationFn: deleteUsuario, onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }) })

  const openCreate = () => { reset({ rol: "alumno", activo: true }); setEditing(null); setOpen(true) }
  const openEdit = (u: Usuario) => { reset({ nombre: u.nombre, apellido_paterno: u.apellido_paterno, apellido_materno: u.apellido_materno, email: u.email, rol: u.rol as "admin" | "profesor" | "alumno", activo: u.activo }); setEditing(u); setOpen(true) }
  const close = () => { setOpen(false); setEditing(null) }

  const onSubmit = (data: CreateFormData) => {
    if (editing) update.mutate({ id: editing.id, body: data as Partial<Usuario> })
    else create.mutate(data)
  }

  const ROL_VARIANT: Record<string, "default" | "accent" | "secondary" | "warning"> = {
    admin: "default", profesor: "accent", alumno: "secondary", superadmin: "warning",
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Usuarios</h2>
        <Button size="sm" onClick={openCreate}><Plus className="h-4 w-4" /> Nuevo usuario</Button>
      </div>
      <Card><CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{["Nombre", "Email", "Rol", "Estado", ""].map(h => <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">Cargando...</td></tr>
                : usuarios.map(u => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{u.nombre} {u.apellido_paterno}</td>
                    <td className="px-4 py-3">{u.email}</td>
                    <td className="px-4 py-3"><Badge variant={ROL_VARIANT[u.rol] ?? "secondary"}>{u.rol}</Badge></td>
                    <td className="px-4 py-3"><Badge variant={u.activo ? "success" : "secondary"}>{u.activo ? "Activo" : "Inactivo"}</Badge></td>
                    <td className="px-4 py-3"><div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(u)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => remove.mutate(u.id)}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                    </div></td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </CardContent></Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar usuario" : "Nuevo usuario"}</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><label className="block text-sm font-medium mb-1">Nombre</label><Input error={errors.nombre?.message} {...register("nombre")} /></div>
              <div><label className="block text-sm font-medium mb-1">Ap. paterno</label><Input error={errors.apellido_paterno?.message} {...register("apellido_paterno")} /></div>
            </div>
            <div><label className="block text-sm font-medium mb-1">Ap. materno</label><Input {...register("apellido_materno")} /></div>
            <div><label className="block text-sm font-medium mb-1">Email</label><Input type="email" error={errors.email?.message} {...register("email")} /></div>
            <div><label className="block text-sm font-medium mb-1">Contraseña {editing && "(dejar vacío para no cambiar)"}</label><Input type="password" error={errors.password?.message} {...register("password")} /></div>
            <div><label className="block text-sm font-medium mb-1">Rol</label>
              <select className="w-full h-10 rounded-md border border-gray-300 px-3 text-sm" {...register("rol")}>
                <option value="alumno">Alumno</option>
                <option value="profesor">Profesor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...register("activo")} /> Usuario activo</label>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={close}>Cancelar</Button>
              <Button type="submit" loading={isSubmitting}>Guardar</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
