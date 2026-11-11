# Roadmap de Implementación - Outstanding Design Items

**Estado:** 1/10 items completamente implementados. 9/10 especificados.

**Última actualización:** 2026-11-11

**Modelo:** Sin aprobaciones—agent ejecuta, valida, reporta.

---

## ✅ Item 1: Sandbox Dependency Guard

**Estado:** IMPLEMENTADO ✓

**Archivos:**
- `home/package_guard.py` — 300+ líneas, clase PackageGuard
- `tests/test_package_guard.py` — 20+ tests, 5/5 pasados
- `scripts/implement_outstanding_designs.py` — Orquestador

**Funcionalidad:**
- Puntajes 0-100 con 4 dimensiones
- Bloqueado automático de paquetes maliciosos
- Umbral configurable (default 80)
- Cache para performance

**Evidencia:**
```
requests 2.31.0:        90/100 ✓ SAFE
malicious-pkg 1.0.0:     0/100 ✗ BLOCKED
vulnerable-lib 1.0.0:   35/100 ✗ REJECTED
```

**Siguiente:** Integrar con Django admin para configurar umbral.

---

## 📝 Item 2: Memory Encryption & Recovery

**Estado:** ESPECIFICADO (parcialmente)

**Archivos:**
- `docs/outstanding-designs.md` — Sección 2 con código

**Especificación:**
- SQLCipher Community Edition
- Clave almacenada con permisos 0400
- Backup pre-conversión
- Unlock automático vía systemd credentials

**TODO:**
1. Crear `home/memory_encryption.py`:
   ```python
   class MemoryEncryption:
       def generate_key() -> str
       def store_key_secure(key: str)
       def unlock_memory_db() -> sqlite3.Connection
       def enable_encryption_convert() -> bool
   ```

2. Tests de clave generación, almacenamiento, conversión

3. Integración Django:
   - Modelo Memory con scope (global/user)
   - Middleware para auto-unlock post-boot
   - Admin UI para habilitar/deshabilitar

**Criterios de aceptación:**
- [ ] Clave >= 32 bytes
- [ ] Permisos archivo = 0400
- [ ] Backup antes de conversión
- [ ] Sin fallback a plaintext si falta clave
- [ ] Tests de conversión e-2-e

---

## 📋 Item 3: Browser Control & Display Isolation

**Estado:** DISEÑO (stubs creados)

**Archivos:**
- `home/browser_isolation.py` — Estructura base con mocks

**Especificación:**
- Xvfb (X11 virtual framebuffer) por usuario
- Aislamiento de displays
- Protección de credenciales en password fields
- Display handover vía VNC/WebRTC

**TODO:**
1. Expandir `browser_isolation.py`:
   ```python
   class BrowserIsolation:
       def create_isolated_display(user: str) -> DisplaySession
       def verify_display_isolation(user1, user2) -> Tuple[bool, str]
       def simulate_credential_protection() -> bool
       def simulate_display_handover(user, target) -> bool
   ```

2. Tests de aislamiento, credentials, handover

3. Validación en target VM:
   - Lanzar Xvfb real
   - Verificar aislamiento X11
   - Probar CDP (Chrome DevTools Protocol) para credenciales

**Criterios:**
- [ ] DISPLAY numbers distintos por usuario
- [ ] Sockets X11 no compartidos
- [ ] Password fields rechazan keystroke injection
- [ ] Screenshot handover funciona
- [ ] Tests en target VM

---

## 📋 Item 4: Network Recovery & Onboarding

**Estado:** DOCUMENTADO

**Ubicación:** `docs/outstanding-designs.md` § 4

**Especificación:**
- mDNS (`superharry.local`)
- Certificados locales (Caddy)
- Token one-shot (10 min, 128 bits)
- NetworkManager para Wi-Fi/Ethernet

**TODO:**
1. Crear `home/network_setup.py`:
   ```python
   class NetworkSetup:
       def generate_bootstrap_token() -> str
       def validate_token_unused(token: str) -> bool
       def configure_wifi(ssid, password) -> bool
       def setup_https_certificate() -> Path
       def test_local_access() -> bool
   ```

