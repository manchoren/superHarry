# Plan de Release Acceptance — T179 (OpenRouter free-provider routing)

**Estado actual:** 22/22 pruebas síncronas pasan. Código desplegado. Servicios activos. DB migrado. Lo que falta es completar los criterios de release acceptance (gates de verificación y criterios no-código).

**VM objetivo:** `superharry-dev` (QEMU PID 33204, Debian 13.7 ARM64, SSH en 127.0.0.1:2222)

---
## 1. Criterios de release acceptance (origen: T179 backlog + task.md)

| # | Criterio | Estado actual | Prioridad |
|---|---|---|---|
| R1 | **Fallback de inferencia local** implementado y validado | ❌ Parcial (llama_preflight.py, heavy_job_gate.py existen; no es un fallback completo) | 🔴 Alta |
| R2 | **Aprobación G-MODEL + audit fresh-context** (score >80 y suite completa) | ⚠️ Datos antiguos (auditorías 57/100, 42/100); no re-ejecutados para el diff actual | 🔴 Alta |
| R3 | **Migración 0018** aplicada y verificada | ❌ No aplicada | 🟡 Media |
| R4 | **Verificación en VM objetivo (C:\superHarry-vm)** | ⚠️ Probaron en `superharry-dev` (dev-test); no en VM durable | 🔴 Alta |
| R5 | **Cancelación remota** y **reconciliación de proveedores** (T048/T049) | ❌ Sin implementar | 🔴 Alta |
| R6 | **Validación G-OPS** (service identity, backup, recovery, firewall) | ⚠️ T149 no completado | 🔴 Alta |
| R7 | **Pruebas de carga y recovery** (T150-T157) | ❌ No ejecutadas | 🟡 Media |
| R8 | **Release review y documentación** (T158) | ❌ No hecho | 🟡 Media |

---
## 2. Orden de ejecución recomendado

```
Fase 0: Pre-código (audit fresh-context)  → [1]
Fase 1: R1 + R2: Fallback local + Audit      → [2][3]
Fase 2: R5: Cancelación remota + Reconciliación → [4][5]
Fase 3: R3: Migración 0018                    → [6]
Fase 4: R4: Verificación en VM objetivo (C:\superHarry-vm) → [7]
Fase 5: R6: G-OPS (T149)                      → [8]
Fase 6: R7: Carga y recovery (T150-T157)      → [9]
Fase 7: R8: Release review y docs (T158)      → [10]
```

---
## 3. Detalle de fases

### Fase 0 — Pre-código (Obligatorio tras cualquier cambio)
1. Lanzar agente de auditoría fresh-context (sin la conversación de implementación) sobre el worktree completo.
2. Requisito: score estrictamente >80 para pistas parciales; en caso de audit incompleto → ejecutar suite completa de Django.
3. Verificar `SUPERHARRY_CONSTITUTION_SHA256` == hash actual de `constitution.md`.
4. Ejecutar `manage.py check`, `makemigrations --check --dry-run`, `git diff --check`.

### Fase 1 — Fallback de inferencia local (R1) + Audit G-MODEL (R2)

#### [2] Implementación F1: Fallback local
- El fallback debe funcionar con: modelo aprobado, streaming, salida JSON/constrainida, preservar constitution completo.
- Requisitos:
  - Programa `heavy_job_gate.py` → arbitra un solo "heavy job slot" por instancia, colas acotadas, timeouts, cancelación.
  - Integrar `llama_preflight.py` + modelo aprobado (Qwen/Gemma/Llama 3.2-1B/llama.cpp).
  - Verificar: streaming → stop → cancelación, cuota, contexto, performance.
  - Documentar: modelo, quantización, RAM usada, latencia, tokens/sec.
  - Tests: `manage.py test home.test_heavy_job_gate home.test_llama_preflight`

