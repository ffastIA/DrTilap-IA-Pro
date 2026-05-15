# backend/test_phase6_clean_reindex_preview_manual.py
import os
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv
from app.services.clean_reindex_service import CleanReindexService

# Configurações obrigatórias
FILE_PATH = r"C:\Users\usuario\Python\DrTilapIA\backend\docs\BIP 2024 publicado.pdf"  # Ajuste para o caminho real do arquivo
ORIGINAL_FILE_NAME =  None
STORAGE_BUCKET =  None
STORAGE_PATH =  None
SOURCE = r"C:\Users\usuario\AppData\Local\Temp\tmpgvop9xdp.pdf"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MIN_EXPECTED_PAGES_KEPT = 1
MIN_EXPECTED_CHUNKS_KEPT = 1
PRINT_FULL_REPORT = False


def validate_env() -> None:
    """Valida variáveis de ambiente."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERRO: OPENAI_API_KEY não configurado.")
        sys.exit(1)
    if not os.getenv("SUPABASE_URL"):
        print("ERRO: SUPABASE_URL não configurado.")
        sys.exit(1)
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_key:
        print("ERRO: SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY não configurado.")
        sys.exit(1)


def validate_config() -> None:
    """Valida arquivo e parâmetros de chunking."""
    if not os.path.isfile(FILE_PATH):
        print(f"ERRO: Arquivo não encontrado: {FILE_PATH}")
        sys.exit(1)
    if CHUNK_SIZE <= 0:
        print("ERRO: CHUNK_SIZE deve ser > 0.")
        sys.exit(1)
    if CHUNK_OVERLAP < 0 or CHUNK_OVERLAP >= CHUNK_SIZE:
        print("ERRO: 0 <= CHUNK_OVERLAP < CHUNK_SIZE.")
        sys.exit(1)


def build_service() -> CleanReindexService:
    """Instancia CleanReindexService."""
    return CleanReindexService(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    )


def run_preview(service: CleanReindexService) -> Dict[str, Any]:
    """Executa preview sem alterar banco."""
    return service.preview_clean_reindex(
        file_path=FILE_PATH,
        original_file_name=ORIGINAL_FILE_NAME,
        storage_bucket=STORAGE_BUCKET,
        storage_path=STORAGE_PATH,
        source=SOURCE,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )


def print_report(report: Dict[str, Any]) -> None:
    """Imprime relatório resumido ou completo."""
    if PRINT_FULL_REPORT:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    print("=== Relatório Preview ===")
    print(f"  Sucesso: {report.get('success', False)}")
    print(f"  Modo: {report.get('mode', 'N/A')}")
    print(f"  Arquivo: {report.get('file_path', 'N/A')}")
    print(f"  Páginas carregadas: {report.get('pages_loaded', 0)}")
    print(f"  Páginas mantidas: {report.get('pages_kept', 0)}")
    print(f"  Páginas descartadas: {report.get('pages_discarded', 0)}")
    print(f"  Chunks gerados: {report.get('chunks_generated', 0)}")
    print(f"  Chunks mantidos: {report.get('chunks_kept', 0)}")
    print(f"  Chunks descartados: {report.get('chunks_discarded', 0)}")
    print(f"  Candidatos a deletar: {report.get('candidate_delete_count', 0)}")
    print(f"  Duração: {report.get('duration_seconds', 0):.2f}s")
    print(f"  Estratégia: {report.get('identification_strategy', 'N/A')}")
    sample_previews = report.get('sample_previews', [])
    if sample_previews:
        print("  Amostras (primeiras 3):")
        for i, sample in enumerate(sample_previews[:3]):
            print(f"    {i+1}: {str(sample)[:100]}...")
    print(f"  Mensagem: {report.get('message', 'N/A')}")


def print_validation_summary(report: Dict[str, Any]) -> None:
    """Valida métricas mínimas."""
    print("\n=== Resumo de Validação ===")
    if not report.get("success", False):
        print("FALHA")
        return
    pages_kept = report.get("pages_kept", 0)
    chunks_kept = report.get("chunks_kept", 0)
    pages_ok = pages_kept >= MIN_EXPECTED_PAGES_KEPT
    chunks_ok = chunks_kept >= MIN_EXPECTED_CHUNKS_KEPT
    if pages_ok and chunks_ok:
        print("APROVADO")
    else:
        print("ATENÇÃO")
        if not pages_ok:
            print(f"  Páginas: {pages_kept} < {MIN_EXPECTED_PAGES_KEPT}")
        if not chunks_ok:
            print(f"  Chunks: {chunks_kept} < {MIN_EXPECTED_CHUNKS_KEPT}")


def main() -> None:
    """Fluxo principal."""
    load_dotenv()
    validate_env()
    validate_config()
    service = build_service()
    print("Executando preview da reindexação limpa...")
    report = run_preview(service)
    print_report(report)
    print_validation_summary(report)
    if not report.get("success", False):
        sys.exit(1)
    print("\nPreview concluído com sucesso!")


if __name__ == "__main__":
    main()

# Comandos PowerShell:
# cd backend
# python test_phase6_clean_reindex_preview_manual.py