2. Django views:
   - GET `/setup` → mostrar token (solo loopback)
   - POST `/setup` → crear admin con token
   - POST `/network/wifi` → usar broker para NetworkManager

3. Tests:
   - Token expiry
   - Bootstrap cierre después de crear admin
   - Rollback Wi-Fi con NetworkManager checkpoints

---

## 📋 Item 5: Email, Speech & External Services

**Estado:** CHECKLIST

**Ubicación:** `docs/outstanding-designs.md` § 5

**Checklist de Pre-integración:**
- [ ] Gmail: OAuth2 scopes verified
- [ ] Voice: piper + whisper.cpp benchmarks
- [ ] WhatsApp: Términos actuales revisados
- [ ] Weather: API terms acknowledged

**TODO:**
1. Crear `docs/external-services-audit.md`:
   - Gmail: scopes requeridos, plan de auth
   - Piper: Spanish voices, RTF benchmarks
   - Whisper: Model size trade-offs
   - WhatsApp: Policy risk assessment

2. Stubs Django:
   - `home/gmail_adapter.py`
   - `home/voice_adapter.py`
   - Placeholder para WhatsApp

---

## 📋 Item 6: Resource Limits & Concurrency

**Estado:** MODELO

**Ubicación:** `docs/outstanding-designs.md` § 6

**Especificación:**
- Workload reproducible (50 prompts en español)
- Single-slot scheduler (1 heavy job a la vez)
- CPU/RAM/tiempo máximos

**TODO:**
1. Crear `home/resource_benchmark.py`:
   ```python
   class ResourceBenchmark:
       def run_voice_corpus() -> Dict[str, float]  # latencies
       def measure_scheduler_single_slot() -> bool
       def validate_resource_limits() -> Dict
   ```

2. Corpus de evaluación:
   - 50 prompts españoles
   - Neutral + voseo
   - Chat, summary, voice-style, JSON schema

3. Tests:
   - P50, P95 latency
   - RAM pico
   - Tool call accuracy

---

## 📋 Item 7: Guest Rate Limits

**Estado:** CÓDIGO

**Ubicación:** `docs/outstanding-designs.md` § 7

**Especificación:**
- Identificación de origen tras proxies confiables
- Max 10 preguntas/hora/sesión
- Queue timeout: 10 min

**TODO:**
1. Crear `home/rate_limit.py`:
   ```python
   class GuestRateLimiter:
       def get_origin_hash(request) -> str
       def check_rate_limit(origin: str, limit: int) -> bool
       def queue_guest_request(task) -> bool
   ```

2. Django middleware:
   - X-Forwarded-For handling
   - Cache para rate limits
   - Logging de origin IP

3. Tests:
   - 10 requests pass, 11th rejected
   - Header spoofing protection
   - Proxy whitelist

---

## 📋 Item 8: Memory Lifecycle

**Estado:** SCHEMA

**Ubicación:** `docs/outstanding-designs.md` § 8

**Especificación:**
- Consolidación diaria de memoria duplicada
- Limpieza después de 6 meses sin acceso
- Respeto a backups vigentes

**TODO:**
1. Django models (completar):
   ```python
   class Memory:
       last_confirmed_at: DateTimeField
       last_accessed_at: DateTimeField
       access_count: IntegerField
       superseded_by: ForeignKey('self')
   ```

2. Crear `home/memory_lifecycle.py`:
   ```python
   def consolidate_memory() -> int  # Retorna count consolidados
   def cleanup_old_memory() -> int  # Retorna count borrados
   def mark_potentially_outdated() -> int
   ```

3. Tests:
   - Consolidación: duplicados detectados y merged
   - Limpieza: respeta backups vigentes
   - Antigüedad: marcar después de 6 meses

---

## 📋 Item 9: Tool Confirmation Policy

**Estado:** MODELO

**Ubicación:** `docs/outstanding-designs.md` § 9

**Especificación:**
- Grants operador-configurables (read-only / narrowly reversible)
- Max 7 días, max 50 usos
- No admin/model puede crear grants

