# Arquivo: backend/test_phase5_chunking_reindex_manual.py

import os
import json
import re
from collections import Counter
from statistics import mean, median, stdev
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

# Configurações obrigatórias
default_k = 5
max_docs_to_print = 5
simulate_rechunk = False
source_pdf_path = None  # Defina o caminho para um PDF específico se quiser simular
alternative_splits = [(600, 120), (800, 160), (1000, 200)]

queries_diagnosticas = [
    "Como se comporta a tilápia do nilo com dieta restritiva",
    "tilápia do nilo restrição alimentar",
    "feed restriction Oreochromis niloticus"
]

pergunta_principal = queries_diagnosticas[0]

# Termos fixos de relevância para todas as queries
relevance_terms = [
    'tilápia', 'nilo', 'oreochromis', 'niloticus',
    'dieta', 'restritiva', 'restrição', 'alimentar',
    'feed', 'restriction', 'comportamento', 'behavior'
]

# Marcadores de ruído comuns
noise_markers = [
    re.compile(r'doi[:\s]*[^\s]+', re.IGNORECASE),
    re.compile(r'page\s*\d+/\d+|p\.\s*\d+', re.IGNORECASE),
    re.compile(r'1/\d+|\d+/\d+', re.IGNORECASE),
    re.compile(r'conflict of interest', re.IGNORECASE),
    re.compile(r'data availability', re.IGNORECASE),
    re.compile(r'authors?\s*contribution', re.IGNORECASE),
    re.compile(r'reference', re.IGNORECASE),
    re.compile(r'bibliograph', re.IGNORECASE),
    re.compile(r'disclaimer', re.IGNORECASE),
]


def validate_env() -> None:
    """Valida variáveis de ambiente obrigatórias."""
    required_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
    }
    supabase_keys = ['SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_KEY']
    has_supabase_key = any(os.getenv(key) for key in supabase_keys)

    missing = [var for var, val in required_vars.items() if not val]
    if not has_supabase_key:
        missing.append('SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY')

    if missing:
        print(f"ERRO: Variáveis de ambiente ausentes: {', '.join(missing)}")
        print("Configure o arquivo .env e execute novamente.")
        raise SystemExit(1)


