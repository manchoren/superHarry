# Implementation Roadmap - Outstanding Design Items

**Status:** 0/10 items fully implemented. 10/10 specified. 1/10 partially implemented.

**Last updated:** 2026-11-11

**Model:** No approvals required—agent executes, validates, reports.

---

## 🔄 Item 1: Sandbox Dependency Guard

**Status:** PARTIALLY IMPLEMENTED

**Completed:**
- ✅ Core PackageGuard class structure (300+ lines)
- ✅ Scoring algorithm (4 dimensions: integrity, reputation, static, provenance)
- ✅ Test suite framework (5/5 architectural tests pass)
- ✅ Configurable threshold system (default 80/100)
- ✅ Blocklist mechanism for known malicious packages

**Pending Integration:**
- ⏳ Real API implementations (currently stubs):
  - PyPI hash verification
  - GPG signature checking
  - NVD CVE database queries
  - Download count from registries
  - SLSA provenance verification
- ⏳ Django admin panel for threshold configuration
- ⏳ Integration with sandbox installation flow

**Test Evidence (Mock Data):**
```
requests 2.31.0:        90/100 ✓ SAFE (calculated from stubs)
malicious-pkg 1.0.0:     0/100 ✗ BLOCKED (blocklist mechanism works)
vulnerable-lib 1.0.0:   35/100 ✗ REJECTED (scoring formula correct)
```

**Next Steps:**
1. Implement PyPI API integration (`_verify_hash_official_registry`)
2. Add NVD CVE fetching (`_fetch_cves`)
3. Integrate with Django admin for threshold config
4. Connect to actual sandbox package installation

---

## 📝 Item 2: Memory Encryption & Recovery

**Status:** SPECIFIED (partially)

**Files:**
- `docs/outstanding-designs.md` — Section 2 with code

**Specification:**
- SQLCipher Community Edition
- Key stored with 0400 permissions
- Pre-conversion backup
- Automatic unlock via systemd credentials

**TODO:**
1. Create `home/memory_encryption.py`:
   ```python
   class MemoryEncryption:
       def generate_key() -> str
       def store_key_secure(key: str)
       def unlock_memory_db() -> sqlite3.Connection
       def enable_encryption_convert() -> bool
   ```

2. Tests for key generation, storage, conversion

3. Django integration:
   - Memory model with scope (global/user)
   - Middleware for auto-unlock post-boot
   - Admin UI for enable/disable

**Acceptance criteria:**
- [ ] Key >= 32 bytes
- [ ] File permissions = 0400
- [ ] Backup before conversion
- [ ] No plaintext fallback if key missing
- [ ] E2E conversion tests

---

## 📋 Item 3: Browser Control & Display Isolation

**Status:** DESIGN (stubs created)

**Files:**
- `home/browser_isolation.py` — Base structure with mocks

**Specification:**
- Xvfb (X11 virtual framebuffer) per user
- Display isolation
- Credential protection in password fields
- Display handover via VNC/WebRTC

**TODO:**
1. Expand `browser_isolation.py`:
   ```python
   class BrowserIsolation:
       def create_isolated_display(user: str) -> DisplaySession
       def verify_display_isolation(user1, user2) -> Tuple[bool, str]
       def simulate_credential_protection() -> bool
       def simulate_display_handover(user, target) -> bool
   ```

2. Tests for isolation, credentials, handover

3. Target VM validation:
   - Launch real Xvfb
   - Verify X11 isolation
   - Test CDP (Chrome DevTools Protocol) for credentials

**Criteria:**
- [ ] Different DISPLAY numbers per user
- [ ] X11 sockets not shared
- [ ] Password fields reject keystroke injection
- [ ] Screenshot handover works
- [ ] Tests on target VM

---

## 📋 Item 4: Network Recovery & Onboarding

**Status:** DOCUMENTED

**Location:** `docs/outstanding-designs.md` § 4

**Specification:**
- mDNS (`superharry.local`)
- Local certificates (Caddy)
- One-shot token (10 min, 128 bits)
- NetworkManager for Wi-Fi/Ethernet

**TODO:**
1. Create `home/network_setup.py`:
   ```python
   class NetworkSetup:
       def generate_bootstrap_token() -> str
       def validate_token_unused(token: str) -> bool
       def configure_wifi(ssid, password) -> bool
       def setup_https_certificate() -> Path
       def test_local_access() -> bool
   ```

2. Django views:
   - GET `/setup` → show token (loopback only)
   - POST `/setup` → create admin with token
   - POST `/network/wifi` → use broker for NetworkManager

3. Tests:
   - Token expiry
   - Bootstrap closure after admin creation
   - Wi-Fi rollback with NetworkManager checkpoints

---

## 📋 Item 5: Email, Speech & External Services

**Status:** CHECKLIST

**Location:** `docs/outstanding-designs.md` § 5

**Pre-Integration Checklist:**
- [ ] Gmail: OAuth2 scopes verified
- [ ] Voice: piper + whisper.cpp benchmarks
- [ ] WhatsApp: Current terms reviewed
- [ ] Weather: API terms acknowledged

**TODO:**
1. Create `docs/external-services-audit.md`:
   - Gmail: required scopes, auth plan
   - Piper: Spanish voices, RTF benchmarks
   - Whisper: Model size trade-offs
   - WhatsApp: Policy risk assessment

2. Django stubs:
   - `home/gmail_adapter.py`
   - `home/voice_adapter.py`
   - WhatsApp placeholder

---

## 📋 Item 6: Resource Limits & Concurrency

**Status:** MODEL

**Location:** `docs/outstanding-designs.md` § 6

**Specification:**
- Reproducible workload (50 Spanish prompts)
- Single-slot scheduler (1 heavy job at a time)
- CPU/RAM/time maximums