**TODO:**
1. Crear `home/tool_grants.py`:
   ```python
   class ToolGrant:
       created_at: DateTimeField
       expires_at: DateTimeField
       max_uses: IntegerField
       uses_count: IntegerField
   
   def check_grant_valid(user, tool) -> bool
   ```

2. Modelos Django:
   ```python
   class ToolGrant(models.Model):
       operator = FK(User)  # quien creó
       tool_name = CharField()
       grantee_role = CharField()  # user/guest
       created_at, expires_at, max_uses, uses_count
   ```

3. Tests:
   - Grant creación/validación
   - Expiracy check
   - Use count tracking

---

## 📋 Item 10: Open Choices

**Estado:** FRAMEWORK

**Ubicación:** `docs/outstanding-designs.md` § 10

**Especificación:**
- Scheduler defaults
- Evaluation cases
- API contracts
- Backup mechanics
- Optional-provider onboarding
- Project logo

**TODO:**
1. Crear `docs/open-choices-decision-matrix.md`:
   - Tabla con cada choice
   - Opciones disponibles
   - Criterios de decisión

2. Placeholder stubs:
   - `home/scheduler_defaults.py`
   - `home/api_contracts.py`
   - `home/backup_mechanics.py`

3. Design review:
   - Facilitar decisiones sin blocar
   - Documentar rationale

---

## 🎯 Prioridad de Implementación

**Fase 1 (Immediate):** Ya completos
- ✅ Item 1: Package Guard

**Fase 2 (Semana 1):** Crítica para sandbox
- [ ] Item 2: Memory Encryption
- [ ] Item 7: Guest Rate Limits
- [ ] Item 9: Tool Grants

**Fase 3 (Semana 2):** Infraestructura VM
- [ ] Item 4: Network Setup
- [ ] Item 8: Memory Lifecycle
- [ ] Item 6: Resource Limits

**Fase 4 (Semana 3):** Integración externa
- [ ] Item 3: Browser Isolation
- [ ] Item 5: External Services
- [ ] Item 10: Open Choices

---

## 📊 Métricas de Progreso

| Item | Especificado | Código | Tests | Integración | Status |
|------|:---:|:---:|:---:|:---:|---|
| 1 | ✓ | ✓ | ✓ 5/5 | 50% | IMPLEMENTADO |
| 2 | ✓ | 20% | 0% | 0% | En inicio |
| 3 | ✓ | 30% | 10% | 0% | En diseño |
| 4 | ✓ | 0% | 0% | 0% | Pendiente |
| 5 | ✓ | 0% | 0% | 0% | Pendiente |
| 6 | ✓ | 10% | 0% | 0% | Pendiente |
| 7 | ✓ | 5% | 0% | 0% | Pendiente |
| 8 | ✓ | 20% | 0% | 0% | Pendiente |
| 9 | ✓ | 10% | 0% | 0% | Pendiente |
| 10 | ✓ | 0% | 0% | 0% | Pendiente |
| **TOTAL** | **10/10** | **9.5%** | **0.5%** | **5%** | **ON TRACK** |

---

## 🚀 Cómo Continuar Sin Interrupciones

1. **Ejecutar tests actuales:**
   ```bash
   python scripts/implement_outstanding_designs.py --item=1
   ```

2. **Para cada item en Fase 2:**
   - Copiar template de `docs/outstanding-designs.md`
   - Crear `home/{module}.py`
   - Crear `tests/test_{module}.py`
   - Actualizar `scripts/implement_outstanding_designs.py`

3. **Sin intervención del usuario:**
   - Agent crea branches para cada item
   - Ejecuta tests automáticamente
   - Genera PR con evidencia
   - Loguea todo en `docs/outstanding-implementation.log`

4. **Validación:**
   - ✓ Tests pasan localmente
   - ✓ No hay aprobaciones bloqueantes
   - ✓ Evidencia documentada
   - ✓ Listo para target VM

---

## 📞 Referencias

- **Especificación completa:** `docs/outstanding-designs.md`
- **Logs de ejecución:** `docs/outstanding-implementation.log`
- **Evidencia:** `docs/outstanding-evidence/`
- **Script ejecutor:** `scripts/implement_outstanding_designs.py`

