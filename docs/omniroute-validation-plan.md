# omniroute Validation Plan for Target VM

**Date:** 2026-11-11  
**Objective:** Validate omniroute integration and operation on production target VM  
**Status:** 🔄 In progress

---

## 1. Executive Summary

omniroute is the centralized gateway that manages:
- Credentials for ALL AI model providers (Nous Portal, OpenRouter, Groq, Gemini, Ollama)
- Smart routing with automatic fallback chains
- Centralized logging of usage, tokens, and costs
- Unified OpenAI-compatible interface

superHarry **does not store** provider credentials directly, only omniroute's API key.

---

## 2. Integration Architecture

```
┌──────────────────┐
│ superHarry       │
│ Django App       │
└────────┬─────────┘
         │ HTTP POST
         │ Authorization: Bearer {omniroute_api_key}
         ▼
┌─────────────────────────────────┐
│ omniroute :20128                │
│ Smart Gateway                   │
│ - Credential management         │
│ - Fallback routing              │
│ - Quota tracking                │
│ - Audit logging                 │
└────────┬────────────────────────┘
         │
         ├─► Nous Portal (primario)
         ├─► OpenRouter (fallback 1)
         ├─► Groq (fallback 2)
         └─► Ollama :11434 (local - qwen3.5:4b)
```

---

## 3. Validation Prerequisites

### 3.1 Network Checks

- [ ] Port 20128 accessible from superHarry
- [ ] Port 11434 accessible from omniroute (Ollama)
- [ ] DNS/networking functional for cloud access

### 3.2 Required Services

- [ ] omniroute service active and responding
- [ ] Ollama installed and qwen3.5:4b model downloaded
- [ ] superHarry configured with `OMNIROUTE_ENDPOINT` and API key

### 3.3 Credentials

- [ ] omniroute API key generated and stored in `.env`
- [ ] Providers configured in omniroute dashboard:
  - Nous Portal API key
  - OpenRouter API key (optional)
  - Groq API key (optional)
  - Gemini OAuth token (optional)
  - Ollama endpoint (localhost:11434)

---

## 4. Test Cases

### 4.1 Level 1 Tests: Basic Connectivity

#### T1.1 - Health Check
**Objective:** Verify omniroute is responding

```bash
curl -X GET http://localhost:20128/health
```

**Resultado esperado:**
```json
{
  "status": "ok",
  "version": "x.x.x",
  "providers": {
    "nous-portal": "configured",
    "ollama": "connected"
  }
}
```

#### T1.2 - Dashboard Access
**Objective:** Access the web interface

```bash
curl -I http://localhost:20128
```

**Expected result:** HTTP 200 or redirect to login

---

### 4.2 Level 2 Tests: Authentication

#### T2.1 - Valid API Key
**Objective:** Verify authentication with correct API key

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

**Expected result:** HTTP 200 with model response

#### T2.2 - Invalid API Key
**Objective:** Verify rejection of incorrect credentials

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer invalid-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Test"}]
  }'
```

**Expected result:** HTTP 401 Unauthorized

---

### 4.3 Level 3 Tests: Model Routing

#### T3.1 - External Model (Nous Portal)
**Objective:** Validate routing to primary cloud provider

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [
      {"role": "system", "content": "Responde en español"},
      {"role": "user", "content": "¿Cuál es la capital de Argentina?"}
    ],
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

**Validations:**
- HTTP 200
- Coherent response in Spanish
- `model` field in response shows provider used
- Response time < 10 seconds

#### T3.2 - Local Model (Ollama)
**Objective:** Validate routing to local model

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen3.5:4b",
    "messages": [
      {"role": "user", "content": "¿Qué es Python?"}
    ],
    "max_tokens": 100,
    "temperature": 0.5
  }'
```

**Validations:**
- HTTP 200
- Response from local model
- No calls to external providers
- Latency < 30 seconds (hardware dependent)

#### T3.3 - Non-Existent Model
**Objective:** Error handling for unknown model

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "invalid-provider/invalid-model",
    "messages": [{"role": "user", "content": "Test"}]
  }'
```

**Expected result:** HTTP 400 or 404 with clear error message

---

### 4.4 Level 4 Tests: Fallback Chain

#### T4.1 - Automatic Fallback
**Objective:** Validate fallback when Nous Portal fails

**Setup:** Simulate Nous Portal failure (temporarily misconfigure API key in omniroute dashboard)

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Fallback test"}]
  }'
```

**Validations:**
- HTTP 200 (no error to user)
- Response comes from alternative provider (OpenRouter, Groq, or Ollama)
- omniroute log shows primary attempt and fallback success

#### T4.2 - Fallback to Local
**Objective:** Use Ollama if all cloud providers fail

