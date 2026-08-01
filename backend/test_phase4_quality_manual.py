# Teste manual Fase 4 - Diagnóstico de qualidade contexto/resposta

import os
from dotenv import load_dotenv

load_dotenv()


def validate_env():
    # Valida variáveis de ambiente obrigatórias
    required_vars = ['OPENAI_API_KEY']
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise ValueError(f'Variáveis ausentes: {", ".join(missing)}')


validate_env()

try:
    from app.services.rag_service import rag_service
except ImportError as e:
    print(f'Erro no import de rag_service: {e}')
    exit(1)

from typing import List, Dict, Any
from langchain_core.documents import Document

QUESTION = 'Como se comporta a tilápia do nilo com dieta restritiva'


def normalize_text(text: str) -> str:
    # Normaliza texto: minúsculo, remove pontuação
    return ''.join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()


def extract_question_terms(question: str) -> set[str]:
    # Extrai termos únicos da pergunta
    return set(normalize_text(question).split())


def safe_preview(text: str, max_len: int = 150) -> str:
    # Preview seguro do texto
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '...'


def normalize_metadata(doc: Document) -> str:
    # Formata metadados
    meta = doc.metadata
    return f"ID:{meta.get('id', 'N/A')}, Fonte:{meta.get('source', 'N/A')}, Página:{meta.get('page', 'N/A')}"


def print_document_summary(docs: List[Document]) -> None:
    # Imprime resumo estruturado dos documentos
    print('Resumo dos Documentos Recuperados:')
    for i, doc in enumerate(docs, 1):
        print(f'\nDoc {i}:')
        print(f'  Metadados: {normalize_metadata(doc)}')
        print(f'  Preview: {safe_preview(doc.page_content)}')


def safe_similarity(a_terms: str, b_text: str) -> float:
    # Similaridade Jaccard simples
    set_a = set(normalize_text(a_terms).split())
    set_b = set(normalize_text(b_text).split())
    if not set_a:
        return 0.0
    return len(set_a & set_b) / len(set_a)


def analyze_context_coverage(question_terms: set[str], context: str) -> Dict[str, Any]:
    # Analisa cobertura de termos no contexto
    paras = context.split('\n\n')  # Calculado fora de f-strings
    para_count = len(paras)
    coverage_per_para = []
    term_hits: Dict[str, List[int]] = {term: [] for term in question_terms}

    for i, para in enumerate(paras):
        para_norm = normalize_text(para)
        sim = safe_similarity(' '.join(question_terms), para)
        coverage_per_para.append(sim)
        for term in question_terms:
            if term in para_norm:
                term_hits[term].append(i + 1)

    avg_coverage = sum(coverage_per_para) / para_count if para_count else 0.0
    covered_terms = sum(1 for hits in term_hits.values() if hits)
    term_coverage = covered_terms / len(question_terms) if question_terms else 0.0

    print('\nAnálise de Cobertura do Contexto:')
    print(f'  Número de parágrafos: {para_count}')
    print(f'  Cobertura média por parágrafo: {avg_coverage:.2%}')
    print(f'  Termos da pergunta cobertos: {term_coverage:.2%} ({covered_terms}/{len(question_terms)})')
    print('  Ocorrências por termo:')
    for term, hits in sorted(term_hits.items()):
        print(f"    '{term}': parágrafos {hits}")

    return {
        'para_count': para_count,
        'avg_coverage': avg_coverage,
        'term_coverage': term_coverage,
        'term_hits': term_hits
    }


def print_final_diagnostic(
    graph_response: Dict[str, Any],
    answer_response: str,
    coverage: Dict[str, Any]
) -> None:
    # Emite diagnóstico heurístico final
    graph_ans = graph_response.get('answer', graph_response.get('response', 'N/A'))
    print('\nDiagnóstico Final:')
    print(f'  Resposta Graph: {safe_preview(graph_ans)}')
    print(f'  Resposta get_answer: {safe_preview(answer_response)}')

    sim_graph = safe_similarity(QUESTION, graph_ans)
    sim_answer = safe_similarity(QUESTION, answer_response)
    print(f'  Similaridade Graph vs Pergunta: {sim_graph:.2%}')
    print(f'  Similaridade get_answer vs Pergunta: {sim_answer:.2%}')
    print(f'  Qualidade Contexto (cobertura termos): {coverage["term_coverage"]:.2%}')

    if coverage['term_coverage'] > 0.7 and min(sim_graph, sim_answer) > 0.4:
        status = 'BOM - Contexto cobre termos chave, respostas relevantes.'
    elif coverage['term_coverage'] > 0.4:
        status = 'MEDIANO - Cobertura parcial, verificar refinamentos RAG.'
    else:
        status = 'RUIM - Contexto insuficiente, revisar retrieval/indexação.'

    print(f'  Status Geral: {status}')


if __name__ == '__main__':
    print('Iniciando teste manual Fase 4 - Qualidade Contexto/Resposta')
    print(f'Pergunta: {QUESTION}')

    print('\nRecuperando documentos (k=5)...')
    docs: List[Document] = rag_service._retrieve_docs_via_rpc(QUESTION, k=5)

    print_document_summary(docs)

    context = '\n\n'.join(doc.page_content for doc in docs)
    print(f'\nContexto montado: {len(context)} caracteres')

    question_terms = extract_question_terms(QUESTION)
    print(f'Termos extraídos: {question_terms}')
    coverage = analyze_context_coverage(question_terms, context)

    print('\nExecutando Graph RAG...')
    graph_response = rag_service.graph.invoke({'question': QUESTION})

    print('\nExecutando get_answer...')
    answer_result = rag_service.get_answer(QUESTION)
    answer_response = answer_result.answer
    print(f'Fontes: {answer_result.sources}')

    print_final_diagnostic(graph_response, answer_response, coverage)
    print('\nTeste concluído.')