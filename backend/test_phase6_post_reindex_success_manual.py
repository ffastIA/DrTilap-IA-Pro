# backend/test_phase6_post_reindex_success_manual.py

import os
from typing import Dict, Any
from dotenv import load_dotenv

QUESTION = "Como se comporta a tilápia do nilo com dieta restritiva"
TOP_K = 5
MIN_DOCS = 1
MIN_CONTEXT_LENGTH = 300
PRINT_DOC_PREVIEWS = True
SUCCESS_TERMS = ["dieta", "restr", "feed", "restriction", "growth", "metabolism", "metabol"]


def validate_env() -> None:
    """Valida variáveis obrigatórias do .env"""
    required = ['OPENAI_API_KEY', 'SUPABASE_URL']
    missing_supabase = os.getenv('SUPABASE_SERVICE_ROLE_KEY') is None and os.getenv('SUPABASE_KEY') is None
    if missing_supabase:
        print("ERRO: Falta SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY no .env")
        raise SystemExit(1)
    for key in required:
        if not os.getenv(key):
            print(f"ERRO: Falta {key} no .env")
            raise SystemExit(1)
    print("✓ Ambiente validado com sucesso.")


def _get_rag_service():
    """Importa rag_service após carregamento do .env"""
    from app.services.rag_service import rag_service
    return rag_service


def run_retrieval(rag_service) -> Dict[str, Any]:
    """Executa retrieval e analisa resultados"""
    docs = rag_service._retrieve_docs_via_rpc(QUESTION, k=TOP_K)
    context_text = "\n\n".join(doc.page_content for doc in docs)
    docs_count = len(docs)
    context_length = len(context_text)
    docs_with_success_terms = sum(
        1 for doc in docs
        if any(term.lower() in doc.page_content.lower() for term in SUCCESS_TERMS)
    )
    doc_previews = [
        doc.page_content[:200] + "..."
        for doc in docs[:3]
    ] if PRINT_DOC_PREVIEWS else []
    return {
        'docs': docs,
        'context_text': context_text,
        'docs_count': docs_count,
        'context_length': context_length,
        'docs_with_success_terms': docs_with_success_terms,
        'doc_previews': doc_previews
    }


def print_retrieval_report(result: Dict[str, Any]) -> None:
    """Imprime relatório de retrieval"""
    print("\n" + "="*60)
    print("RELATÓRIO DE RETRIEVAL")
    print("="*60)
    print(f"Docs encontrados: {result['docs_count']}/{TOP_K}")
    print(f"Tamanho do contexto: {result['context_length']} chars")
    print(f"Docs com termos de sucesso: {result['docs_with_success_terms']}")
    if result['doc_previews']:
        print("\nPreviews dos docs:")
        for i, preview in enumerate(result['doc_previews'], 1):
            print(f"  {i}. {preview}")


def run_answer_generation(rag_service) -> Dict[str, Any]:
    """Gera resposta com RAG"""
    result = rag_service.get_answer(QUESTION)
    answer_text = result.answer
    answer_length = len(answer_text)
    return {
        'answer_text': answer_text,
        'answer_length': answer_length,
        'sources': result.sources,
    }


def print_answer_report(result: Dict[str, Any]) -> None:
    """Imprime relatório da resposta"""
    print("\n" + "="*60)
    print("RELATÓRIO DA RESPOSTA")
    print("="*60)
    print(f"Tamanho da resposta: {result['answer_length']} chars")
    print("\nResposta final:")
    print(result['answer_text'])
    print("\nFontes:")
    print(result.get('sources', []))


def print_success_summary(retrieval_result: Dict[str, Any], answer_result: Dict[str, Any]) -> None:
    """Avalia e imprime resumo de sucesso"""
    print("\n" + "="*60)
    print("RESUMO DE SUCESSO PÓS-REINDEX")
    print("="*60)

    docs_ok = retrieval_result['docs_count'] >= MIN_DOCS
    context_ok = retrieval_result['context_length'] >= MIN_CONTEXT_LENGTH
    terms_ok = retrieval_result['docs_with_success_terms'] >= 1
    answer_ok = answer_result['answer_length'] > 0

    print("Checklist:")
    print(f"  - Docs >= {MIN_DOCS}: {'✓' if docs_ok else '✗'}")
    print(f"  - Contexto >= {MIN_CONTEXT_LENGTH} chars: {'✓' if context_ok else '✗'}")
    print(f"  - Docs com termos sucesso >= 1: {'✓' if terms_ok else '✗'}")
    print(f"  - Resposta não vazia: {'✓' if answer_ok else '✗'}")

    if all([docs_ok, context_ok, terms_ok, answer_ok]):
        status = "✅ APROVADO"
    elif any([docs_ok, context_ok, terms_ok]):
        status = "⚠️  ATENÇÃO (sinais fracos)"
    else:
        status = "❌ FALHA"
    print(f"\n{status}")


def main() -> None:
    """Função principal do teste manual"""
    try:
        print("Iniciando teste pós-reindex...")
        load_dotenv()  # Carrega .env PRIMEIRO
        validate_env()  # Valida ambiente
        rag_service = _get_rag_service()  # Importa rag_service APÓS .env
        retrieval_result = run_retrieval(rag_service)
        print_retrieval_report(retrieval_result)
        answer_result = run_answer_generation(rag_service)
        print_answer_report(answer_result)
        print_success_summary(retrieval_result, answer_result)
        print("\nTeste concluído.")
    except Exception as e:
        print(f"\nERRO CRÍTICO: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

# Para executar:
# cd backend
# python test_phase6_post_reindex_success_manual.py
