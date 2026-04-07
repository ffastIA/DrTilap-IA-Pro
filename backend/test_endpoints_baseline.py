"""
TESTE BASELINE DOS ENDPOINTS - 06/04/2026
Objetivo: Validar que todos os endpoints do backend estão funcionando
"""
import asyncio
import httpx
import json
from pathlib import Path
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


class EndpointAudit:
    def __init__(self):
        self.results = []
        self.client = httpx.Client(timeout=TIMEOUT)

    def log_test(self, endpoint: str, method: str, status: int, response: dict, error: str = None):
        """Registra resultado de cada teste"""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status,
            "success": 200 <= status < 300,
            "response_sample": str(response)[:200],  # Primeiros 200 chars
            "error": error
        }
        self.results.append(result)
        symbol = "✅" if not error else "❌"
        print(f"{symbol} {endpoint} - {method} - Status {status}")

    def test_health(self):
        """GET /health - Verificar disponibilidade da API"""
        try:
            print("\n[1/4] Testando GET /health...")
            response = self.client.get(f"{BASE_URL}/health")
            self.log_test("/health", "GET", response.status_code, response.json())
        except Exception as e:
            self.log_test("/health", "GET", 0, {}, str(e))

    def test_login(self, email: str = "admin@drtilapia.com", password: str = "test123"):
        """POST /auth/login - Testar autenticação"""
        try:
            print("\n[2/4] Testando POST /auth/login...")
            payload = {"email": email, "password": password}
            response = self.client.post(
                f"{BASE_URL}/auth/login",
                json=payload
            )
            self.log_test("/auth/login", "POST", response.status_code, response.json())

            # Se sucesso, extrai token para próximos testes
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                return token
        except Exception as e:
            self.log_test("/auth/login", "POST", 0, {}, str(e))
        return None

    def test_chat(self, token: str):
        """POST /consultoria/chat - Testar RAG"""
        try:
            print("\n[3/4] Testando POST /consultoria/chat...")
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            payload = {
                "message": "Qual é a temperatura ideal para tilápia?",
                "history": []
            }
            response = self.client.post(
                f"{BASE_URL}/consultoria/chat",
                json=payload,
                headers=headers
            )
            self.log_test("/consultoria/chat", "POST", response.status_code, response.json())
        except Exception as e:
            self.log_test("/consultoria/chat", "POST", 0, {}, str(e))

    def generate_report(self):
        """Salva relatório em JSON"""
        report_dir = Path(__file__).parent.parent / "docs"
        report_dir.mkdir(exist_ok=True)

        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"endpoint_audit_report_{date_str}.json"

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n📊 Relatório salvo: {report_path}")
        return report_path

    def run_all_tests(self):
        """Executa sequência de testes"""
        print("\n" + "=" * 60)
        print("🧪 INICIANDO TESTES DE BASELINE")
        print("=" * 60)

        self.test_health()
        token = self.test_login()

        if token:
            print(f"\n✅ Token obtido: {token[:20]}...")
            self.test_chat(token)
        else:
            print("\n⚠️  Skipped chat test - Token não obtido")

        print("\n[4/4] Gerando relatório...")
        self.generate_report()

        # Resumo
        passed = sum(1 for r in self.results if r['success'])
        total = len(self.results)
        print(f"\n{'=' * 60}")
        print(f"✅ {passed}/{total} testes passaram")
        print(f"{'=' * 60}\n")

        return self.results


if __name__ == "__main__":
    audit = EndpointAudit()
    audit.run_all_tests()