**Setup:** Misconfigure all cloud providers

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Local fallback test"}]
  }'
```

**Validations:**
- HTTP 200
- Response from local model (qwen3.5:4b)
- Log shows complete fallback to Ollama

---

### 4.5 Level 5 Tests: Quotas and Rate Limiting

#### T5.1 - Token Tracking
**Objective:** Verify token counting in responses

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Escribe 5 líneas sobre Python"}],
    "max_tokens": 200
  }'
```

**Validations:**
- Response includes `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`
- Values are > 0 and coherent

#### T5.2 - Usage Query
**Objective:** Get usage statistics

```bash
curl -X GET http://localhost:20128/usage \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}"
```

**Expected result:**
```json
{
  "total_requests": 123,
  "total_tokens": 45678,
  "by_provider": {
    "nous-portal": {"requests": 100, "tokens": 40000},
    "ollama": {"requests": 23, "tokens": 5678}
  },
  "quota_remaining": {...}
}
```

---

### 4.6 Level 6 Tests: Advanced Features

#### T6.1 - Streaming Responses
**Objective:** Validate SSE (Server-Sent Events) streaming

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Cuenta del 1 al 10"}],
    "stream": true
  }'
```

**Validations:**
- Content-Type: text/event-stream
- Receives `data: {...}` events incrementally
- Last event is `data: [DONE]`

#### T6.2 - Tool Calling / Function Calling
**Objective:** Validate tool passing to model

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "¿Qué hora es?"}],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_current_time",
          "description": "Obtiene la hora actual",
          "parameters": {"type": "object", "properties": {}}
        }
      }
    ]
  }'
```

**Validations:**
- Model returns `tool_calls` if it decides to use the function
- Correct tool call format

#### T6.3 - Reasoning Mode Off (Memory Agent)
**Objective:** Verify reasoning can be disabled

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nous-ai/solar-mini-4",
    "messages": [{"role": "user", "content": "Test"}],
    "reasoning": false
  }'
```

**Validations:**
- Response does NOT include reasoning tokens or internal blocks
- Lower latency (if model supports this feature)

---

### 4.7 Level 7 Tests: superHarry Integration

#### T7.1 - Call from Django
**Script:** `scripts/test_omniroute_integration.py`

```python
import os
import requests
from django.conf import settings

def test_superharry_to_omniroute():
    """Simulates a call from superHarry to omniroute."""
    
    endpoint = os.getenv('OMNIROUTE_ENDPOINT', 'http://localhost:20128/v1')
    api_key = os.getenv('OMNIROUTE_API_KEY')
    
    if not api_key:
        raise ValueError("OMNIROUTE_API_KEY not configured in .env")
    
    response = requests.post(
        f"{endpoint}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "nous-ai/solar-mini-4",
            "messages": [
                {"role": "user", "content": "Hola, ¿funcionas correctamente?"}
            ],
            "max_tokens": 50
        },
        timeout=30
    )
    
    response.raise_for_status()
    data = response.json()
    
    assert 'choices' in data
    assert len(data['choices']) > 0
    assert 'message' in data['choices'][0]
    
    print(f"✅ Response received: {data['choices'][0]['message']['content']}")
    print(f"📊 Tokens used: {data.get('usage', {})}")
    
    return True

if __name__ == "__main__":
    test_superharry_to_omniroute()
```

#### T7.2 - Complete Chat Test (End-to-End)
**Objective:** Validate complete flow from UI to response

1. Log in as `admin` in superHarry
2. Open chat
3. Send message: "Explain what Django is in one line"
4. Verify:
   - Response appears in UI
   - Model used is correct (shown in UI)
   - No errors in Django logs
   - omniroute log records the request

---

## 5. Monitoring and Debugging

### 5.1 omniroute Logs

**Location (depends on installation):**
```bash
# If running as systemd service
sudo journalctl -u omniroute -f

# If running in container
docker logs -f omniroute

# File logs
tail -f /var/log/omniroute/access.log
tail -f /var/log/omniroute/error.log
```

### 5.2 omniroute Dashboard

Access: `http://localhost:20128` (or VM IP)

**Verify:**
- [ ] Provider status (green/active)
- [ ] Request graphs by provider
- [ ] Tokens consumed (daily/monthly)
- [ ] Recent errors
- [ ] Average latency

### 5.3 Key Metrics

| Metric | Expected Value | Action if out of range |
|---------|----------------|------------------------|
| P50 Latency (cloud) | < 3s | Check network / provider |
| P95 Latency (cloud) | < 10s | Investigate timeouts |
| P50 Latency (local) | < 5s | Check VM resources |
| Error rate | < 1% | Review error logs |
| Fallback rate | < 10% | Check quotas / credentials |

