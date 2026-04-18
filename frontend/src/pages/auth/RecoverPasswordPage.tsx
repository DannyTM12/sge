import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Link } from "react-router-dom"
import { useState } from "react"
import apiClient from "@/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"

const schema = z.object({ email: z.string().email("Correo inválido") })
type FormData = z.infer<typeof schema>

export function RecoverPasswordPage() {
  const [sent, setSent] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    await apiClient.post("/auth/forgot-password", { email: data.email })
    setSent(true)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Recuperar contraseña</CardTitle>
          <p className="text-sm text-gray-500">
            Ingresa tu correo y te enviaremos un enlace para restablecer tu contraseña.
          </p>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="text-center space-y-3">
              <p className="text-sm text-green-700 bg-green-50 rounded-lg p-3">
                Si el correo existe en el sistema, recibirás un enlace en breve.
              </p>
              <Link to="/login" className="text-sm text-primary hover:underline">
                Volver al inicio
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Correo electrónico
                </label>
                <Input
                  type="email"
                  placeholder="usuario@escuela.edu"
                  error={errors.email?.message}
                  {...register("email")}
                />
              </div>
              <Button type="submit" className="w-full" loading={isSubmitting}>
                Enviar enlace
              </Button>
              <p className="text-center text-xs">
                <Link to="/login" className="text-primary hover:underline">
                  Volver al inicio
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