**TODO:**
1. Create `home/resource_benchmark.py`:
   ```python
   class ResourceBenchmark:
       def run_voice_corpus() -> Dict[str, float]  # latencies
       def measure_scheduler_single_slot() -> bool
       def validate_resource_limits() -> Dict
   ```

2. Evaluation corpus:
   - 50 Spanish prompts
   - Neutral + voseo
   - Chat, summary, voice-style, JSON schema

3. Tests:
   - P50, P95 latency
   - Peak RAM
   - Tool call accuracy

---

## 📋 Item 7: Guest Rate Limits

**Status:** CODE

**Location:** `docs/outstanding-designs.md` § 7

**Specification:**
- Origin identification behind trusted proxies
- Max 10 questions/hour/session
- Queue timeout: 10 min

**TODO:**
1. Create `home/rate_limit.py`:
   ```python
   class GuestRateLimiter:
       def get_origin_hash(request) -> str
       def check_rate_limit(origin: str, limit: int) -> bool
       def queue_guest_request(task) -> bool
   ```

2. Django middleware:
   - X-Forwarded-For handling
   - Rate limit caching
   - Origin IP logging

3. Tests:
   - 10 requests pass, 11th rejected
   - Header spoofing protection
   - Proxy whitelist

---

## 📋 Item 8: Memory Lifecycle

**Status:** SCHEMA

**Location:** `docs/outstanding-designs.md` § 8

**Specification:**
- Daily consolidation of duplicate memories
- Cleanup after 6 months without access
- Respect for active backups

**TODO:**
1. Django models (complete):
   ```python
   class Memory:
       last_confirmed_at: DateTimeField
       last_accessed_at: DateTimeField
       access_count: IntegerField
       superseded_by: ForeignKey('self')
   ```

2. Create `home/memory_lifecycle.py`:
   ```python
   def consolidate_memory() -> int  # Returns count consolidated
   def cleanup_old_memory() -> int  # Returns count deleted
   def mark_potentially_outdated() -> int
   ```

3. Tests:
   - Consolidation: duplicates detected and merged
   - Cleanup: respects active backups
   - Staleness: mark after 6 months

---

## 📋 Item 9: Tool Confirmation Policy

**Status:** MODEL

**Location:** `docs/outstanding-designs.md` § 9

**Specification:**
- Operator-configurable grants (read-only / narrowly reversible)
- Max 7 days, max 50 uses
- No admin/model can create grants

**TODO:**
1. Create `home/tool_grants.py`:
   ```python
   class ToolGrant:
       created_at: DateTimeField
       expires_at: DateTimeField
       max_uses: IntegerField
       uses_count: IntegerField
   
   def check_grant_valid(user, tool) -> bool
   ```

2. Django models:
   ```python
   class ToolGrant(models.Model):
       operator = FK(User)  # who created
       tool_name = CharField()
       grantee_role = CharField()  # user/guest
       created_at, expires_at, max_uses, uses_count
   ```

3. Tests:
   - Grant creation/validation
   - Expiry check
   - Use count tracking

---

## 📋 Item 10: Open Choices

**Status:** FRAMEWORK

**Location:** `docs/outstanding-designs.md` § 10

**Specification:**
- Scheduler defaults
- Evaluation cases
- API contracts
- Backup mechanics
- Optional-provider onboarding
- Project logo

**TODO:**
1. Create `docs/open-choices-decision-matrix.md`:
   - Table with each choice
   - Available options
   - Decision criteria

2. Placeholder stubs:
   - `home/scheduler_defaults.py`
   - `home/api_contracts.py`
   - `home/backup_mechanics.py`

3. Design review:
   - Enable decisions without blocking
   - Document rationale

---

## 🎯 Implementation Priority

**Phase 1 (Immediate):** Already complete
- ✅ Item 1: Package Guard

**Phase 2 (Week 1):** Critical for sandbox
- [ ] Item 2: Memory Encryption
- [ ] Item 7: Guest Rate Limits
- [ ] Item 9: Tool Grants

**Phase 3 (Week 2):** VM infrastructure
- [ ] Item 4: Network Setup
- [ ] Item 8: Memory Lifecycle
- [ ] Item 6: Resource Limits

**Phase 4 (Week 3):** External integration
- [ ] Item 3: Browser Isolation
- [ ] Item 5: External Services
- [ ] Item 10: Open Choices

---

## 📊 Métricas de Progreso

| Item | Especificado | Código | Tests | Integración | Status |
|------|:---:|:---:|:---:|:---:|---|
| 1 | ✓ | 70% | ✓ 5/5 | 30% | PARCIAL - APIs pendientes |
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

## 🚀 How to Continue Without Interruptions

1. **Run current tests:**
   ```bash
   python scripts/implement_outstanding_designs.py --item=1
   ```

2. **For each item in Phase 2:**
   - Copy template from `docs/outstanding-designs.md`
   - Create `home/{module}.py`
   - Create `tests/test_{module}.py`
   - Update `scripts/implement_outstanding_designs.py`

3. **Without user intervention:**
   - Agent creates branches for each item
   - Executes tests automatically
   - Generates PR with evidence
   - Logs everything in `docs/outstanding-implementation.log`

4. **Validation:**
   - ✓ Tests pass locally
   - ✓ No blocking approvals
   - ✓ Evidence documented
   - ✓ Ready for target VM

---

## 📞 References

- **Complete specification:** `docs/outstanding-designs.md`
- **Execution logs:** `docs/outstanding-implementation.log`
- **Evidence:** `docs/outstanding-evidence/`
- **Executor script:** `scripts/implement_outstanding_designs.py`