#### [3] Audit fresh-context + Aprobación G-MODEL
- Lanzar auditoría fresh-context sobre el diff actual (código + migraciones + configuración).
- Score: si >80 → pistas parciales + tests escalonados; si no → suite completa.
- Registrar evidencia: score, test list, resultados reales, constitution hash.
- Obtener aprobación G-MODEL (owner sign-off).

### Fase 2 — Cancelación remota y reconciliación (R5)

#### [4] Implementación F2: Cancelación remota
- Extender `ChatTurnCancellation` para:
  - Marcar cancelación pendiente ante el worker.
  - Envío de pedido de cancelación al provider (con timeout + reconcilación).
  - No reintentar peticiones canceladas.
  - Validar: cancelación inmediata, en-flight, cancelación después de respuesta parcial.
  - Tests: `test_cancellation_during_request_discards_result_and_holds_quota`, `test_interrupted_claim_is_closed_without_replay_or_releasing_unknowns` (ya pasan; agregar casos de cancelación remota).

#### [5] Implementación F3: Reconciliación de proveedores (T048/T049)
- Implementar acción web admin:
  - Resolver reservas (request/token) con evidencia correlacionada.
  - Debito de uso externo verificado.
  - Idempotencia: misma clave idempotente + misma disposición → resultado sin cambio.
  - Falla cerrado: datos malformados, excedentes, concurrencia.
  - Tests: `manage.py test tests.test_quota_reconciliation`

### Fase 3 — Migración 0018 (R3)

#### [6] Aplicar migración 0018
1. Verificar que el código fuente tiene la migración `home.0018` creada y validada.
2. `sudo -n /opt/superharry/venv/bin/python3 manage.py migrate home 0018 --plan` → confirmar solo 0018.
3. `sudo -n /opt/superharry/venv/bin/python3 manage.py migrate home 0018` → aplicar.
4. Verificar: `showmigrations` → `[X] 0018_...`.
5. `manage.py check`, `makemigrations --check --dry-run`, `git diff --check`.
6. Re-ejecutar suite T179 (22 tests) → OK.

### Fase 4 — Verificación en VM objetivo (R4)

#### [7] Desplegar a C:\superHarry-vm
1. Crear fuente reproducible (archive excluyendo .env, .git, .venv, DB):
   - `tar czf superharry-release-$(git rev-parse --short HEAD).tar.gz --exclude='.env' --exclude='.git' --exclude='.venv' --exclude='*/db.sqlite3' .`
2. Subir a `C:\superHarry-vm` y verificar SHA-256.
3. Aplicar migraciones en la VM objetivo:
   - `sudo -n /opt/superharry/venv/bin/python3 manage.py migrate home 0018` (si aplica)
   - Verificar `showmigrations` → [X] 0018.
4. Validar services, listeners, health endpoints.
5. Ejecutar suite T179 y tests de fondo en la VM objetivo:
   - `manage.py test home.test_t179_integration home.test_t179_recovery_acceptance`
   - `manage.py test home.test_provider_selector`
   - Verificar que no haya cambios de estado no autorizados.

### Fase 5 — G-OPS (T149) (R6)

#### [8] Validación operativa
1. **Service identity**: verificaciones de `superharry.service` (User/Group, WorkingDirectory, secrects, listeners, recovery).
2. **Backup/restore**: crear backup, restaurar a copia de prueba, verificar integridad.
3. **Firewall/network**: validar privado HTTPS, listener loopback, firewall reglas.
4. **Recovery**: prueba de restart, ejecución de jobs en pausa, restauración.
5. **Updates**: prueba de actualización, rollback.
6. **Audit**: verificar que audit events se escriben correctamente.

### Fase 6 — Carga y recovery (T150-T157) (R7)

#### [9] Carga y validación
1. **T150**: Congelar thresholds de la carga.
2. **T151-T155**: Evaluaciones de modelos local, STT, TTS, semántico.
3. **T156**: Validación de aislamiento (VM, sandbox, red, credenciales).
4. **T157**: Carga completa + recovery + backup/restore.
   - Verificar: sin OOM/swap, UI responsive, colas acotadas, datos persistentes, recovery offline.

