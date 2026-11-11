#!/usr/bin/env python3
"""
Script de validación automática de omniroute.
Ejecuta todos los tests y genera reporte.

Uso:
    python scripts/validate_omniroute.py
    
Variables de entorno requeridas:
    OMNIROUTE_ENDPOINT: URL del gateway (default: http://localhost:20128)
    OMNIROUTE_API_KEY: API key generada por omniroute
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import time


@dataclass
class TestResult:
    """Resultado de un test individual."""
    name: str
    passed: bool
    duration_ms: float
    error: str = ""
    details: str = ""


class OmnirouteValidator:
    """Validador automatizado de omniroute."""
    
    def __init__(self):
        self.endpoint = os.getenv('OMNIROUTE_ENDPOINT', 'http://localhost:20128')
        self.api_key = os.getenv('OMNIROUTE_API_KEY')
        self.results: List[TestResult] = []
        
        if not self.api_key:
            raise ValueError(
                "❌ OMNIROUTE_API_KEY no configurada\n"
                "   Configurar con: export OMNIROUTE_API_KEY='tu-api-key'"
            )
        
        print(f"🔧 Configuración:")
        print(f"   Endpoint: {self.endpoint}")
        print(f"   API Key: {self.api_key[:8]}...{self.api_key[-4:] if len(self.api_key) > 12 else '****'}")
        print()
    
    def run_all_tests(self) -> bool:
        """Ejecuta todos los tests y retorna True si todos pasan."""
        print("🚀 Iniciando validación de omniroute...")
        print("="*70)
        print()
        
        # Nivel 1: Conectividad
        print("📡 Nivel 1: Conectividad Básica")
        self._run_and_record("T1.1 Health Check", self.test_health)
        self._run_and_record("T1.2 Dashboard Access", self.test_dashboard)
        print()
        
        # Nivel 2: Autenticación
        print("🔐 Nivel 2: Autenticación")
        self._run_and_record("T2.1 API Key Válida", self.test_auth_valid)
        self._run_and_record("T2.2 API Key Inválida", self.test_auth_invalid)
        print()
        
        # Nivel 3: Enrutamiento
        print("🎯 Nivel 3: Enrutamiento de Modelos")
        self._run_and_record("T3.1 Modelo Externo (Nous Portal)", self.test_external_model)
        self._run_and_record("T3.2 Modelo Local (Ollama)", self.test_local_model)
        self._run_and_record("T3.3 Modelo No Existente", self.test_invalid_model)
        print()
        
        # Nivel 4: Características Avanzadas
        print("⚡ Nivel 4: Características Avanzadas")
        self._run_and_record("T4.1 Streaming SSE", self.test_streaming)
        self._run_and_record("T4.2 Token Tracking", self.test_token_tracking)
        print()
        
        # Nivel 5: Monitoring
        print("📊 Nivel 5: Monitoring y Stats")
        self._run_and_record("T5.1 Usage Stats", self.test_usage_stats)
        print()
        
        # Resumen
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print("="*70)
        print(f"\n📊 Resumen: {passed}/{total} tests pasaron ({(passed/total*100):.1f}%)")
        
        if passed == total:
            print("✅ TODOS LOS TESTS PASARON")
            return True
        else:
            print(f"❌ {total - passed} TESTS FALLARON")
            print("\nTests fallidos:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.error}")
            return False
    
    def _run_and_record(self, name: str, test_func):
        """Ejecuta un test individual y registra el resultado."""
        start = time.time()
        
        try:
            details = test_func()
            duration_ms = (time.time() - start) * 1000
            
            result = TestResult(name, True, duration_ms, details=details or "")
            self.results.append(result)
            
            print(f"   ✅ {name} ({duration_ms:.0f}ms)")
            if details:
                print(f"      {details}")
        
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error = str(e)
            
            result = TestResult(name, False, duration_ms, error=error)
            self.results.append(result)
            
            print(f"   ❌ {name} ({duration_ms:.0f}ms)")
            print(f"      Error: {error}")
    
    # =========================================================================
    # Tests Nivel 1: Conectividad
    # =========================================================================
    
    def test_health(self) -> str:
        """Test: Health check endpoint."""
        resp = requests.get(f"{self.endpoint}/health", timeout=10)
        resp.raise_for_status()
        
        data = resp.json()
        status = data.get('status', 'unknown')
        
        if status not in ['ok', 'healthy', 'up']:
            raise AssertionError(f"Health status inválido: {status}")
        
        # Información adicional
        providers = data.get('providers', {})
        provider_count = len(providers)
        
        return f"Status: {status}, Providers: {provider_count}"
    
    def test_dashboard(self) -> str:
        """Test: Dashboard web accesible."""
        resp = requests.get(self.endpoint, timeout=10, allow_redirects=False)
        
        # Aceptamos 200 (página) o 302/307 (redirect a login)
        if resp.status_code not in [200, 302, 307, 401]:
            raise AssertionError(f"Dashboard inaccesible: HTTP {resp.status_code}")
        
        return f"HTTP {resp.status_code}"
    
    # =========================================================================
    # Tests Nivel 2: Autenticación
    # =========================================================================
    
    def test_auth_valid(self) -> str:
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
        if 'choices' not in data:
            raise AssertionError("Respuesta sin campo 'choices'")
        
        content = data['choices'][0]['message']['content']
        return f"Respuesta recibida: '{content[:50]}...'"
    
    def test_auth_invalid(self) -> str:
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
        
        if resp.status_code != 401:
            raise AssertionError(f"Esperaba HTTP 401, obtuvo {resp.status_code}")
        
        return "Rechazado correctamente con HTTP 401"
    
    # =========================================================================
    # Tests Nivel 3: Enrutamiento
    # =========================================================================
    
    def test_external_model(self) -> str:
        """Test: Llamada a modelo externo (Nous Portal)."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [
                    {"role": "system", "content": "Responde solo con el nombre de la ciudad."},
                    {"role": "user", "content": "¿Cuál es la capital de Chile?"}
                ],
                "max_tokens": 20,
                "temperature": 0.3
            },
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        content = data['choices'][0]['message']['content'].lower()
        
        # Validación flexible (puede responder "Santiago" o "Santiago de Chile")
        if 'santiago' not in content:
            raise AssertionError(f"Respuesta inesperada: '{content}'")
        
        model_used = data.get('model', 'unknown')
        return f"Respuesta: '{content}' | Modelo: {model_used}"
    
    def test_local_model(self) -> str:
        """Test: Llamada a modelo local (Ollama)."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "ollama/qwen3.5:4b",
                "messages": [{"role": "user", "content": "Responde solo: 'ok'"}],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        if 'choices' not in data:
            raise AssertionError("Sin respuesta del modelo local")
        
        content = data['choices'][0]['message']['content']
        model_used = data.get('model', 'unknown')
        
        return f"Respuesta: '{content}' | Modelo: {model_used}"
    
    def test_invalid_model(self) -> str:
        """Test: Manejo de modelo no existente."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "invalid-provider/invalid-model-xyz",
                "messages": [{"role": "user", "content": "Test"}]
            },
            timeout=10
        )
        
        # Esperamos error 400 (Bad Request) o 404 (Not Found)
        if resp.status_code not in [400, 404, 422]:
            raise AssertionError(
                f"Esperaba HTTP 400/404/422, obtuvo {resp.status_code}"
            )
        
        return f"Rechazado correctamente con HTTP {resp.status_code}"
    
    # =========================================================================
    # Tests Nivel 4: Avanzado
    # =========================================================================
    
    def test_streaming(self) -> str:
        """Test: Streaming SSE."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [{"role": "user", "content": "Cuenta del 1 al 3"}],
                "stream": True,
                "max_tokens": 30
            },
            stream=True,
            timeout=30
        )
        resp.raise_for_status()
        
        # Leer chunks de streaming
        chunks = 0
        for line in resp.iter_lines():
            if line:
                chunks += 1
                if chunks >= 3:  # Al menos 3 eventos
                    break
        
        if chunks < 2:
            raise AssertionError(f"Solo recibió {chunks} chunks, esperaba >= 2")
        
        return f"{chunks} chunks recibidos"
    
    def test_token_tracking(self) -> str:
        """Test: Tracking de tokens en respuesta."""
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nous-ai/solar-mini-4",
                "messages": [{"role": "user", "content": "Escribe 3 líneas"}],
                "max_tokens": 50
            },
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        usage = data.get('usage', {})
        
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        if not all([prompt_tokens, completion_tokens, total_tokens]):
            raise AssertionError("Faltan campos de usage en respuesta")
        
        if total_tokens != prompt_tokens + completion_tokens:
            raise AssertionError("Conteo de tokens incoherente")
        
        return f"Tokens: {prompt_tokens} + {completion_tokens} = {total_tokens}"
    
    # =========================================================================
    # Tests Nivel 5: Monitoring
    # =========================================================================
    
    def test_usage_stats(self) -> str:
        """Test: Endpoint de usage stats."""
        resp = requests.get(
            f"{self.endpoint}/usage",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10
        )
        
        # Algunos omniroute pueden no tener este endpoint
        if resp.status_code == 404:
            return "Endpoint /usage no disponible (ok)"
        
        resp.raise_for_status()
        
        data = resp.json()
        if not isinstance(data, dict):
            raise AssertionError("Usage stats no es un diccionario")
        
        # Intentar extraer información si está disponible
        total_requests = data.get('total_requests', '?')
        total_tokens = data.get('total_tokens', '?')
        
        return f"Requests: {total_requests}, Tokens: {total_tokens}"
    
    # =========================================================================
    # Generación de Reporte
    # =========================================================================
    
    def generate_report(self) -> str:
        """Genera reporte markdown detallado."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        success_rate = (passed/total*100) if total > 0 else 0
        
        # Determinar status general
        if passed == total:
            overall_status = "✅ TODOS PASARON"
            status_emoji = "✅"
        elif passed >= total * 0.7:
            overall_status = f"⚠️ PARCIALMENTE OK ({total - passed} fallidos)"
            status_emoji = "⚠️"
        else:
            overall_status = f"❌ MÚLTIPLES FALLOS ({total - passed} fallidos)"
            status_emoji = "❌"
        
        report = f"""# Reporte de Validación omniroute

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Endpoint:** `{self.endpoint}`  
**Status:** {overall_status}

---

## 📊 Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Tests ejecutados | {total} |
| Exitosos | {passed} {status_emoji} |
| Fallidos | {total - passed} |
| Tasa de éxito | {success_rate:.1f}% |
| Duración promedio | {sum(r.duration_ms for r in self.results) / total:.0f} ms |

---

## 📋 Detalle de Tests

"""
        
        # Agrupar por nivel
        levels = {
            "Nivel 1: Conectividad": ["T1."],
            "Nivel 2: Autenticación": ["T2."],
            "Nivel 3: Enrutamiento": ["T3."],
            "Nivel 4: Avanzado": ["T4."],
            "Nivel 5: Monitoring": ["T5."],
        }
        
        for level_name, prefixes in levels.items():
            level_tests = [r for r in self.results if any(r.name.startswith(p) for p in prefixes)]
            if not level_tests:
                continue
            
            report += f"\n### {level_name}\n\n"
            
            for r in level_tests:
                status = "✅ PASS" if r.passed else "❌ FAIL"
                report += f"- **{status}** {r.name} `{r.duration_ms:.0f}ms`\n"
                
                if r.details:
                    report += f"  - {r.details}\n"
                
                if not r.passed:
                    report += f"  - ❌ Error: `{r.error}`\n"
        
        # Recomendaciones
        report += "\n---\n\n## 💡 Recomendaciones\n\n"
        
        if passed == total:
            report += "✅ Todos los tests pasaron. omniroute está funcionando correctamente.\n\n"
            report += "**Próximos pasos:**\n"
            report += "1. Integrar con superHarry (chat_views.py)\n"
            report += "2. Configurar fallback chains en omniroute dashboard\n"
            report += "3. Establecer alertas de quota\n"
        else:
            report += "⚠️ Se encontraron problemas. Revisar:\n\n"
            
            # Análisis de fallos
            failed = [r for r in self.results if not r.passed]
            
            if any('T1.' in r.name for r in failed):
                report += "- **Conectividad:** Verificar que omniroute esté corriendo (`systemctl status omniroute`)\n"
            
            if any('T2.' in r.name for r in failed):
                report += "- **Autenticación:** Revisar OMNIROUTE_API_KEY en `.env`\n"
            
            if any('T3.' in r.name for r in failed):
                report += "- **Modelos:** Verificar configuración de proveedores en omniroute dashboard\n"
            
            if any('ollama' in r.error.lower() for r in failed):
                report += "- **Ollama:** Verificar que Ollama esté corriendo y modelo descargado (`ollama list`)\n"
        
        report += "\n---\n\n## 📚 Referencias\n\n"
        report += "- **Plan completo:** `docs/omniroute-validation-plan.md`\n"
        report += "- **Configuración:** `.env.paths` (OMNIROUTE_ENDPOINT)\n"
        report += "- **Dashboard:** " + self.endpoint + "\n"
        
        return report


def main():
    """Punto de entrada principal."""
    try:
        validator = OmnirouteValidator()
        success = validator.run_all_tests()
        
        # Generar reporte
        report = validator.generate_report()
        
        # Mostrar resumen
        print("\n" + "="*70)
        print("\n📄 Generando reporte...")
        
        # Guardar reporte
        report_path = "omniroute-validation-report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"✅ Reporte guardado en: {report_path}")
        print()
        
        # Mostrar conclusión
        if success:
            print("✅ VALIDACIÓN EXITOSA - omniroute está funcionando correctamente")
            sys.exit(0)
        else:
            print("❌ VALIDACIÓN FALLÓ - Revisar reporte para detalles")
            sys.exit(1)
    
    except ValueError as e:
        print(f"\n❌ Error de configuración:\n{e}\n")
        sys.exit(2)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Validación interrumpida por el usuario")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
