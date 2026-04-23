import uuid
import logging
from pathlib import Path
from tempfile import gettempdir
from typing import List, Tuple, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import supabase_admin
from storage3.exceptions import StorageApiError

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        self.supabase = supabase_admin
        self.storage_bucket = "rag-documents"
        self.embedding_batch_size = 20
        self.insert_batch_size = 20
        self.logger = logging.getLogger(__name__)

    def _detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return 'pt'
        words = [w.strip('.,!?;:"\'()[]{}') for w in text.lower().split() if w.strip('.,!?;:"\'()[]{}')]
        pt_words = {'o', 'a', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'é', 'com', 'não', 'na', 'os', 'no', 'as', 'dos', 'que', 'por', 'mais', 'pelo', 'pela', 'sem', 'sobre', 'este', 'esta', 'foi', 'era', 'tem', 'ser'}
        en_words = {'the', 'of', 'and', 'a', 'to', 'in', 'is', 'you', 'that', 'it', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they', 'i', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'but', 'not', 'what', 'all', 'were', 'when', 'can', 'said', 'there', 'use', 'an', 'each'}
        pt_score = sum(1 for w in words if w in pt_words)
        en_score = sum(1 for w in words if w in en_words)
        return 'pt' if pt_score > en_score else 'en'

    async def ingest_pdf(self, file_path: str, filename: str, original_file_id: Optional[str] = None, cleanup_existing: bool = False) -> Dict[str, Any]:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        if original_file_id is None:
            original_file_id = str(uuid.uuid4())
        self.logger.info(f"Iniciando ingestão do PDF: {filename}")
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        self.logger.info(f"Gerados {len(chunks)} chunks do PDF {filename}")
        if not chunks:
            raise ValueError("Nenhum chunk foi gerado do PDF.")
        full_text = " ".join(doc.page_content for doc in documents)
        document_language = self._detect_language(full_text)
        self.logger.info(f"Idioma detectado do documento {filename}: {document_language}")
        storage_path = f"uploads/{original_file_id}/{filename}"
        self._upload_file_to_storage(file_path, storage_path, overwrite=cleanup_existing)
        self.logger.info(f"PDF {filename} enviado para storage em {storage_path}")
        if cleanup_existing:
            await self._delete_existing_document_chunks(original_file_id)
        payloads = self._build_chunk_payloads(chunks, original_file_id, filename, self.storage_bucket, storage_path, document_language)
        await self._generate_embeddings_in_payloads(payloads)
        inserted_count = await self._insert_payload_batches(payloads)
        persisted_chunks = self._verify_persisted_chunks(original_file_id)
        self.logger.info(f"Persistidos {persisted_chunks} chunks para {original_file_id}")
        if persisted_chunks <= 0:
            raise RuntimeError(f"Nenhum chunk foi persistido para original_file_id: {original_file_id}")
        return {
            "message": "PDF ingerido com sucesso",
            "original_file_id": original_file_id,
            "original_file_name": filename,
            "chunks_criados": len(chunks),
            "persisted_chunks": persisted_chunks,
            "storage_bucket": self.storage_bucket,
            "storage_path": storage_path,
            "source_language": document_language,
            "multilingual_ready": True
        }

    async def get_answer(self, question: str, chat_history: List[Tuple[str, str]]) -> Dict[str, Any]:
        question_language = self._detect_language(question)
        query_embedding = self.embeddings.embed_query(question)
        response_orig = self.supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_count": 5,
            "similarity_threshold": 0.7
        }).execute()
        docs_orig = response_orig.data or []
        normalized_docs = []
        if question_language == 'pt':
            eng_prompt = f'''Traduza esta pergunta para inglês de forma precisa, concisa e otimizada para busca semântica:\n\n"{question}"\n\nResponda APENAS com a tradução em inglês, sem explicações adicionais.'''
            eng_query = self.llm.invoke(eng_prompt).content.strip()
            self.logger.info(f"Query auxiliar em inglês gerada: {eng_query}")
            eng_embedding = self.embeddings.embed_query(eng_query)
            response_eng = self.supabase.rpc("match_documents", {
                "query_embedding": eng_embedding,
                "match_count": 5,
                "similarity_threshold": 0.7
            }).execute()
            docs_eng = response_eng.data or []
            all_docs = docs_orig + docs_eng
            seen = set()
            unique_docs = []
            for doc in all_docs:
                key = f"{doc.get('original_file_id', '')}_{doc.get('metadata', {{}}).get('page', 0)}"
                if key not in seen:
                    seen.add(key)
                    unique_docs.append(doc)
            unique_docs.sort(key=lambda d: d.get('similarity', 0.0), reverse=True)
            normalized_docs = [self._normalize_match_doc(doc) for doc in unique_docs[:5]]
        else:
            normalized_docs = [self._normalize_match_doc(doc) for doc in docs_orig]
        if not any(doc.get('content') for doc in normalized_docs):
            normalized_docs = await self._best_effort_fetch_recent_chunks(limit=5)
        context = self._build_context_from_docs(normalized_docs)
        if not context:
            return {
                "answer": "Desculpe, não encontrei conteúdo suficiente na base de conhecimento para responder à sua pergunta sobre piscicultura e tilápia.",
                "sources": []
            }
        prompt = f"""

Você é um assistente especializado em piscicultura e tilápia. Responda SEMPRE em português brasileiro, de forma clara e precisa, com base no contexto fornecido.

Contexto (pode conter trechos em inglês ou português):

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
        storage_path = file_info.get("storage_path")
        if not storage_path:
            raise ValueError("storage_path ausente para reindexação")
        filename = file_info.get("original_file_name") or Path(storage_path).name
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

    def _build_chunk_payloads(self, chunks, original_file_id, original_file_name, storage_bucket, storage_path, document_language: str):
        payloads = []
        for chunk in chunks:
            source_language = self._detect_language(chunk.page_content)
            chunk_language = source_language
            metadata = dict(chunk.metadata)
            metadata.update({
                "source_language": source_language,
                "document_language": document_language,
                "chunk_language": chunk_language,
                "translation_strategy": "answer_in_ptbr"
            })
            payload = {
                "content": chunk.page_content,
                "metadata": metadata,
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
            "original_file_id": doc.get("original_file_id", ""),
            "similarity": doc.get("similarity", 0.0)
        }

    def _build_context_from_docs(self, docs):
        context_parts = []
        for doc in docs:
            content = doc.get("content", "").strip()
            if content:
                file_name = doc.get("original_file_name", "Arquivo desconhecido")
                metadata = doc.get("metadata", {})
                page = self._safe_page_from_metadata(metadata)
                lang_info = metadata.get("chunk_language")
                lang_str = f", Idioma: {lang_info.upper()}" if lang_info else ""
                if page is not None:
                    context_parts.append(f"Arquivo: {file_name}, Página: {page}{lang_str}\n{content}")
                else:
                    context_parts.append(f"Arquivo: {file_name}{lang_str}\n{content}")
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

    def _upload_file_to_storage(self, file_path: str, storage_path: str, overwrite: bool = False) -> None:
        try:
            bucket = self.supabase.storage.from_(self.storage_bucket)
            with open(file_path, "rb") as f:
                if overwrite and hasattr(bucket, 'update'):
                    bucket.update(storage_path, f)
                else:
                    bucket.upload(storage_path, f)
        except StorageApiError as e:
            msg = str(e).lower()
            if any(kw in msg for kw in ["row-level security", "policy", "unauthorized", "403"]):
                raise RuntimeError("Falha de permissão no Supabase Storage. Verifique a SUPABASE_SERVICE_ROLE_KEY e as políticas do bucket 'rag-documents'.")
            else:
                raise RuntimeError(f"Falha no upload para o Supabase Storage: {str(e)}")

rag_service = RAGService()