---

## 6. Common Troubleshooting

### 6.1 Error: Connection Refused (port 20128)

**Causes:**
- omniroute is not running
- Firewall blocking port

**Solution:**
```bash
# Verificar si omniroute está activo
sudo systemctl status omniroute

# Reiniciar
sudo systemctl restart omniroute

# Verificar puerto
sudo netstat -tlnp | grep 20128
```

### 6.2 Error: 401 Unauthorized

**Causas:**
- API key incorrecta
- API key no configurada en omniroute

**Solución:**
```bash
# Verificar .env de superHarry
grep OMNIROUTE_API_KEY .env

# Regenerar API key en omniroute dashboard
# Actualizar .env con nueva key
```

### 6.3 Error: Model Not Found

**Causas:**
- Proveedor no configurado
- Nombre de modelo incorrecto

**Solución:**
- Verificar en dashboard que el proveedor esté configurado
- Usar nombres exactos: `nous-ai/solar-mini-4`, `ollama/qwen3.5:4b`

### 6.4 Ollama Local No Responde

**Causas:**
- Ollama no instalado
- Modelo qwen3.5:4b no descargado
- Puerto 11434 bloqueado

**Solución:**
```bash
# Verificar Ollama
curl http://localhost:11434/api/tags

# Descargar modelo si falta
ollama pull qwen3.5:4b

# Verificar en omniroute que Ollama provider apunta a localhost:11434
```

### 6.5 Fallback No Funciona

**Causas:**
- Fallback chain no configurada correctamente
- Todos los proveedores fallan simultáneamente

**Solución:**
- Revisar configuración de fallback en omniroute
- Probar cada proveedor individualmente
- Asegurar que Ollama funciona como último fallback

---

## 7. Checklist de Validación Final

### 7.1 Pre-Producción

- [ ] Todos los tests nivel 1-7 pasan
- [ ] Dashboard omniroute accesible y muestra datos
- [ ] Logs no muestran errores críticos
- [ ] Fallback chain funciona correctamente
- [ ] Modelo local (qwen3.5:4b) responde en < 30s
- [ ] superHarry puede hacer llamadas exitosas
- [ ] Quotas configuradas correctamente
- [ ] API key de omniroute con permisos 0400

### 7.2 Post-Despliegue

- [ ] Monitoreo de métricas por 24h
- [ ] Revisión de logs de producción
- [ ] Test de carga con múltiples usuarios concurrentes
- [ ] Validación de logs de auditoría
- [ ] Backup de configuración de omniroute

---

## 8. Scripts de Automatización

### 8.1 Script de Validación Completa

Crear: `scripts/validate_omniroute.py`

