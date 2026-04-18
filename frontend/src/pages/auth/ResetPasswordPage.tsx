import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Link, useSearchParams, useNavigate } from "react-router-dom"
import { useState } from "react"
import apiClient from "@/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"

const schema = z
  .object({
    password: z.string().min(8, "Mínimo 8 caracteres"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Las contraseñas no coinciden",
    path: ["confirm"],
  })
type FormData = z.infer<typeof schema>

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const token = params.get("token") ?? ""

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    try {
      await apiClient.post("/auth/reset-password", {
        token,
        new_password: data.password,
      })
      navigate("/login")
    } catch {
      setError("El enlace es inválido o ha expirado.")
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500">Token inválido. <Link to="/recuperar-password" className="underline">Solicita uno nuevo.</Link></p>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Nueva contraseña</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              type="password"
              placeholder="Nueva contraseña"
              error={errors.password?.message}
              {...register("password")}
            />
            <Input
              type="password"
              placeholder="Confirmar contraseña"
              error={errors.confirm?.message}
              {...register("confirm")}
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" loading={isSubmitting}>
              Guardar contraseña
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
