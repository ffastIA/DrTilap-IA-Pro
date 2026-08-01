# CAMINHO: backend/app/utils/rag_config.py
"""Configuração explícita de embedding e chunking, lida uma vez do ambiente.

Fonte única para os caminhos de ingestão — no passado, dois caminhos
divergiram silenciosamente (um usava chunk_size=4000 hardcoded, o outro não
passava `model=` ao embedding nenhum), e essa divergência é exatamente o
tipo de regressão que motivou centralizar aqui.
"""
import os

# text-embedding-3-large truncado em 1536 dims: cabe no schema vector(1536)
# e no índice HNSW existentes sem migração, e supera ada-002 e 3-small na
# mesma dimensionalidade.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

# Restaura a ordem de grandeza da versão que funcionava (1000/200), com
# folga para tabelas científicas que ficariam truncadas em 1000.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Quantidade de candidatos pedidos ao RPC de busca vetorial. Precisa escalar
# com o número de chunks por documento — chunk_size menor gera mais chunks,
# e a mesma janela k passa a cobrir uma fração menor de cada documento.
# 40 foi medido empiricamente (harness) como suficiente para igualar o
# recall da configuração anterior (chunk_size=4000/k=20) mesmo com o
# chunking mais granular atual — ver design.md de retrieval-refusal-quality.
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "40"))
RETRIEVAL_K_RETRY = int(os.getenv("RETRIEVAL_K_RETRY", "40"))

# Limiar de confiança "alta" — acima disso, os candidatos são usados sem
# ressalva. Calibrado contra a distribuição real de similaridade do golden
# set (backend/evaluation/), não escolhido a dedo: com text-embedding-3-large,
# perguntas fora do escopo pontuaram 0.512-0.629, e a pergunta respondível
# mais fraca pontuou 0.539 — não há um único valor que separe os dois grupos
# com perfeição (ver design.md, "Calibração medida"), então o valor aqui
# prioriza não recusar perguntas respondíveis à custa de deixar passar
# algumas perguntas fora do escopo na zona intermediária (ver
# REFUSAL_FLOOR_SIMILARITY). Substitui o antigo PRIMARY_RPC_SIMILARITY_THRESHOLD.
PRIMARY_RPC_SIMILARITY_THRESHOLD = float(os.getenv("PRIMARY_RPC_SIMILARITY_THRESHOLD", "0.65"))

# Piso de similaridade abaixo do qual o sistema recusa (contexto vazio) em
# vez de responder com o melhor match disponível. Entre o piso e o limiar
# acima fica a "zona fraca": todos os candidatos são mantidos (não só o
# top-1) para não sacrificar recall, mas nenhum é tratado como confiável.
# 0.53 foi calibrado para ficar abaixo da pergunta respondível mais fraca
# medida (0.539) e ainda assim recusar o caso mais claro de pergunta fora
# do escopo medido (0.512) — ver tasks.md de retrieval-refusal-quality.
REFUSAL_FLOOR_SIMILARITY = float(os.getenv("REFUSAL_FLOOR_SIMILARITY", "0.53"))


def effective_config_summary() -> str:
    return (
        f"embedding_model={EMBEDDING_MODEL} "
        f"embedding_dimensions={EMBEDDING_DIMENSIONS} "
        f"chunk_size={CHUNK_SIZE} chunk_overlap={CHUNK_OVERLAP} "
        f"retrieval_k={RETRIEVAL_K} retrieval_k_retry={RETRIEVAL_K_RETRY} "
        f"refusal_floor_similarity={REFUSAL_FLOOR_SIMILARITY}"
    )