```python
#!/usr/bin/env python3
"""
Script de validación automática de omniroute.
Ejecuta todos los tests y genera reporte.
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    error: str = ""

class OmnirouteValidator:
    def __init__(self):
        self.endpoint = os.getenv('OMNIROUTE_ENDPOINT', 'http://localhost:20128')
        self.api_key = os.getenv('OMNIROUTE_API_KEY')
        self.results: List[TestResult] = []
        
        if not self.api_key:
            raise ValueError("OMNIROUTE_API_KEY no configurada")
    
    def run_all_tests(self) -> bool:
        """Executes all tests and returns True if all pass."""
        print("🚀 Starting omniroute validation...")
        print(f"📍 Endpoint: {self.endpoint}\n")
        
        tests = [
            ("Health Check", self.test_health),
            ("Auth Válida", self.test_auth_valid),
            ("Auth Inválida", self.test_auth_invalid),
            ("Modelo Externo", self.test_external_model),
            ("Modelo Local", self.test_local_model),
            ("Streaming", self.test_streaming),
            ("Usage Stats", self.test_usage_stats),
        ]
        
        for name, test_func in tests:
            result = self._run_test(name, test_func)
            self.results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {name} ({result.duration_ms:.0f}ms)")
            if not result.passed:
                print(f"   Error: {result.error}")
        
        return all(r.passed for r in self.results)
    
    def _run_test(self, name: str, test_func) -> TestResult:
        """Ejecuta un test individual y captura excepciones."""
        import time
        start = time.time()
        
        try:
            test_func()
            duration_ms = (time.time() - start) * 1000
            return TestResult(name, True, duration_ms)
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return TestResult(name, False, duration_ms, str(e))
    
    def test_health(self):
        """Test: Health check endpoint."""
        resp = requests.get(f"{self.endpoint}/health", timeout=10)
        resp.raise_for_status()
        
        data = resp.json()
        assert data.get('status') in ['ok', 'healthy'], "Health status inválido"
    
    def test_auth_valid(self):
        """Test: Autenticación con API key válida."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        assert 'choices' in data, "Respuesta sin 'choices'"
    
    def test_auth_invalid(self):
        """Test: Rechazo de API key inválida."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": "Bearer invalid-key-12345",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [{"role": "user", "content": "Test"}]
            },
            timeout=10
        )
        
        assert resp.status_code == 401, f"Esperaba 401, obtuvo {resp.status_code}"
    
    def test_external_model(self):
        """Test: Llamada a modelo externo."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [
                    {"role": "user", "content": "¿Cuál es la capital de Chile?"}
                ],
                "max_tokens": 30
            },
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        content = data['choices'][0]['message']['content'].lower()
        assert 'santiago' in content, "Respuesta incorrecta"
    
    def test_local_model(self):
        """Test: Llamada a modelo local."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "ollama/qwen3.5:4b",
                "messages": [{"role": "user", "content": "Di 'ok'"}],
                "max_tokens": 10
            },
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        assert 'choices' in data, "Sin respuesta del modelo local"
    
    def test_streaming(self):
        """Test: Streaming SSE."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [{"role": "user", "content": "Hola"}],
                "stream": true,
                "max_tokens": 20
            },
            stream=True,
            timeout=30
        )
        resp.raise_for_status()
        
        # Leer al menos un chunk
        chunks = 0
        for line in resp.iter_lines():
            if line:
                chunks += 1
                if chunks >= 2:  # Al menos 2 eventos
                    break
        
        assert chunks >= 2, "No recibió eventos de streaming"
    
    def test_usage_stats(self):
        """Test: Endpoint de usage stats."""
        resp = requests.get(
            f"{self.endpoint}/usage",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10
        )
        resp.raise_for_status()
        
        data = resp.json()
        # Estructura puede variar según omniroute
        assert isinstance(data, dict), "Usage stats no es dict"
    
    def generate_report(self) -> str:
        """Genera reporte markdown."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        report = f"""
# Reporte de Validación omniroute

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Endpoint:** {self.endpoint}  
**Resultado:** {'✅ TODOS PASARON' if passed == total else f'❌ {total - passed} FALLARON'}

## Resumen

- **Tests ejecutados:** {total}
- **Exitosos:** {passed}
- **Fallidos:** {total - passed}
- **Tasa de éxito:** {(passed/total*100):.1f}%

## Detalle de Tests

"""
        
        for r in self.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            report += f"- {status} **{r.name}** ({r.duration_ms:.0f}ms)\n"
            if not r.passed:
                report += f"  - Error: `{r.error}`\n"
        
        return report

if __name__ == "__main__":
    validator = OmnirouteValidator()
    success = validator.run_all_tests()
    
    print("\n" + "="*60)
    print(validator.generate_report())
    
    # Guardar reporte
    with open("omniroute-validation-report.md", "w") as f:
        f.write(validator.generate_report())
    
    print("📄 Reporte guardado en: omniroute-validation-report.md")
    
    sys.exit(0 if success else 1)
```

### 8.2 Script Usage

```bash
# Configure environment variables
export OMNIROUTE_ENDPOINT="http://localhost:20128"
export OMNIROUTE_API_KEY="your-api-key-here"

# Run validation
python scripts/validate_omniroute.py

# View generated report
cat omniroute-validation-report.md
```

---

## 9. References

- **Complete specification:** `docs/reference/product-requirements.md` § 4.1.2
- **Security policies:** `docs/reference/security-policies.md` § 5
- **Configuration:** `.env.paths` (OMNIROUTE_ENDPOINT, OMNIROUTE_DASHBOARD)
- **Credentials:** `.env` (OMNIROUTE_API_KEY)

---

## 10. Next Steps

Once omniroute is validated:

1. ✅ Integrate omniroute with chat_views.py
2. ✅ Implement automatic fallback in chat_dispatch.py
3. ✅ Add omniroute logging to audit.py
4. ✅ Create Django dashboard for omniroute stats
5. ✅ Document API key rotation process
6. ✅ Configure alerts for quota exhaustion

---

**Validation status:**

| Level | Tests | Status |
|-------|-------|--------|
| 1. Connectivity | 2/2 | ⏳ Pending |
| 2. Authentication | 2/2 | ⏳ Pending |
| 3. Routing | 3/3 | ⏳ Pending |
| 4. Fallback | 2/2 | ⏳ Pending |
| 5. Quotas | 2/2 | ⏳ Pending |
| 6. Advanced | 3/3 | ⏳ Pending |
| 7. Integration | 2/2 | ⏳ Pending |

**TOTAL:** 0/16 completed
