# backend/scripts/manual_clean_reindex.py

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from app.services.clean_reindex_service import CleanReindexService

# Constantes de configuração
ORIGINAL_FILE_NAME = None
STORAGE_BUCKET = None
STORAGE_PATH = None
SOURCE = r"C:\Users\usuario\AppData\Local\Temp\tmpgvop9xdp.pdf"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
PRINT_FULL_REPORT = False


def print_error_and_exit(message: str, details: str | None = None) -> None:
    """Imprime erro e encerra com código 1."""
    print(f"\n❌ ERRO: {message}", file=sys.stderr)
    if details:
        print(f"Detalhes: {details}", file=sys.stderr)
    sys.exit(1)


def validate_env() -> None:
    """Valida variáveis de ambiente obrigatórias."""
    keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
    }
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_key:
        print_error_and_exit("Faltando SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY")
    for name, value in keys.items():
        if not value:
            print_error_and_exit(f"Faltando variável de ambiente: {name}")


def validate_script_config(file_path: str) -> None:
    """Valida configuração do script e existência do arquivo."""
    if not Path(file_path).exists():
        print_error_and_exit("Arquivo não encontrado", file_path)
    if CHUNK_SIZE <= 0:
        print_error_and_exit("CHUNK_SIZE deve ser > 0")
    if CHUNK_OVERLAP < 0 or CHUNK_OVERLAP >= CHUNK_SIZE:
        print_error_and_exit("CHUNK_OVERLAP deve ser >= 0 e < CHUNK_SIZE")


def build_service() -> CleanReindexService:
    """Instancia o CleanReindexService com envs."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    return CleanReindexService(
        openai_api_key=openai_api_key,
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )


def build_request_payload(args: argparse.Namespace) -> dict:
    """Monta payload para o serviço."""
    return {
        "file_path": args.file_path,
        "original_file_name": ORIGINAL_FILE_NAME,
        "storage_bucket": STORAGE_BUCKET,
        "storage_path": STORAGE_PATH,
        "source": SOURCE,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }


def print_operation_header(operation: str, payload: dict) -> None:
    """Imprime cabeçalho da operação."""
    print(f"\n{'='*80}")
    print(f"OPERAÇÃO: {operation.upper()}")
    print(f"File Path: {payload['file_path']}")
    print(f"Original File Name: {payload['original_file_name']}")
    print(f"Storage Bucket: {payload['storage_bucket']}")
    print(f"Storage Path: {payload['storage_path']}")
    print(f"Source: {payload['source']}")
    print(f"Chunk Size: {payload['chunk_size']}")
    print(f"Chunk Overlap: {payload['chunk_overlap']}")
    print(f"{'='*80}\n")


def print_operation_report(report: dict) -> None:
    """Imprime relatório da operação."""
    if PRINT_FULL_REPORT:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Success: {report.get('success', False)}")
        print(f"Mode: {report.get('mode', 'N/A')}")
        print(f"File Path: {report.get('file_path', 'N/A')}")
        print(f"Pages Loaded: {report.get('pages_loaded', 0)}")
        print(f"Pages Kept: {report.get('pages_kept', 0)}")
        print(f"Pages Discarded: {report.get('pages_discarded', 0)}")
        print(f"Chunks Generated: {report.get('chunks_generated', 0)}")
        print(f"Chunks Kept: {report.get('chunks_kept', 0)}")
        print(f"Chunks Discarded: {report.get('chunks_discarded', 0)}")
        print(f"Candidate Delete Count: {report.get('candidate_delete_count', 0)}")
        print(f"Vectors Deleted: {report.get('vectors_deleted', 0)}")
        print(f"Vectors Inserted: {report.get('vectors_inserted', 0)}")
        print(f"Duration Seconds: {report.get('duration_seconds', 0):.2f}")
        print(f"Identification Strategy: {report.get('identification_strategy', 'N/A')}")
        print(f"Message: {report.get('message', 'N/A')}")


def run_preview(service: CleanReindexService, payload: dict) -> dict:
    """Executa preview."""
    return service.preview_clean_reindex(**payload)


def run_execution(service: CleanReindexService, payload: dict) -> dict:
    """Executa operação real."""
    return service.reindex_file_clean(**payload, dry_run=False)


def main() -> None:
    """Função principal."""
    load_dotenv()

    # Valida ambiente
    validate_env()

    # Parse argumentos
    parser = argparse.ArgumentParser(description="Script para preview ou execução de clean e reindex.")
    parser.add_argument("--file-path", required=True, help="Caminho para o arquivo PDF.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preview", action="store_true", help="Executar apenas preview (dry-run).")
    group.add_argument("--execute", action="store_true", help="Executar a operação real.")
    args = parser.parse_args()

    # Valida config
    validate_script_config(args.file_path)

    # Monta serviço e payload
    service = build_service()
    payload = build_request_payload(args)

    # Imprime cabeçalho
    operation = "PREVIEW" if args.preview else "EXECUTE"
    print_operation_header(operation, payload)

    # Executa
    if args.preview:
        report = run_preview(service, payload)
    else:
        report = run_execution(service, payload)

    # Imprime relatório
    print_operation_report(report)

    # Verifica sucesso
    if not report.get("success", False):
        print_error_and_exit("Operação falhou", report.get("message", "Erro desconhecido"))


if __name__ == "__main__":
    main()

# Comandos PowerShell de exemplo:
# cd backend
# python scripts/manual_clean_reindex.py --file-path "C:\Users\usuario\Python\DrTilapIA\backend\docs\BIP 2024 publicado.pdf" --preview
# python scripts/manual_clean_reindex.py --file-path "C:\Users\usuario\Python\DrTilapIA\backend\docs\BIP 2024 publicado.pdf" --execute
