import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useNavigate, Link } from "react-router-dom"
import { useAuthStore } from "@/stores/authStore"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"

const schema = z.object({
  email: z.string().email("Correo inválido"),
  password: z.string().min(1, "La contraseña es requerida"),
})
type FormData = z.infer<typeof schema>

const ROLE_HOME: Record<string, string> = {
  superadmin: "/admin",
  admin: "/admin",
  profesor: "/profesor",
  alumno: "/alumno",
}

export function LoginPage() {
  const { login, isAuthenticated, isHydrating, user } = useAuthStore()
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (!isHydrating && isAuthenticated && user) {
      navigate(ROLE_HOME[user.rol] ?? "/", { replace: true })
    }
  }, [isHydrating, isAuthenticated, user, navigate])

  const onSubmit = async (data: FormData) => {
    try {
      await login(data.email, data.password)
    } catch {
      setError("root", { message: "Credenciales incorrectas" })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white font-bold text-xl">
            S
          </div>
          <CardTitle>Iniciar sesión</CardTitle>
          <p className="text-sm text-gray-500">Sistema de Gestión Escolar</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Correo electrónico
              </label>
              <Input
                type="email"
                placeholder="usuario@escuela.edu"
                autoComplete="email"
                error={errors.email?.message}
                {...register("email")}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <Input
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                error={errors.password?.message}
                {...register("password")}
              />
            </div>

            {errors.root && (
              <p className="text-sm text-red-500 text-center">{errors.root.message}</p>
            )}

            <Button type="submit" className="w-full" loading={isSubmitting}>
              Entrar
            </Button>

            <p className="text-center text-xs text-gray-500">
              <Link to="/recuperar-password" className="text-primary hover:underline">
                ¿Olvidaste tu contraseña?
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