def normalize_metadata(meta: Any) -> Dict[str, Any]:
    """Normaliza metadata para dict seguro."""
    if isinstance(meta, dict):
        return meta.copy()
    elif isinstance(meta, str):
        try:
            return json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def safe_preview(text: str, max_len: int = 150) -> str:
    """Gera preview seguro e truncado do conteúdo."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '...'


def has_noise(content: str) -> bool:
    """Detecta presença de marcadores de ruído."""
    content_lower = content.lower()
    return any(pattern.search(content_lower) for pattern in noise_markers)


def relevance_score(content: str, terms: List[str]) -> int:
    """Conta ocorrências de termos relevantes (case insensitive)."""
    content_lower = content.lower()
    return sum(1 for term in terms if term.lower() in content_lower)


def analyze_chunk_quality(doc: Any, query: str) -> Dict[str, Any]:
    """Analisa qualidade heurística de um chunk."""
    meta = normalize_metadata(doc.metadata)
    content = doc.page_content or ''
    len_content = len(content)

    db_id = meta.get('db_id')
    similarity = meta.get('similarity', 0.0)
    title = meta.get('title', 'N/A')
    source = meta.get('source', 'N/A')
    page = meta.get('page', 'N/A')

    preview = safe_preview(content)
    is_noisy = has_noise(content)
    rel_score = relevance_score(content, relevance_terms)
    is_relevant = rel_score >= 2
    heuristic_score = (rel_score * 10 - (20 if is_noisy else 0) + similarity * 50)

    print(f"  db_id: {db_id} | sim: {similarity:.3f} | len: {len_content} | noisy: {'SIM' if is_noisy else 'NÃO'} | rel_terms: {rel_score} | score: {heuristic_score:.1f}")
    print(f"    Preview: {preview}")
    print(f"    Fonte/Pág: {source}:{page} | Título: {title}")

    return {
        'db_id': db_id,
        'len': len_content,
        'noisy': is_noisy,
        'rel_score': rel_score,
        'is_relevant': is_relevant,
        'heuristic_score': heuristic_score,
        'source': source,
        'page': page,
        'similarity': similarity
    }


def print_chunk_summary(docs: List[Any], query: str) -> None:
    """Imprime resumo estruturado dos chunks para uma query."""
    print(f"\n=== Chunks recuperados para query: '{query}' (k={default_k}) ===")
    print(f"Total de chunks: {len(docs)}")
    for i, doc in enumerate(docs[:max_docs_to_print], 1):
        print(f"\nChunk {i}:")
        analyze_chunk_quality(doc, query)
    if len(docs) > max_docs_to_print:
        print(f"  ... e {len(docs) - max_docs_to_print} chunks adicionais.")


def aggregate_chunk_metrics(all_chunks: List[Any]) -> Dict[str, Any]:
    """Agrega métricas globais dos chunks analisados."""
    if not all_chunks:
        return {}

    qualities = []
    sources = []
    pages = []
    for doc in all_chunks:
        meta = normalize_metadata(doc.metadata)
        q = analyze_chunk_quality(doc, pergunta_principal)  # Reanalisa para métricas
        qualities.append(q)
        sources.append(meta.get('source', 'desconhecida'))
        pages.append(f"{meta.get('source', 'desconhecida')}:{meta.get('page', 'N/A')}")

    lengths = [q['len'] for q in qualities]
    num_chunks = len(all_chunks)
    avg_len = mean(lengths)
    min_len = min(lengths)
    max_len = max(lengths)
    very_short_count = sum(1 for l in lengths if l < 250)
    noisy_count = sum(1 for q in qualities if q['noisy'])
    relevant_count = sum(1 for q in qualities if q['is_relevant'])
    avg_rel_score = mean(q['rel_score'] for q in qualities)
    avg_heuristic = mean(q['heuristic_score'] for q in qualities)

    source_counter = Counter(sources).most_common(5)
    page_counter = Counter(pages).most_common(5)

    return {
        'num_chunks': num_chunks,
        'avg_len': avg_len,
        'min_len': min_len,
        'max_len': max_len,
        'very_short_count': very_short_count,
        'very_short_ratio': very_short_count / num_chunks,
        'noisy_count': noisy_count,
        'noisy_ratio': noisy_count / num_chunks,
        'relevant_count': relevant_count,
        'relevant_ratio': relevant_count / num_chunks,
        'avg_rel_score': avg_rel_score,
        'avg_heuristic': avg_heuristic,
        'top_sources': source_counter,
        'top_pages': page_counter
    }


def print_aggregate_report(metrics: Dict[str, Any]) -> None:
    """Imprime relatório agregado de métricas."""
    print(f"\n=== DIAGNÓSTICO AGREGADO ({metrics['num_chunks']} chunks analisados) ===")
    print(f"Tamanhos: média {metrics['avg_len']:.0f} chars (min: {metrics['min_len']}, max: {metrics['max_len']})")
    print(f"Chunks muito curtos (<250 chars): {metrics['very_short_count']} ({metrics['very_short_ratio']:.1%})")
    print(f"Chunks com ruído: {metrics['noisy_count']} ({metrics['noisy_ratio']:.1%})")
    print(f"Chunks relevantes: {metrics['relevant_count']} ({metrics['relevant_ratio']:.1%})")
    print(f"Média termos relevantes: {metrics['avg_rel_score']:.1f}")
    print(f"Média score heurístico: {metrics['avg_heuristic']:.1f}")
    print(f"Fontes mais recorrentes: {dict(metrics['top_sources'])}")
    print(f"Páginas mais recorrentes: {dict(metrics['top_pages'][:3])}")


def simulate_rechunk_if_requested() -> None:
    """Simula rechunking alternativo se configurado."""
    if not simulate_rechunk:
        print("\nSIMULATE_RECHUNK=False: pulando simulação.")
        return

    if not source_pdf_path or not os.path.exists(source_pdf_path):
        print(f"\nAVISO: SIMULATE_RECHUNK=True mas SOURCE_PDF_PATH='{source_pdf_path}' inválido. Pulando simulação.")
        return

    print(f"\n=== SIMULAÇÃO RECHUNKING com PDF: {source_pdf_path} ===")
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        loader = PyPDFLoader(source_pdf_path)
        pages = loader.load()
        print(f"PDF carregado: {len(pages)} páginas.")

        for chunk_size, chunk_overlap in alternative_splits:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            chunks = splitter.split_documents(pages)
            lengths = [len(c.page_content) for c in chunks]
            very_short = sum(1 for l in lengths if l < 250)
            print(f"  Config ({chunk_size},{chunk_overlap}): {len(chunks)} chunks, média {mean(lengths):.0f} chars, curtos: {very_short}")
            for i, chunk in enumerate(chunks[:2]):
                print(f"    Preview {i+1}: {safe_preview(chunk.page_content, 100)}")
    except ImportError as e:
        print(f"ERRO na simulação: {e}. Verifique langchain_community e langchain_text_splitters.")
    except Exception as e:
        print(f"ERRO ao carregar PDF: {e}")


def print_final_recommendations(metrics: Dict[str, Any]) -> None:
    """Emite recomendações heurísticas baseadas nas métricas."""
    print(f"\n=== RECOMENDAÇÕES TÉCNICAS PARA CHUNKING/REINDEXAÇÃO ===")
    recs = []

    if metrics.get('very_short_ratio', 0) > 0.3:
        recs.append("- Aumentar chunk_size (muitos chunks curtos).")
    elif metrics.get('avg_len', 0) > 1200:
        recs.append("- Reduzir chunk_size (chunks muito longos, risco de ruído).")

    if metrics.get('noisy_ratio', 0) > 0.4:
        recs.append("- Limpar cabeçalhos/rodapés/ruído textual antes de indexar (pré-processamento).")
        recs.append("- Filtrar chunks com marcadores de referências/disclaimers.")

    if metrics.get('relevant_ratio', 0) < 0.6:
        recs.append("- Reindexar com chunking diferente (mais overlap ou tamanhos alternativos).")
    elif metrics.get('avg_rel_score', 0) < 1.5:
        recs.append("- Aumentar overlap para melhor contexto.")

    top_sources = dict(metrics.get('top_sources', []))
    if 'references' in ' '.join(top_sources.keys()).lower() or metrics.get('noisy_ratio', 0) > 0.5:
        recs.append("- Filtrar páginas de referências/bibliografia.")

    if not recs or metrics.get('relevant_ratio', 0) > 0.8 and metrics.get('noisy_ratio', 0) < 0.2:
        recs.append("- Manter chunking atual (não parece ser o gargalo principal).")

    for rec in recs[:8]:
        print(rec)

    print("- Próximo passo: testar reindexação completa se recomendado.")


if __name__ == '__main__':
    print("Iniciando diagnóstico de chunking e reindexação - DrTilápia")
    validate_env()

    try:
        from app.services.rag_service import rag_service
    except ImportError as e:
        print(f"ERRO ao importar rag_service: {e}")
        raise SystemExit(1)

    # Imprime configuração atual do splitter
    print("\nConfiguração atual do text_splitter:")
    splitter = rag_service.text_splitter
    print(f"Classe: {type(splitter).__name__}")
    print(f"chunk_size: {getattr(splitter, 'chunk_size', 'N/A')}")
    print(f"chunk_overlap: {getattr(splitter, 'chunk_overlap', 'N/A')}")

    # Recupera e analisa chunks para cada query
    all_chunks = []
    for query in queries_diagnosticas:
        docs = rag_service._retrieve_docs_via_rpc(query, k=default_k)
        print_chunk_summary(docs, query)
        all_chunks.extend(docs)

    # Relatórios
    metrics = aggregate_chunk_metrics(all_chunks)
    print_aggregate_report(metrics)
    simulate_rechunk_if_requested()
    print_final_recommendations(metrics)

    print("\nDiagnóstico concluído.")

"""
Comandos PowerShell para executar (a partir da raiz do projeto):

cd backend
python test_phase5_chunking_reindex_manual.py

Para simular rechunking:
- Defina SIMULATE_RECHUNK = True
- Defina SOURCE_PDF_PATH = 'caminho/para/seu_arquivo.pdf'
- Reexecute

Depuração no PyCharm: defina breakpoint em analyze_chunk_quality ou aggregate_chunk_metrics.
"""