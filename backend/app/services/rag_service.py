# CAMINHO: backend/app/services/rag_service.py
import uuid
import logging
from pathlib import Path
from tempfile import gettempdir
from typing import List, Tuple, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import supabase_admin

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.supabase = supabase_admin
        self.storage_bucket = "rag-documents"
        self.embedding_batch_size = 20
        self.insert_batch_size = 20
        self.logger = logging.getLogger(__name__)

    async def ingest_pdf(self, file_path: str, filename: str, original_file_id: Optional[str] = None, cleanup_existing: bool = False) -> Dict[str, Any]:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        if original_file_id is None:
            original_file_id = str(uuid.uuid4())
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        if not chunks:
            raise ValueError("Nenhum chunk foi gerado do PDF.")
        storage_path = f"uploads/{original_file_id}/{filename}"
        with open(file_path, "rb") as f:
            self.supabase.storage.from_(self.storage_bucket).upload(storage_path, f)
        if cleanup_existing:
            await self._delete_existing_document_chunks(original_file_id)
        payloads = self._build_chunk_payloads(chunks, original_file_id, filename, self.storage_bucket, storage_path)
        await self._generate_embeddings_in_payloads(payloads)
        inserted_count = await self._insert_payload_batches(payloads)
        persisted_chunks = self._verify_persisted_chunks(original_file_id)
        if persisted_chunks <= 0:
            raise RuntimeError(f"Nenhum chunk foi persistido para original_file_id: {original_file_id}")
        return {
            "message": "PDF ingerido com sucesso",
            "original_file_id": original_file_id,
            "original_file_name": filename,
            "chunks_criados": len(chunks),
            "persisted_chunks": persisted_chunks,
            "storage_bucket": self.storage_bucket,
            "storage_path": storage_path
        }

    async def get_answer(self, question: str, chat_history: List[Tuple[str, str]]) -> Dict[str, Any]:
        query_embedding = self.embeddings.embed_query(question)
        response = self.supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_count": 5,
            "similarity_threshold": 0.7
        }).execute()
        docs = response.data or []
        normalized_docs = [self._normalize_match_doc(doc) for doc in docs]
        if not any(doc.get('content') for doc in normalized_docs):
            normalized_docs = await self._best_effort_fetch_recent_chunks(limit=5)
        context = self._build_context_from_docs(normalized_docs)
        if not context:
            return {
                "answer": "Desculpe, não encontrei conteúdo suficiente na base de conhecimento para responder à sua pergunta sobre piscicultura e tilápia.",
                "sources": []
            }
        prompt = f"""
Você é um assistente especializado em piscicultura e tilápia. Responda à pergunta do usuário com base no contexto fornecido.

Contexto:

{context}

Pergunta: {question}

Histórico do chat:

{chat_history}

Responda de forma clara e precisa.

"""
        answer = self.llm.invoke(prompt).content
        sources = [{"original_file_name": doc.get("original_file_name"), "page": doc.get("metadata", {}).get("page")} for doc in normalized_docs if doc.get("content")]
        return {
            "answer": answer,
            "sources": sources
        }

    async def reindex_file_from_storage(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        original_file_id = file_info.get("original_file_id")
        filename = file_info.get("original_file_name")
        storage_path = file_info.get("storage_path")
        temp_dir = Path(gettempdir())
        temp_file = temp_dir / filename
        try:
            with open(temp_file, "wb") as f:
                res = self.supabase.storage.from_(self.storage_bucket).download(storage_path)
                f.write(res)
            result = await self.ingest_pdf(str(temp_file), filename, original_file_id, cleanup_existing=True)
            return result
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def _build_chunk_payloads(self, chunks, original_file_id, original_file_name, storage_bucket, storage_path):
        payloads = []
        for chunk in chunks:
            payload = {
                "content": chunk.page_content,
                "metadata": chunk.metadata,
                "original_file_id": original_file_id,
                "original_file_name": original_file_name,
                "storage_bucket": storage_bucket,
                "storage_path": storage_path
            }
            payloads.append(payload)
        return payloads

    def _chunk_list(self, lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    async def _generate_embeddings_in_payloads(self, payloads):
        for batch in self._chunk_list(payloads, self.embedding_batch_size):
            contents = [p["content"] for p in batch]
            embeddings = self.embeddings.embed_documents(contents)
            for p, emb in zip(batch, embeddings):
                p["embedding"] = emb

    async def _insert_payload_batches(self, payloads):
        total_inserted = 0
        for batch in self._chunk_list(payloads, self.insert_batch_size):
            self.logger.info(f"Inserindo batch de {len(batch)} payloads")
            response = self.supabase.table("documents").insert(batch).execute()
            total_inserted += len(response.data or [])
        return total_inserted

    def _verify_persisted_chunks(self, original_file_id):
        response = self.supabase.table("documents").select("id").eq("original_file_id", original_file_id).execute()
        return len(response.data or [])

    async def _best_effort_fetch_recent_chunks(self, limit=5):
        try:
            response = self.supabase.table("documents").select("*").order("created_at", desc=True).limit(limit).execute()
            docs = response.data or []
            return [self._normalize_match_doc(doc) for doc in docs]
        except Exception as e:
            self.logger.warning(f"Falha ao buscar chunks recentes: {e}")
            return []

    async def _fetch_document_chunks_by_original_file_id(self, original_file_id):
        if original_file_id is None:
            return []
        response = self.supabase.table("documents").select("*").eq("original_file_id", original_file_id).execute()
        return response.data or []

    def _normalize_match_doc(self, doc):
        return {
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "original_file_name": doc.get("original_file_name", ""),
            "original_file_id": doc.get("original_file_id", "")
        }

    def _build_context_from_docs(self, docs):
        context_parts = []
        for doc in docs:
            content = doc.get("content", "").strip()
            if content:
                file_name = doc.get("original_file_name", "Arquivo desconhecido")
                page = self._safe_page_from_metadata(doc.get("metadata", {}))
                if page:
                    context_parts.append(f"Arquivo: {file_name}, Página: {page}\n{content}")
                else:
                    context_parts.append(f"Arquivo: {file_name}\n{content}")
        return "\n\n".join(context_parts)

    async def _delete_existing_document_chunks(self, original_file_id):
        self.supabase.table("documents").delete().eq("original_file_id", original_file_id).execute()

    def _safe_page_from_metadata(self, metadata):
        if isinstance(metadata, dict):
            page = metadata.get("page")
            if isinstance(page, int):
                return page
        return None

    def _safe_content(self, doc):
        return doc.get("content", "").strip()

rag_service = RAGService()