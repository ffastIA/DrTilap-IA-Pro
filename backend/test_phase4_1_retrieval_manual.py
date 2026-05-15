# Arquivo: backend/test_phase4_1_retrieval_manual.py
#
# Script para diagnóstico fino de retrieval na Fase 4.1 do projeto DrTilápia.
# Executa retrieval com múltiplas queries equivalentes e valores de k.
# Analisa cobertura lexical, similaridade e gera ranking comparativo.

import os
import json
from dotenv import load_dotenv

load_dotenv()


def validate_env():
    """Valida variáveis de ambiente obrigatórias."""
    required = ['OPENAI_API_KEY', 'SUPABASE_URL']
    supabase_keys = ['SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_KEY']
    missing = []

    if not os.getenv('OPENAI_API_KEY'):
        missing.append('OPENAI_API_KEY')
    if not os.getenv('SUPABASE_URL'):
        missing.append('SUPABASE_URL')
    if not any(os.getenv(key) for key in supabase_keys):
        missing.append('SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY')

    if missing:
        print('Variáveis de ambiente ausentes:', ', '.join(missing))
        print('Configure o arquivo .env e execute novamente.')
        raise SystemExit(1)


validate_env()

from app.services.rag_service import rag_service


MAIN_QUERY = "Como se comporta a tilápia do nilo com dieta restritiva"
QUERIES = [
    MAIN_QUERY,
    "tilápia do nilo restrição alimentar",
    "tilápia do nilo dieta restrita metabolismo",
    "Oreochromis niloticus under restricted diet",
    "feed restriction Oreochromis niloticus"
]
K_VALUES = [5, 8]


def get_stopwords_pt():
    """Retorna stopwords comuns em português."""
    return {
        'a', 'o', 'as', 'os', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas',
        'como', 'com', 'se', 'um', 'uma', 'e', 'ou', 'por', 'para', 'que', 'para', 'com',
        'the', 'of', 'and', 'or', 'in', 'under', 'with'
    }


def normalize_text(text):
    """Normaliza texto: lower, remove pontuação, normaliza espaços."""
    if not text:
        return ''
    text = text.lower()
    for p in '.,;:!?()[]{}':
        text = text.replace(p, ' ')
    return ' '.join(text.split())


def extract_question_terms(question):
    """Extrai termos chave da query, removendo stopwords."""
    words = normalize_text(question).split()
    stopwords = get_stopwords_pt()
    return [w for w in words if w not in stopwords and len(w) > 2]


def normalize_metadata(meta):
    """Normaliza metadata: dict -> copy, str JSON -> dict, else {}."""
    if isinstance(meta, dict):
        return meta.copy()
    elif isinstance(meta, str):
        try:
            return json.loads(meta)
        except (json.JSONDecodeError, ValueError):
            return {}
    else:
        return {}


def safe_preview(content, max_len=100):
    """Preview seguro do conteúdo."""
    if len(content) > max_len:
        return content[:max_len] + '...'
    return content


def safe_similarity(meta):
    """Extrai similaridade do metadata de forma segura."""
    norm_meta = normalize_metadata(meta)
    try:
        return float(norm_meta.get('similarity', 0.0))
    except (ValueError, TypeError):
        return 0.0


def analyze_chunk_coverage(content, terms):
    """Analisa cobertura lexical de termos no chunk."""
    if not terms:
        return 'Sem termos chave.'
    content_norm = normalize_text(content)
    found = [t for t in terms if t in content_norm]
    missing = [t for t in terms if t not in content_norm]
    found_str = ', '.join(found[:5]) + ('...' if len(found) > 5 else '')
    missing_str = ', '.join(missing[:5]) + ('...' if len(missing) > 5 else '')
    return f"Encontrados ({len(found)}/{len(terms)}): {found_str} | Ausentes: {missing_str}"


def score_document(doc, query_terms):
    """Score heurístico por documento: cobertura + similaridade."""
    content_norm = normalize_text(doc.page_content)
    coverage = sum(1 for t in query_terms if t in content_norm) / len(query_terms) if query_terms else 0.0
    sim = safe_similarity(doc.metadata)
    return 0.7 * coverage + 0.3 * sim


