# backend/app/services/rag_service.py

import os
# 'os': módulo padrão do Python para acessar variáveis de ambiente (getenv),
# essencial para configuração segura via .env

import json
# 'json': biblioteca padrão para serialização/deserialização de dados JSON,
# usada para parse de metadata armazenada como string no Supabase

import hashlib
# 'hashlib': biblioteca padrão para funções de hash criptográficas (SHA256),
# utilizada na estratégia de deduplicação de documentos por chaves únicas

from typing import TypedDict, Dict, Any, List
# 'typing': tipos anotados para TypedDict (estado do grafo), Dict/Any/List
# para tipagem estática, melhorando legibilidade e suporte a IDEs como PyCharm

from langchain_core.documents import Document
# 'langchain_core.documents.Document': classe base para representar chunks de texto
# com page_content e metadata, usada em todo o fluxo RAG

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# 'langchain_openai': integrações com OpenAI -
# OpenAIEmbeddings: gera vetores numéricos (embeddings) de texto
# ChatOpenAI: LLM para chat/inferência com modelos como gpt-4o-mini

from langchain_text_splitters import RecursiveCharacterTextSplitter
# 'RecursiveCharacterTextSplitter': divide documentos em chunks semânticos,
# respeitando chunk_size e overlap para melhor recuperação

from langchain_community.vectorstores import SupabaseVectorStore
# 'SupabaseVectorStore': vectorstore para Supabase (PostgreSQL + pgvector),
# suporta add_documents (ingestão com embedding auto) e integração RPC

from langchain_community.document_loaders import PyPDFLoader
# 'PyPDFLoader': loader específico para extrair texto de arquivos PDF,
# preservando metadata como source e page

from langchain_core.prompts import ChatPromptTemplate
# 'ChatPromptTemplate': template parametrizável para prompts de LLM,
# injeta {context} e {question} de forma segura

from langgraph.graph import StateGraph, END
# 'langgraph.graph': framework para workflows stateful como grafo direcionado
# StateGraph: constrói grafo com nodos/edges; END: nodo final

import supabase
# 'supabase': cliente Python oficial para Supabase, permite RPCs edge functions
# e queries no banco PostgreSQL


class State(TypedDict):
    """TypedDict que define o estado (state) propagado pelo grafo LangGraph.

    Campos obrigatórios:
    - question: str - A pergunta original formulada pelo usuário.
    - context: str - Contexto concatenado dos documentos relevantes recuperados.
    - answer: str - Resposta gerada pelo LLM com base no contexto e pergunta.

    Este estado é mutável e passado entre nodos do grafo.
    """
    question: str
    context: str
    answer: str


