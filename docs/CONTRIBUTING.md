# Estrategia de branching — SGE

## Ramas principales

| Rama | Propósito |
|------|-----------|
| `main` | Siempre deployable. Solo código con tests pasando. |

## Nomenclatura de ramas de trabajo

| Prefijo | Cuándo usarlo | Ejemplo |
|---------|--------------|---------|
| `fase/` | Implementación de una fase completa del roadmap | `fase/5-alumnos` |
| `feat/` | Feature nuevo dentro de una fase | `feat/boleta-pdf` |
| `fix/` | Corrección de bug | `fix/tenant-isolation-admin` |
| `chore/` | Mantenimiento sin cambio funcional | `chore/actualizar-dependencias` |

## Flujo de trabajo

```bash
# 1. Crear rama desde main actualizado
git checkout main && git pull
git checkout -b fase/5-alumnos

# 2. Trabajar y commitear con mensajes descriptivos
git add .
git commit -m "feat(alumnos): endpoint calificaciones con historial por ciclo"

# 3. Cuando la sesión de Claude Code termina y los tests pasan
git push origin fase/5-alumnos
gh pr create --title "Fase 5: router /alumnos completo" --body "45 → 58 tests pasando"

# 4. Merge a main
gh pr merge --squash
```

## Convención de commits

Formato: `tipo(scope): descripción corta`

| Tipo | Cuándo |
|------|--------|
| `feat` | Nuevo endpoint, componente o feature |
| `fix` | Corrección de bug |
| `test` | Agregar o corregir tests |
| `chore` | Dependencias, config, CI |
| `docs` | Documentación |

## Versionado del modelo de IA

Los archivos `.pkl` no se guardan en git. Nomenclatura del campo `modelo_version`:

```
sge_v{MAJOR}.{MINOR}.{FECHA}
# Ejemplo: sge_v1.0.20260416
```

- **MAJOR**: cambia cuando se modifican los features del modelo (incompatible hacia atrás)
- **MINOR**: cambia cuando se reentrena con más datos (mismos features)
- **FECHA**: siempre presente en formato YYYYMMDD