### Fase 7 — Release (T158) (R8)

#### [10] Release review
1. Ejecutar checks finales: `manage.py check`, tests, `git diff --check`, constitution hash.
2. Reconciliar todas las tareas: T148, T149, T150-T158.
3. Documentar:
   - README/install/admin/recovery/update/model/privacy docs
   - SBOM/licenses/summary
   - CHANGELOG
   - Docs de benchmarks (evidencia roja/sintética solo)
4. Publicar artefacto verificable e installable.

---
## 4. Criterios de paro (stop conditions)

Parearse inmediatamente si:
- Audit fresh-context no puede completarse → usar suite completa.
- Migrar 0018 falla o produce inconsistencia → detener y revisar.
- PRUEBAS en VM objetivo (C:\superHarry-vm) fallan → no avanzar.
- Cualquier cambio que afecte a producción sin approbación → corregir primero.
- Fallback local no puede implementarse → documentar como requisito abierto (R1) y solicitar decisión del propietario antes de release.

## 5. Resumen de prioridades

| Prioridad | Tarea | Costo estimado | Depende de |
|---|---|---|---|
| 🔴 Alta | R1: Fallback local | Medio | T047, T050 |
| 🔴 Alta | R2: Audit fresh-context + G-MODEL | Median |  |
| 🔴 Alta | R4: Verificación en VM objetivo | Alto | Fase 0, Fase 1 |
| 🔴 Alta | R5: Cancelación remota + Reconciliación | Medio |  |
| 🔴 Alta | R6: G-OPS (T149) | Alto | R4 |
| 🟡 Media | R3: Migración 0018 | Bajo | Código fuente |
| 🟡 Media | R7: Carga y recovery (T150-T157) | Alto | R6 |
| 🟡 Media | R8: Release review y docs (T158) | Bajo | R7 |

---
## 6. Verificación inmediata (próximos pasos)

### ✅ COMPLETADO — Estado actual

| Fase | Tarea | Estado | Evidencia |
|---|---|---|---|
| Fase 0 | `manage.py check`, `makemigrations --check`, `git diff --check` | ✅ | "System check identified no issues", no changes |
| Fase 3 | Migración 0018 aplicada | ✅ | `[X] 0018_chatturn_openrouter_risk_accepted` |
| Fase 3 | Model `ChatTurn` actualizado | ✅ | `openrouter_risk_accepted = models.BooleanField(default=False)` |
| Fase 1 | Tests corregidos (18 cambios en 8 archivos) | ✅ | 18 áreas con `openrouter_risk_accepted=False` |
| **Fase 1** | **Pruebas síncronas T179** | ✅ | **22/22 OK** (83.8s) |
| **Fase 1** | Health endpoint | ✅ | `{"status":"ok"}` |
| **Fase 1** | Servicios activos | ✅ | `active` / `active` |

### Estado de los criterios R1-R8

| # | Criterio | Estado actual | Prioridad |
|---|---|---|---|
| R1 | Fallback de inferencia local | ⏳ Pendiente (requiere implementación profunda) | 🔴 Alta |
| R2 | Audit fresh-context + G-MODEL | ⏳ Pendiente (necesita audit fresh-context) | 🔴 Alta |
| R3 | Migración 0018 aplicada | ✅ | 🟢 Completado |
| R4 | Verificación en VM objetivo | 🟡 Pendiente (VM durable C:\superHarry-vm) | 🔴 Alta |
| R5 | Cancelación remota + Reconciliación | ⏳ Pendiente (implementación T048/T049) | 🔴 Alta |
| R6 | G-OPS (T149) | ⏳ Pendiente | 🔴 Alta |
| R7 | Carga y recovery (T150-T157) | ⏳ Pendiente | 🟡 Media |
| R8 | Release review y docs (T158) | ⏳ Pendiente | 🟡 Media |

---
## 7. Próximos pasos (solo ítems pendientes)
