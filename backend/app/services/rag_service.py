# backend/app/services/rag_service.py

import os
import json
import hashlib
from typing import TypedDict, Dict, Any, List
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import supabase


class State(TypedDict):
    question: str
    context: str
    answer: str


class RAGService:
    def __init__(
        self,
        openai_api_key: str,
        supabase_url: str,
        supabase_key: str,
    ):
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=openai_api_key,
        )
        self.supabase_admin = supabase.create_client(supabase_url, supabase_key)
        self.vectorstore = SupabaseVectorStore(
            client=self.supabase_admin,
            embedding=self.embeddings,
            table_name="documents"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        self.graph = self._build_graph()

    def ingest_pdf(self, file_path: str) -> None:
        """Ingestão de PDF mantida inalterada."""
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        splits = self.text_splitter.split_documents(docs)
        self.vectorstore.add_documents(splits)

    def get_answer(self, question: str) -> str:
        """Geração de resposta com recuperação via RPC."""
        docs = self._retrieve_docs_via_rpc(question)
        context = "\n\n".join(doc.page_content for doc in docs)
        input_state = {"question": question, "context": context}
        result = self.graph.invoke(input_state)
        return result["answer"]

    def _build_graph(self) -> Any:
        """Construção do grafo LangGraph mantida inalterada."""
        workflow = StateGraph(State)

        def rag_chain(state: State) -> Dict[str, str]:
            prompt = ChatPromptTemplate.from_template(
                """Você é um assistente útil. Responda à pergunta com base no contexto fornecido.
Se o contexto não contiver informações relevantes, diga que não sabe.

Contexto:
{context}

Pergunta: {question}"""
            )
            chain = prompt | self.llm
            response = chain.invoke(state)
            return {"answer": response.content}

        workflow.add_node("rag", rag_chain)
        workflow.set_entry_point("rag")
        workflow.add_edge("rag", END)
        return workflow.compile()

    def _embed_query(self, text: str) -> List[float]:
        """Gera embedding da query."""
        return self.embeddings.embed_query(text)

    def _search_rpc(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Busca via RPC no Supabase."""
        response = self.supabase_admin.rpc(
            "rpc_vector_search",
            {"query_vector": query_vector, "limit_count": limit},
        ).execute()
        return response.data or []

    def _normalize_match_doc(self, match: Dict[str, Any]) -> Document:
        """Normaliza resultado RPC em Document."""
        metadata_raw = match.get("metadata")
        if isinstance(metadata_raw, dict):
            metadata = dict(metadata_raw)
        elif isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw) if metadata_raw else {}
        elif metadata_raw is None:
            metadata = {}
        else:
            metadata = {}
        metadata["db_id"] = match["id"]
        metadata["similarity"] = match["similarity"]
        return Document(
            page_content=match["content"],
            metadata=metadata,
        )

    def _make_retrieval_dedup_key(self, doc: Document) -> str:
        """Gera chave para deduplicação: prioriza db_id, metadata forte, hash conteúdo."""
        db_id = doc.metadata.get("db_id")
        if db_id is not None:
            return f"db_id:{db_id}"
        # Metadata forte: source + page
        source = doc.metadata.get("source", "")
        page = doc.metadata.get("page", "")
        strong_key = f"{source}:{page}".strip()
        if strong_key:
            return f"meta:{hashlib.sha256(strong_key.encode('utf-8')).hexdigest()[:12]}"
        # Fallback: hash conteúdo
        content_hash = hashlib.sha256(doc.page_content.encode('utf-8')).hexdigest()[:20]
        return f"content:{content_hash}"

    def _retrieve_docs_via_rpc(self, question: str, k: int = 5) -> List[Document]:
        """Recuperação completa via RPC com deduplicação."""
        query_vector = self._embed_query(question)
        matches = self._search_rpc(query_vector, k)
        docs = [self._normalize_match_doc(m) for m in matches]
        # Deduplicação conservadora
        seen: Dict[str, Document] = {}
        for doc in docs:
            key = self._make_retrieval_dedup_key(doc)
            current_sim = doc.metadata.get("similarity", 0)
            if key not in seen or current_sim > seen[key].metadata.get("similarity", 0):
                seen[key] = doc
        # Ordena por similaridade descendente
        deduped = sorted(
            seen.values(),
            key=lambda d: d.metadata.get("similarity", 0),
            reverse=True,
        )
        return deduped[:k]

# Configurações de ambiente
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

# Instância exportada
rag_service = RAGService(_OPENAI_API_KEY, _SUPABASE_URL, _SUPABASE_KEY)