class RAGService:
    """Classe principal do serviço RAG (Retrieval Augmented Generation).

    Propósito:
    - Gerenciar ingestão de documentos PDF no vectorstore Supabase.
    - Realizar retrieval semântico via embeddings OpenAI + RPC customizada.
    - Gerar respostas contextuais usando LLM (gpt-4o-mini) via grafo LangGraph.
    - Implementar deduplicação robusta e ordenação por similaridade.

    É um singleton exportado, inicializado com variáveis de ambiente.
    Compatível com fluxos assíncronos/síncronos.
    """

    def __init__(
        self,
        openai_api_key: str,
        supabase_url: str,
        supabase_key: str,
    ):
        """Inicializa todos os componentes do serviço RAG.

        Configurações detalhadas:
        - self.embeddings: OpenAIEmbeddings com API key para geração de vetores (1536 dims).
        - self.llm: ChatOpenAI (gpt-4o-mini, temp=0 para respostas determinísticas).
        - self.supabase_admin: Cliente Supabase com service role key para RPCs admin.
        - self.vectorstore: SupabaseVectorStore na tabela 'documents' para ingestão.
                           Nota: retrieval usa RPC custom, não similarity_search.
        - self.text_splitter: RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
                             para chunks semânticos otimizados.
        - self.graph: Grafo LangGraph compilado para fluxo RAG (prompt + LLM).
        """
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        # Gera embeddings de query e documentos implicitamente no vectorstore
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=openai_api_key,
        )
        # LLM leve e preciso para RAG, temp=0 evita alucinações
        self.supabase_admin = supabase.create_client(supabase_url, supabase_key)
        # Cliente com permissões elevadas para RPC 'rpc_vector_search'
        self.vectorstore = SupabaseVectorStore(
            client=self.supabase_admin,
            embedding=self.embeddings,
            table_name="documents"
        )
        # Usado apenas para ingestão (add_documents gera embeddings e insere)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        # Estratégia recursiva: prioriza parágrafos/sentences para coesão
        self.graph = self._build_graph()
        # Grafo para orquestração stateful do RAG

    def ingest_pdf(self, file_path: str) -> None:
        """Ingestão completa de PDF no vectorstore Supabase.

        Fluxo passo a passo:
        1. Carrega o PDF extraindo texto e metadata (source, page) com PyPDFLoader.
        2. Divide os documentos em chunks menores com self.text_splitter.
        3. Adiciona os splits ao vectorstore: gera embeddings automaticamente,
           insere na tabela 'documents' com metadata JSON.

        Não altera lógica: idempotente se chunks duplicados (sem dedup aqui).
        """
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        splits = self.text_splitter.split_documents(docs)
        self.vectorstore.add_documents(splits)
        # Embeddings gerados e armazenados via SupabaseVectorStore

    def get_answer(self, question: str) -> str:
        """Gera resposta RAG para a pergunta usando retrieval via RPC.

        Fluxo principal:
        1. Recupera top-k documentos relevantes com _retrieve_docs_via_rpc.
        2. Concatena page_content em 'context' separada por '\n\n'.
        3. Cria estado inicial {'question': question, 'context': context}.
        4. Invoca self.graph (nodo 'rag' gera prompt + LLM).
        5. Extrai e retorna result['answer'].

        Retrieval usa embeddings + RPC para eficiência e customizações Supabase.
        """
        docs = self._retrieve_docs_via_rpc(question)
        context = "\n\n".join(doc.page_content for doc in docs)
        input_state = {"question": question, "context": context}
        result = self.graph.invoke(input_state)
        return result["answer"]

    def _build_graph(self) -> Any:
        """Constrói e compila o grafo LangGraph para o workflow RAG.

        Estrutura do grafo:
        - StateGraph(State): usa TypedDict State.
        - Nodo 'rag': função rag_chain (prompt template + LLM).
        - Entry point: 'rag'.
        - Edge único: 'rag' -> END (fluxo linear simples).
        - Retorna grafo compilado para invoke.

        Mantém simplicidade: pode expandir para conditional edges no futuro.
        """
        workflow = StateGraph(State)

        def rag_chain(state: State) -> Dict[str, str]:
            """Nodo do grafo: gera resposta com prompt contextualizado."""
            prompt = ChatPromptTemplate.from_template(
                """Você é um assistente útil. Responda à pergunta com base no contexto fornecido.
Se o contexto não contiver informações relevantes, diga que não sabe.

Contexto:
{context}

Pergunta: {question}"""
            )
            # Prompt em PT-BR, instrui honestidade (evita alucinações)
            chain = prompt | self.llm
            # Pipe: template renderiza -> LLM gera response
            response = chain.invoke(state)
            return {"answer": response.content}
            # Atualiza apenas 'answer' no state

        workflow.add_node("rag", rag_chain)
        workflow.set_entry_point("rag")
        workflow.add_edge("rag", END)
        return workflow.compile()
        # Grafo pronto para execução stateful

    def _embed_query(self, text: str) -> List[float]:
        """Gera o embedding (vetor numérico) da query de texto.

        Usa self.embeddings (OpenAI) para consistência com embeddings dos docs.
        Retorna lista de floats (ex: 1536 dims para text-embedding-3-small).
        """
        return self.embeddings.embed_query(text)

    def _search_rpc(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Executa busca vetorial via RPC customizada no Supabase.

        Chama 'rpc_vector_search' (edge function):
        - query_vector: embedding da pergunta.
        - limit_count: número máx de matches.
        Retorna lista de dicts com 'id', 'content', 'metadata', 'similarity'
        ou [] se vazio.

        Vantagem: permite filtros/indexação custom no Supabase (pgvector).
        """
        response = self.supabase_admin.rpc(
            "rpc_vector_search",
            {"query_vector": query_vector, "limit_count": limit},
        ).execute()
        return response.data or []
        # .data é lista de matches ordenados por similaridade

    def _normalize_match_doc(self, match: Dict[str, Any]) -> Document:
        """Normaliza resultado de match da RPC em Document LangChain.

        Processamento de metadata flexível:
        - Se dict: copia diretamente.
        - Se str: parse JSON (ou {} se vazio).
        - Se None/outros: {} vazio.
        - Adiciona 'db_id' (chave primária) e 'similarity' (score cosine).

        Garante compatibilidade com variações de storage no Supabase.
        """
        metadata_raw = match.get("metadata")
        if isinstance(metadata_raw, dict):
            metadata = dict(metadata_raw)  # Já é dict, faz cópia rasa
        elif isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw) if metadata_raw else {}  # Parse JSON
        elif metadata_raw is None:
            metadata = {}  # Sem metadata
        else:
            metadata = {}  # Fallback para tipos inesperados
        metadata["db_id"] = match["id"]
        # ID único do chunk no banco
        metadata["similarity"] = match["similarity"]
        # Score de similaridade (0-1, cosine sim)
        return Document(
            page_content=match["content"],
            metadata=metadata,
        )

    def _make_retrieval_dedup_key(self, doc: Document) -> str:
        """Gera chave única para deduplicação conservadora de documentos.

        Estratégia hierárquica (prioridades):
        1. db_id presente: 'db_id:{id}' - mais preciso, único no banco.
        2. Metadata forte (source + page): hash SHA256[:12] prefix 'meta:'
           - Útil para PDFs multi-página.
        3. Fallback: hash SHA256 do page_content[:20] prefix 'content:'
           - Evita duplicatas exatas de texto.

        Garante unicidade sem colisões, priorizando identidade forte.
        """
        db_id = doc.metadata.get("db_id")
        if db_id is not None:
            return f"db_id:{db_id}"
        # Prioridade máxima: ID do banco
        # Metadata forte: source + page
        source = doc.metadata.get("source", "")
        page = doc.metadata.get("page", "")
        strong_key = f"{source}:{page}".strip()
        if strong_key:
            return f"meta:{hashlib.sha256(strong_key.encode('utf-8')).hexdigest()[:12]}"
        # Hash curto para metadata composta
        # Fallback: hash conteúdo
        content_hash = hashlib.sha256(doc.page_content.encode('utf-8')).hexdigest()[:20]
        return f"content:{content_hash}"

    def _retrieve_docs_via_rpc(self, question: str, k: int = 5) -> List[Document]:
        """Recuperação semântica completa via RPC com pós-processamento.

        Fluxo detalhado:
        1. Gera embedding da question com _embed_query.
        2. Busca k matches via _search_rpc (já ordenados).
        3. Normaliza cada match em Document com _normalize_match_doc.
        4. Deduplicação: usa dict seen[key] = doc (mantém maior similarity).
        5. Ordena valores por 'similarity' descendente.
        6. Retorna top-k deduplicados.

        Estratégia de dedup conservadora evita duplicatas sem perder relevantes.
        """
        query_vector = self._embed_query(question)
        matches = self._search_rpc(query_vector, k)
        docs = [self._normalize_match_doc(m) for m in matches]
        # Lista de Documents normalizados
        # Deduplicação conservadora
        seen: Dict[str, Document] = {}
        for doc in docs:
            key = self._make_retrieval_dedup_key(doc)
            current_sim = doc.metadata.get("similarity", 0)
            if key not in seen or current_sim > seen[key].metadata.get("similarity", 0):
                seen[key] = doc
                # Substitui se maior similaridade
        # Ordena por similaridade descendente
        deduped = sorted(
            seen.values(),
            key=lambda d: d.metadata.get("similarity", 0),
            reverse=True,
        )
        return deduped[:k]
        # Garante exatamente k ou menos


# Configurações de ambiente
# Leitura das variáveis de ambiente obrigatórias para inicialização segura
# Prioriza SUPABASE_SERVICE_ROLE_KEY (admin) ou fallback SUPABASE_KEY (anon)
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Chave OpenAI para embeddings e LLM
_SUPABASE_URL = os.getenv("SUPABASE_URL")
# URL do projeto Supabase (ex: https://xyz.supabase.co)
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
# Service role para RPCs com permissões elevadas

# Instância singleton exportada
# Cria uma única instância global do RAGService, configurada com env vars
# Importe 'rag_service' em outros módulos para uso imediato
# Garante consistência e evita recriações desnecessárias
rag_service = RAGService(_OPENAI_API_KEY, _SUPABASE_URL, _SUPABASE_KEY)
