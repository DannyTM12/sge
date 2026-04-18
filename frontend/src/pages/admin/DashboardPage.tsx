import { useQuery } from "@tanstack/react-query"
import { Users, BookOpen, Bell, AlertTriangle } from "lucide-react"
import { getAdminDashboard } from "@/api/admin"
import { Card, CardContent } from "@/components/ui/Card"
import { Spinner } from "@/components/ui/Spinner"

interface KpiCardProps {
  title: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  color: string
}

function KpiCard({ title, value, icon: Icon, color }: KpiCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className={`flex h-12 w-12 items-center justify-center rounded-full ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}

export function AdminDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: getAdminDashboard,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center pt-20">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
        {data?.ciclo_activo && (
          <p className="text-sm text-gray-500">Ciclo activo: {data.ciclo_activo.nombre}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Alumnos"
          value={data?.total_alumnos ?? 0}
          icon={Users}
          color="bg-primary"
        />
        <KpiCard
          title="Profesores"
          value={data?.total_profesores ?? 0}
          icon={Users}
          color="bg-accent"
        />
        <KpiCard
          title="Grupos activos"
          value={data?.grupos_activos ?? 0}
          icon={BookOpen}
          color="bg-green-600"
        />
        <KpiCard
          title="Alertas IA"
          value={data?.alertas_no_leidas ?? 0}
          icon={Bell}
          color="bg-red-500"
        />
      </div>

      {(data?.materias_en_riesgo ?? 0) > 0 && (
        <Card className="border-yellow-300 bg-yellow-50">
          <CardContent className="flex items-center gap-3 pt-4">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <p className="text-sm text-yellow-800">
              Hay <strong>{data!.materias_en_riesgo}</strong> materias con alumnos en riesgo de reprobación.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
