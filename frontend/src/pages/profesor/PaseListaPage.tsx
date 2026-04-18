import { useCallback, useEffect, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, Clock, X, AlertTriangle, Save } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  getAlumnosGrupo,
  getSesiones,
  crearSesion,
  getAsistenciasSesion,
  registrarAsistencias,
  actualizarAsistencia,
} from "@/api/profesor"
import type { AsistenciaRegistro, SesionClase } from "@/types"
import { Button } from "@/components/ui/Button"
import { Spinner } from "@/components/ui/Spinner"

type Estado = "presente" | "ausente" | "tardanza" | "justificada"

interface EstadoBtn {
  estado: Estado
  label: string
  icon: React.ComponentType<{ className?: string }>
  activeClass: string
}

const ESTADOS: EstadoBtn[] = [
  { estado: "presente", label: "P", icon: Check, activeClass: "bg-green-500 text-white border-green-500" },
  { estado: "tardanza", label: "T", icon: Clock, activeClass: "bg-yellow-500 text-white border-yellow-500" },
  { estado: "ausente", label: "A", icon: X, activeClass: "bg-red-500 text-white border-red-500" },
  { estado: "justificada", label: "J", icon: AlertTriangle, activeClass: "bg-blue-500 text-white border-blue-500" },
]

export function PaseListaPage() {
  const { grupoId } = useParams<{ grupoId: string }>()
  const qc = useQueryClient()

  const [sesionId, setSesionId] = useState<string | null>(null)
  const [estados, setEstados] = useState<Record<string, Estado>>({})
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: alumnos = [], isLoading: loadingAlumnos } = useQuery({
    queryKey: ["alumnos-grupo", grupoId],
    queryFn: () => getAlumnosGrupo(grupoId!),
    enabled: !!grupoId,
  })

  const { data: sesiones = [] } = useQuery({
    queryKey: ["sesiones", grupoId],
    queryFn: () => getSesiones(grupoId!),
    enabled: !!grupoId,
  })

  const { data: asistencias = [] } = useQuery({
    queryKey: ["asistencias-sesion", sesionId],
    queryFn: () => getAsistenciasSesion(sesionId!),
    enabled: !!sesionId,
  })

  // Initialize states from existing asistencias
  useEffect(() => {
    if (asistencias.length > 0) {
      const map: Record<string, Estado> = {}
      asistencias.forEach((a: AsistenciaRegistro) => { map[a.alumno_id] = a.estado })
      setEstados(map)
      setDirty(new Set())
    }
  }, [asistencias])

  // Default all alumnos to "presente" when sesion is created fresh
  useEffect(() => {
    if (sesionId && asistencias.length === 0 && alumnos.length > 0) {
      const map: Record<string, Estado> = {}
      alumnos.forEach(a => { map[a.alumno_id] = "presente" })
      setEstados(map)
      setDirty(new Set(alumnos.map(a => a.alumno_id)))
    }
  }, [sesionId, alumnos, asistencias.length])

  const crearSesionMutation = useMutation({
    mutationFn: crearSesion,
    onSuccess: (s: SesionClase) => {
      setSesionId(s.id)
      qc.invalidateQueries({ queryKey: ["sesiones", grupoId] })
    },
  })

  const iniciarSesion = () => {
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, "0")
    crearSesionMutation.mutate({
      grupo_materia_id: grupoId!,
      fecha: now.toISOString().split("T")[0],
      hora_inicio: `${pad(now.getHours())}:${pad(now.getMinutes())}:00`,
      hora_fin: `${pad(now.getHours() + 1)}:${pad(now.getMinutes())}:00`,
    })
  }

  const toggleEstado = useCallback((alumnoId: string, estado: Estado) => {
    setEstados(prev => ({ ...prev, [alumnoId]: estado }))
    setDirty(prev => new Set(prev).add(alumnoId))
    setSaved(false)

    // Debounced auto-save after 2s of inactivity
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => autoSave(alumnoId, estado), 2000)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionId])

  const autoSave = async (alumnoId: string, estado: Estado) => {
    if (!sesionId) return
    try {
      await actualizarAsistencia(sesionId, alumnoId, estado)
      setDirty(prev => { const next = new Set(prev); next.delete(alumnoId); return next })
    } catch { /* retry on manual save */ }
  }

  const guardarTodo = async () => {
    if (!sesionId) return
    setSaving(true)
    const toSave = Array.from(dirty).map(alumnoId => ({
      alumno_id: alumnoId,
      estado: estados[alumnoId] ?? "presente",
    }))
    try {
      if (asistencias.length === 0) {
        // First save — bulk register
        await registrarAsistencias(sesionId, Object.entries(estados).map(([alumno_id, estado]) => ({ alumno_id, estado })))
      } else {
        // Incremental update
        await Promise.all(toSave.map(({ alumno_id, estado }) => actualizarAsistencia(sesionId, alumno_id, estado)))
      }
      setDirty(new Set())
      setSaved(true)
      qc.invalidateQueries({ queryKey: ["asistencias-sesion", sesionId] })
    } finally {
      setSaving(false)
    }
  }

  if (loadingAlumnos) return <div className="flex justify-center pt-20"><Spinner /></div>

  // No session yet
  if (!sesionId) {
    const today = new Date().toLocaleDateString("es-MX", { weekday: "long", year: "numeric", month: "long", day: "numeric" })
    return (
      <div className="max-w-md mx-auto space-y-6 py-8 px-4">
        <div>
          <h2 className="text-xl font-bold">Pase de lista</h2>
          <p className="text-sm text-gray-500 capitalize">{today}</p>
        </div>
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            {sesiones.length > 0
              ? `Sesiones anteriores: ${sesiones.length}`
              : "No hay sesiones registradas hoy."}
          </p>
          <Button
            className="w-full h-14 text-base"
            onClick={iniciarSesion}
            loading={crearSesionMutation.isPending}
          >
            Iniciar nueva sesión
          </Button>
          {sesiones.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-500 uppercase">Sesiones anteriores</p>
              {sesiones.slice(0, 5).map(s => (
                <button
                  key={s.id}
                  onClick={() => setSesionId(s.id)}
                  className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-primary hover:bg-primary-50 text-sm"
                >
                  {s.fecha} — {s.hora_inicio}
                  {s.tema && <span className="text-gray-500 ml-1">· {s.tema}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  const ausentes = Object.values(estados).filter(e => e === "ausente").length
  const tardanzas = Object.values(estados).filter(e => e === "tardanza").length

  return (
    <div className="max-w-2xl mx-auto">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h2 className="font-bold text-gray-900 text-sm">Pase de lista</h2>
          <p className="text-xs text-gray-500">
            {alumnos.length} alumnos · {ausentes} ausentes · {tardanzas} tardanzas
          </p>
        </div>
        <Button
          size="sm"
          onClick={guardarTodo}
          loading={saving}
          disabled={dirty.size === 0}
          className={cn(saved && dirty.size === 0 && "bg-green-600 hover:bg-green-700")}
        >
          <Save className="h-4 w-4" />
          {saved && dirty.size === 0 ? "Guardado" : dirty.size > 0 ? `Guardar (${dirty.size})` : "Guardado"}
        </Button>
      </div>

      {/* Alumno list — touch-friendly */}
      <div className="divide-y divide-gray-100">
        {alumnos.map(alumno => {
          const estado = estados[alumno.alumno_id] ?? "presente"
          return (
            <div
              key={alumno.alumno_id}
              className={cn(
                "flex items-center justify-between px-4 py-3 transition-colors",
                dirty.has(alumno.alumno_id) && "bg-yellow-50",
              )}
            >
              <div className="min-w-0 flex-1 pr-3">
                <p className="font-medium text-gray-900 text-sm truncate">{alumno.nombre_completo}</p>
                {alumno.matricula && (
                  <p className="text-xs text-gray-500">{alumno.matricula}</p>
                )}
              </div>

              {/* Estado buttons — 64px min tap target */}
              <div className="flex gap-1.5" style={{ touchAction: "manipulation" }}>
                {ESTADOS.map(btn => (
                  <button
                    key={btn.estado}
                    onClick={() => toggleEstado(alumno.alumno_id, btn.estado)}
                    className={cn(
                      "flex items-center justify-center rounded-lg border-2 font-bold text-sm transition-all select-none",
                      "w-11 h-11 md:w-9 md:h-9",
                      estado === btn.estado
                        ? btn.activeClass
                        : "border-gray-200 text-gray-400 hover:border-gray-400",
                    )}
                    aria-label={btn.estado}
                    aria-pressed={estado === btn.estado}
                  >
                    {btn.label}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {alumnos.length === 0 && (
        <p className="text-center text-gray-400 py-12 text-sm">No hay alumnos en este grupo.</p>
      )}

      {/* Bottom save button for easy mobile reach */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 px-4 py-3">
        <Button
          className="w-full h-12"
          onClick={guardarTodo}
          loading={saving}
          disabled={dirty.size === 0}
        >
          <Save className="h-5 w-5" />
          {dirty.size > 0 ? `Guardar ${dirty.size} cambio${dirty.size > 1 ? "s" : ""}` : "Todo guardado"}
        </Button>
      </div>
    </div>
  )
}
