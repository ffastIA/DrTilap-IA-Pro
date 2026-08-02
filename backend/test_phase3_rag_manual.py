# Arquivo: backend/test_phase3_rag_manual.py

import os
from dotenv import load_dotenv

load_dotenv()


def validate_env():
    missing = []
    if not os.getenv('OPENAI_API_KEY'):
        missing.append('OPENAI_API_KEY')
    if not os.getenv('SUPABASE_URL'):
        missing.append('SUPABASE_URL')
    if not os.getenv('SUPABASE_SERVICE_ROLE_KEY') and not os.getenv('SUPABASE_KEY'):
        missing.append('SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY')
    if missing:
        print(f'Variáveis de ambiente faltando: {", ".join(missing)}')
        raise SystemExit(1)


validate_env()

QUESTION = "Como se comporta a tilápia do nilo com dieta restritiva"

import json
from langchain_core.documents import Document

from app.services.rag_service import rag_service

# Passo 1: Validar ambiente - feito
# Passo 2: Importar rag_service - feito

# Passo 3: Confirmar graph
if not hasattr(rag_service, 'graph'):
    print('ERRO: rag_service.graph não existe')
    raise SystemExit(1)
print('rag_service.graph confirmado.')


# Passo 4: Introspecção defensiva
def safe_graph_introspection(graph):
    print('\nIntrospecção do grafo:')
    try:
        if hasattr(graph, 'get_graph'):
            g = graph.get_graph()
            if hasattr(g, 'nodes'):
                print('Nós:', list(g.nodes))
            edges = g.edges if hasattr(g, 'edges') else []
            if hasattr(edges, '__iter__'):
                print('Arestas:', list(edges)[:10])  # Limitar para depuração
            else:
                print('Arestas:', edges)
        else:
            if hasattr(graph, 'nodes'):
                print('Nós:', list(graph.nodes))
    except Exception as e:
        print(f'Introspecção limitada: {e}')


safe_graph_introspection(rag_service.graph)


# Funções auxiliares
def normalize_metadata(meta):
    if isinstance(meta, dict):
        return meta.copy()
    elif isinstance(meta, str):
        try:
            return json.loads(meta)
        except json.JSONDecodeError:
            return {}
    else:
        return {}


def safe_similarity(meta):
    norm_meta = normalize_metadata(meta)
    return norm_meta.get('similarity', 'N/A')


def safe_preview(content, max_len=100):
    if len(content) > max_len:
        return content[:max_len] + '...'
    return content


def print_document_summary(docs):
    print('\nResumo dos documentos recuperados:')
    for i, doc in enumerate(docs, 1):
        meta = normalize_metadata(doc.metadata)
        db_id = meta.get('db_id', 'N/A')
        sim = safe_similarity(meta)
        title = meta.get('title', 'N/A')
        source = meta.get('source', 'N/A')
        page = meta.get('page', 'N/A')
        content_len = len(doc.page_content)
        preview = safe_preview(doc.page_content)
        print(f'Doc {i}: db_id={db_id}, sim={sim}, title={title}, source={source}, page={page}, len={content_len}')
        print(f'Preview: {preview}\n')


# Passo 5: Executar retrieve
print('\nExecutando _retrieve_docs_via_rpc...')
docs = rag_service._retrieve_docs_via_rpc(QUESTION, k=5)
print_document_summary(docs)

# Passo 7: Executar graph.invoke raw
print('\nExecutando rag_service.graph.invoke raw...')
raw_result = rag_service.graph.invoke({"question": QUESTION})
print(f'Tipo do retorno: {type(raw_result)}')
if isinstance(raw_result, dict):
    print(f'Chaves: {list(raw_result.keys())}')
    if 'answer' in raw_result:
        print(f'Answer: {raw_result["answer"]}')
    if 'context' in raw_result:
        print('Retorno inclui "context" e "answer"')
else:
    print(raw_result)

# Preparar rastreamento
print('\nPreparando monkey patches para rastreamento...')
events = []
input_keys_log = []

# Patch graph.invoke (instância)
original_graph_invoke = rag_service.graph.invoke


def tracked_graph_invoke(input_dict):
    events.append('graph.invoke chamado')
    input_keys_log.append(list(input_dict.keys()))
    result = original_graph_invoke(input_dict)
    return result


rag_service.graph.invoke = tracked_graph_invoke

# Patch _retrieve_docs_via_rpc (instância)
original_retrieve = rag_service._retrieve_docs_via_rpc


def tracked_retrieve(question, k=5, **kwargs):
    events.append('_retrieve_docs_via_rpc chamado')
    return original_retrieve(question, k=k, **kwargs)


rag_service._retrieve_docs_via_rpc = tracked_retrieve

# Patch LLM invoke (nível da classe) — llm_generation/llm_utility são a
# mesma classe (ChatOpenAI), então isso intercepta as duas instâncias.
llm_class = type(rag_service.llm_generation)
original_llm_invoke = llm_class.invoke


def tracked_llm_invoke(self, *args, **kwargs):
    events.append('LLM.invoke ANTES')
    result = original_llm_invoke(self, *args, **kwargs)
    events.append('LLM.invoke DEPOIS')
    return result


llm_class.invoke = tracked_llm_invoke

# Passo 12: Chamar get_answer com rastreamento
print('\nExecutando rag_service.get_answer com rastreamento...')
try:
    result = rag_service.get_answer(QUESTION)
    print(f'Resposta de get_answer: {result.answer}')
    print(f'Fontes: {result.sources}')
except Exception as e:
    print(f'Erro em get_answer: {e}')

finally:
    # Restaurar originais
    rag_service.graph.invoke = original_graph_invoke
    rag_service._retrieve_docs_via_rpc = original_retrieve
    llm_class.invoke = original_llm_invoke

# Passo 13: Diagnóstico final
print('\n=== DIAGNÓSTICO FINAL ===')
print(f'Eventos na ordem: {events}')
print(f'Chaves passadas para graph.invoke: {input_keys_log}')

if not hasattr(rag_service, 'graph'):
    print('FALHA ESTRUTURAL: rag_service.graph não existe')
else:
    has_retrieve = '_retrieve_docs_via_rpc chamado' in events
    has_llm = 'LLM.invoke ANTES' in events
    retrieve_before_llm = events.index('_retrieve_docs_via_rpc chamado') < events.index(
        'LLM.invoke ANTES') if has_retrieve and has_llm else False

    if 'context' in raw_result and 'answer' in raw_result:
        print('graph.invoke raw retorna "context" e "answer": fluxo RAG básico ok')

    if has_retrieve and has_llm and retrieve_before_llm:
        print('SUCESSO: Fluxo retrieve -> generate validado (retrieve antes de LLM)')
    elif has_retrieve and not has_llm:
        print('Gargalo: Retrieval ok, mas sem chamada ao LLM')
    elif has_llm and not has_retrieve:
        print('Gargalo: LLM chamado, mas sem retrieval/orquestração')
    else:
        print('Fluxo indefinido')

    if input_keys_log and 'context' in input_keys_log[-1]:
        print('AVISO: graph.invoke em get_answer recebeu "context" pré-preenchido: fluxo híbrido possível')

print('\nTeste concluído.')

"""
# Comandos PowerShell para rodar:
# cd backend
# python test_phase3_rag_manual.py
"""