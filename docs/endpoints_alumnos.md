# Referencia de endpoints — /alumnos

> Todos requieren `Authorization: Bearer <token>` con rol `alumno`.
> `alumno_id` nunca es parámetro — siempre se deriva del token.

---

## Dashboard

### `GET /alumnos/dashboard`
Pantalla home del alumno. Una sola llamada devuelve todo lo necesario.

**Response** `200 DashboardAlumnoRead`
```json
{
  "nombre_completo": "María López García",
  "matricula": "2026001",
  "grupo_nombre": "1A",
  "ciclo_nombre": "2026-1",
  "ciclo_id": "uuid",
  "promedio_general": "8.50",
  "materias_en_riesgo": 1,
  "alertas_no_leidas": 3,
  "materias": [ /* lista MiMateriaRead */ ]
}
```

> Si no hay inscripción activa devuelve 200 con `grupo_nombre=null`, `materias=[]`.

---

## Calificaciones

### `GET /alumnos/calificaciones`
Calificaciones del ciclo activo. Parciales no cerrados devuelven `calificacion=null, esta_publicada=false`.

**Response** `200 list[MiMateriaRead]`
```json
[{
  "materia_id": "uuid",
  "materia_nombre": "Matemáticas",
  "clave": "MAT101",
  "profesor_nombre": "Juan García",
  "num_parciales": 3,
  "parciales": [
    { "parcial_numero": 1, "parcial_nombre": "Parcial 1", "calificacion": "9.0", "fecha_registro": "...", "esta_publicada": true },
    { "parcial_numero": 2, "parcial_nombre": "Parcial 2", "calificacion": null, "fecha_registro": null, "esta_publicada": false }
  ],
  "calificacion_calculada": "9.00",
  "calificacion_final": "9.00",
  "fue_modificada_manualmente": false
}]
```

### `GET /alumnos/calificaciones/historial`
Historial por ciclo, descendente. Solo ciclos cerrados o con calificaciones finales.

**Response** `200 list[HistorialCicloRead]`
```json
[{
  "ciclo_id": "uuid",
  "ciclo_nombre": "2025-2",
  "ciclo_tipo": "semestral",
  "fecha_inicio": "2025-08-01",
  "fecha_fin": "2025-12-31",
  "materias": [ /* MiMateriaRead */ ],
  "promedio_ciclo": "8.75"
}]
```

---

## Asistencias

### `GET /alumnos/asistencias`
Listado del ciclo activo, por fecha desc.

**Query params:** `limit` (max 500, default 100), `offset`

**Response** `200 list[MiAsistenciaRead]`
```json
[{
  "sesion_fecha": "2026-04-10",
  "sesion_hora_inicio": "08:00:00",
  "materia_nombre": "Matemáticas",
  "estado": "presente",
  "justificante_descripcion": null
}]
```

### `GET /alumnos/asistencias/resumen`
Agrupado por materia, ordenado por porcentaje ASC (primero donde más falta).

**Response** `200 list[ResumenAsistenciaRead]`
```json
[{
  "materia_id": "uuid",
  "materia_nombre": "Física",
  "total_sesiones": 20,
  "presentes": 14,
  "ausentes": 4,
  "tardanzas": 1,
  "justificadas": 1,
  "porcentaje_asistencia": 0.8
}]
```

> `porcentaje_asistencia = (presentes + tardanzas + justificadas) / total_sesiones`.
> Si `total_sesiones = 0` → `null` (no `0.0`).

---

## Horario

### `GET /alumnos/horario`
Horario del grupo activo, ordenado por día (lunes…sábado) y hora.

**Response** `200 list[MiHorarioRead]`
```json
[{
  "dia_semana": "lunes",
  "hora_inicio": "08:00:00",
  "hora_fin": "09:30:00",
  "materia_nombre": "Matemáticas",
  "profesor_nombre": "Juan García",
  "aula": "Aula 3"
}]
```

---

## Notas

### `GET /alumnos/notas`
Solo notas con `es_visible_alumno=true`, más recientes primero.

**Query params:** `limit` (max 200, default 50), `offset`

**Response** `200 list[MiNotaRead]`
```json
[{
  "contenido": "Excelente participación en clase.",
  "autor_nombre_completo": "Profr. García",
  "created_at": "2026-04-10T10:00:00Z"
}]
```

---

## Notificaciones

### `GET /alumnos/notificaciones`
Paginada, más recientes primero.

**Query params:** `solo_no_leidas` (bool, default false), `limit` (max 200, default 50), `offset`

**Response** `200 list[NotificacionRead]`
```json
[{
  "id": "uuid",
  "titulo": "Nueva calificación",
  "mensaje": "Se publicó el Parcial 1 de Matemáticas.",
  "tipo": "info",
  "leida": false,
  "created_at": "2026-04-10T10:00:00Z"
}]
```

### `GET /alumnos/notificaciones/no-leidas`
Optimizado para polling (badge). Objetivo < 50ms.

**Response** `200`
```json
{ "count": 3 }
```

### `PATCH /alumnos/notificaciones/{id}/leer`
Marca una notificación como leída. 404 si no existe o es ajena (anti-enumeration).

**Response** `200 NotificacionRead` con `leida=true`

### `PATCH /alumnos/notificaciones/marcar-todas-leidas`
Marca todas las no leídas del alumno.

**Response** `200`
```json
{ "actualizadas": 5 }
```

---

## Boleta PDF

### `GET /alumnos/boleta`
Boleta del ciclo activo.

### `GET /alumnos/boleta/{ciclo_id}`
Boleta de un ciclo del historial.

**Rate limit:** 10 descargas/hora por alumno. La 11ª recibe `429`.

**Errores:**
- `404` — sin inscripción activa en ese ciclo
- `422` — ningún parcial cerrado aún (`"No hay calificaciones publicadas aún"`)
- `429` — rate limit excedido

**Response** `200 application/pdf`
```
Content-Disposition: attachment; filename="boleta_2026001_2026-1.pdf"
```

**Auditoría:** Se registra en `auditoria` con `accion='descarga_boleta'`, `tabla_afectada='calificaciones_finales'`, `valor_nuevo={"folio": "uuid", "ciclo_escolar_id": "uuid"}`.

---

## Notas de diseño

| Regla | Detalle |
|-------|---------|
| `alumno_id` | Siempre del token JWT, nunca por parámetro |
| Visibilidad parciales | `calificacion=null` si `fecha_cierre > now()` o es `null` |
| Anti-enumeration | Recursos ajenos devuelven `404`, nunca `403` |
| CURP en boleta | Nunca incluida (LFPDPPP) |
| Logs | Solo `alumno_id` (UUID), nunca nombre completo, CURP ni email tutor |