def summarize_run(query, k, docs, query_terms):
    """Métricas heurísticas da execução."""
    if not docs:
        return {'num_docs': 0, 'avg_sim': 0.0, 'max_sim': 0.0, 'total_coverage': 0,
                'relevant_chunks': 0, 'final_score': 0.0}

    sims = [safe_similarity(d.metadata) for d in docs]
    avg_sim = sum(sims) / len(docs)
    max_sim = max(sims)
    total_coverage = sum(sum(1 for t in query_terms if t in normalize_text(d.page_content)) for d in docs)
    relevant_chunks = sum(1 for d in docs if score_document(d, query_terms) > 0.5)
    norm_coverage = total_coverage / (len(query_terms) * len(docs)) if query_terms else 0.0
    final_score = 0.4 * avg_sim + 0.4 * norm_coverage + 0.2 * (relevant_chunks / len(docs))

    return {
        'num_docs': len(docs),
        'avg_sim': avg_sim,
        'max_sim': max_sim,
        'total_coverage': total_coverage,
        'relevant_chunks': relevant_chunks,
        'final_score': final_score
    }


def print_document_summary(docs, query_terms, k):
    """Imprime resumo estruturado dos documentos."""
    print(f"\n--- {len(docs)} documentos para k={k} ---")
    for i, doc in enumerate(docs, 1):
        norm_meta = normalize_metadata(doc.metadata)
        db_id = norm_meta.get('db_id', 'N/A')
        sim = safe_similarity(doc.metadata)
        preview = safe_preview(doc.page_content)
        coverage = analyze_chunk_coverage(doc.page_content, query_terms)
        score = score_document(doc, query_terms)
        print(f"Doc {i} (db_id: {db_id}, sim: {sim:.4f}, score: {score:.2f})")
        print(f"  Preview: {preview}")
        print(f"  Cobertura: {coverage}")


def print_final_ranking(results):
    """Imprime ranking comparativo das execuções."""
    print(f"\n{'='*70}")
    print("RANKING COMPARATIVO FINAL (ordenado por score final heurístico)")
    sorted_results = sorted(results, key=lambda x: x['final_score'], reverse=True)
    for i, res in enumerate(sorted_results, 1):
        q_short = res['query'][:60] + '...' if len(res['query']) > 60 else res['query']
        print(f"{i:2d}. '{q_short}' (k={res['k']}) | score={res['final_score']:.3f} | "
              f"avg_sim={res['avg_sim']:.3f} | docs={res['num_docs']} | rel={res['relevant_chunks']}")
    best = sorted_results[0]
    q_best_short = best['query'][:60] + '...' if len(best['query']) > 60 else best['query']
    print(f"\n*** QUERY MAIS PROMISSORA: '{q_best_short}' com k={best['k']} (score: {best['final_score']:.3f}) ***")


# Execução principal
results = []
for query in QUERIES:
    query_terms = extract_question_terms(query)
    print(f"\n{'='*60}")
    print(f"Query: '{query}'\nTermos chave: {query_terms}")

    for k in K_VALUES:
        print(f"\nExecutando retrieval com k={k}...")
        docs = rag_service._retrieve_docs_via_rpc(query, k=k)
        print_document_summary(docs, query_terms, k)

        summary = summarize_run(query, k, docs, query_terms)
        print(f"\nMétricas (k={k}): docs={summary['num_docs']}, avg_sim={summary['avg_sim']:.3f}, "
              f"max_sim={summary['max_sim']:.3f}, cobertura_total={summary['total_coverage']}, "
              f"chunks_relevantes={summary['relevant_chunks']}, score_final={summary['final_score']:.3f}")
        results.append({'query': query, 'k': k, **summary})

print_final_ranking(results)

print(f"\n{'='*60}")
print("Diagnóstico concluído. Analise os scores para decidir próximos ajustes.")

"""

# Comandos PowerShell para executar:
# cd backend
# python test_phase4_1_retrieval_manual.py

"""