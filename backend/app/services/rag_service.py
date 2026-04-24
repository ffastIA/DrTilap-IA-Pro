import uuid
import logging
from pathlib import Path
from tempfile import gettempdir
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import supabase_admin
from storage3.exceptions import StorageApiError

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.supabase = supabase_admin
        self.storage_bucket = "rag-documents"
        self.embedding_batch_size = 20
        self.insert_batch_size = 20
        self.log_dir = Path(__file__).resolve().parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        # self.primary_rpc_similarity_threshold = 0.84
        # self.auxiliary_rpc_similarity_threshold = 0.72
        # self.strict_primary_threshold = 0.84
        # self.strict_secondary_threshold = 0.74
        # self.min_supporting_chunks = 2
        # self.support_check_similarity_gate = 0.88
        self.primary_rpc_similarity_threshold = 0.5
        self.auxiliary_rpc_similarity_threshold = 0.6
        self.strict_primary_threshold = 0.5
        self.strict_secondary_threshold = 0.6
        self.min_supporting_chunks = 2
        self.support_check_similarity_gate = 0.5
        self.use_support_validator = True
        self.ingest_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=100)

    def _detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return 'pt'
        words = [w.strip('.,!?;:"\'()[]{}') for w in text.lower().split() if w.strip('.,!?;:"\'()[]{}')]
        pt_words = {'o', 'a', 'de', 'do', 'da', 'em', 'um', 'uma', 'para', 'é', 'com', 'não', 'na', 'os', 'no', 'as', 'dos', 'que', 'por', 'mais', 'pelo', 'pela', 'sem', 'sobre', 'este', 'esta', 'foi', 'era', 'tem', 'ser'}
        en_words = {'the', 'of', 'and', 'a', 'to', 'in', 'is', 'you', 'that', 'it', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they', 'i', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'but', 'not', 'what', 'all', 'were', 'when', 'can', 'said', 'there', 'use', 'an', 'each'}
        pt_score = sum(1 for w in words if w in pt_words)
        en_score = sum(1 for w in words if w in en_words)
        return 'pt' if pt_score > en_score else 'en'

    def _clean_text(self, text: str) -> str:
        text = text.replace('\r', '\n')
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            line = ' '.join(line.split())
            if line and (not clean_lines or clean_lines[-1] != line):
                clean_lines.append(line)
        return '\n'.join(clean_lines)

    def _write_semantic_log_block(self, log_file: Path, request_id: str, block_title: str, **kwargs) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[RAG][{timestamp}][{request_id}][{block_title}]\n")
            for key, value in kwargs.items():
                f.write(f"- {key}: {value}\n")
            f.write("-" * 100 + "\n\n")

    async def ingest_pdf(self, file_path: str, filename: str, original_file_id: Optional[str] = None, cleanup_existing: bool = True) -> Dict[str, Any]:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        if original_file_id is None:
            original_file_id = str(uuid.uuid4())
        self.logger.info(f"Iniciando ingestão do PDF: {filename}")
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        for doc in documents:
            doc.page_content = self._clean_text(doc.page_content)
        text_splitter = self.ingest_splitter
        chunks = text_splitter.split_documents(documents)
        chunks_brutos = len(chunks)
        seen = set()
        final_chunks = []
        for chunk in chunks:
            content = chunk.page_content.strip()
            if content and content not in seen:
                seen.add(content)
                final_chunks.append(chunk)
        duplicatas_removidas = chunks_brutos - len(final_chunks)
        chunks_finais = len(final_chunks)
        chunks = final_chunks
        self.logger.info(f"chunks_brutos: {chunks_brutos}, duplicatas_removidas: {duplicatas_removidas}, chunks_finais: {chunks_finais} do PDF {filename}")
        if not chunks:
            raise ValueError("Nenhum chunk foi gerado do PDF.")
        full_text = " ".join(doc.page_content for doc in documents)
        document_language = self._detect_language(full_text)
        self.logger.info(f"Idioma detectado do documento {filename}: {document_language}")
        storage_path = f"uploads/{original_file_id}/{filename}"
        self._upload_file_to_storage(file_path, storage_path, overwrite=cleanup_existing)
        self.logger.info(f"PDF {filename} enviado para storage em {storage_path}")
        if cleanup_existing:
            await self._delete_existing_document_chunks(original_file_id=original_file_id, original_file_name=filename)
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
        request_id = str(uuid.uuid4()).split('-')[0][:8]
        timestamp_filename = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"Log+{timestamp_filename}.txt"
        self._write_semantic_log_block(log_file, request_id, "INPUT",
            question=question,
            question_language=question_language,
            chat_history_size=len(chat_history)
        )
        self._write_semantic_log_block(log_file, request_id, "CONFIG",
            primary_rpc_similarity_threshold=self.primary_rpc_similarity_threshold,
            auxiliary_rpc_similarity_threshold=self.auxiliary_rpc_similarity_threshold,
            strict_primary_threshold=self.strict_primary_threshold,
            strict_secondary_threshold=self.strict_secondary_threshold,
            min_supporting_chunks=self.min_supporting_chunks,
            support_check_similarity_gate=self.support_check_similarity_gate,
            use_support_validator=self.use_support_validator,
            semantic_search_log_path=str(log_file)
        )
        query_embedding = self.embeddings.embed_query(question)
        response_orig = self.supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_count": 5,
            "similarity_threshold": self.primary_rpc_similarity_threshold
        }).execute()
        docs_orig = response_orig.data or []
        if question_language == 'pt':
            eng_prompt = f'''Traduza esta pergunta para inglês de forma precisa, concisa e otimizada para busca semântica:\n\n"{question}"\n\nResponda APENAS com a tradução em inglês, sem explicações adicionais.'''
            eng_response = await self.llm.ainvoke(eng_prompt)
            english_query = eng_response.content.strip()
            self._write_semantic_log_block(log_file, request_id, "AUX_QUERY", english_query=english_query)
            eng_embedding = self.embeddings.embed_query(english_query)
            response_eng = self.supabase.rpc("match_documents", {
                "query_embedding": eng_embedding,
                "match_count": 5,
                "similarity_threshold": self.auxiliary_rpc_similarity_threshold
            }).execute()
            docs_eng = response_eng.data or []
        else:
            docs_eng = []
            english_query = "N/A"
            self._write_semantic_log_block(log_file, request_id, "AUX_QUERY", english_query=english_query)
        docs_orig_preview = ', '.join(f"{round(d.get('similarity', 0), 3)}" for d in docs_orig[:3])
        docs_eng_preview = ', '.join(f"{round(d.get('similarity', 0), 3)}" for d in docs_eng[:3])
        self._write_semantic_log_block(log_file, request_id, "RAW_RESULTS",
            docs_orig_count=len(docs_orig),
            docs_eng_count=len(docs_eng),
            docs_orig_preview=docs_orig_preview,
            docs_eng_preview=docs_eng_preview
        )
        all_docs = docs_orig + docs_eng
        seen = set()
        unique_docs = []
        for doc in all_docs:
            key = f"{doc.get('original_file_id', '')}_{doc.get('metadata', {}).get('page', 0)}"
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)
        unique_docs.sort(key=lambda d: d.get('similarity', 0.0), reverse=True)
        unique_docs_preview = ', '.join(f"{round(d.get('similarity', 0), 3)}" for d in unique_docs[:3])
        self._write_semantic_log_block(log_file, request_id, "POST_DEDUP",
            docs_after_dedup_count=len(unique_docs),
            docs_after_dedup_preview=unique_docs_preview
        )
        main_evidence = [d for d in docs_orig if d.get('similarity', 0) >= self.strict_primary_threshold]
        aux_evidence = [d for d in docs_eng if d.get('similarity', 0) >= self.strict_secondary_threshold]
        all_evidence = main_evidence + aux_evidence
        seen_ev = set()
        evidence_docs_raw = []
        for doc in all_evidence:
            key = f"{doc.get('original_file_id', '')}_{doc.get('metadata', {}).get('page', 0)}"
            if key not in seen_ev:
                seen_ev.add(key)
                evidence_docs_raw.append(doc)
        evidence_docs_raw.sort(key=lambda d: d.get('similarity', 0.0), reverse=True)
        best_similarity = evidence_docs_raw[0].get('similarity', 0.0) if evidence_docs_raw else 0.0
        supporting_chunks_count = len(evidence_docs_raw)
        has_primary_evidence = len(main_evidence) > 0
        has_secondary_evidence = len(aux_evidence) > 0
        evidence_decision = "APPROVED" if supporting_chunks_count >= self.min_supporting_chunks else "REJECTED"
        self._write_semantic_log_block(log_file, request_id, "EVIDENCE",
            best_similarity=round(best_similarity, 3),
            supporting_chunks_count=supporting_chunks_count,
            has_primary_evidence=has_primary_evidence,
            has_secondary_evidence=has_secondary_evidence,
            evidence_decision=evidence_decision
        )
        if evidence_decision == "REJECTED":
            answer = "Desculpe, não encontrei evidências suficientes na base de conhecimento para responder à sua pergunta."
            self._write_semantic_log_block(log_file, request_id, "OUTPUT",
                final_decision="NO_DATA_INSUFFICIENT_EVIDENCE",
                sources_count=0,
                source_files=[]
            )
            return {
                "answer": answer,
                "sources": []
            }
        normalized_docs = [self._normalize_match_doc(doc) for doc in evidence_docs_raw[:5]]
        context = self._build_context_from_docs(normalized_docs)
        if not context:
            answer = "Desculpe, não encontrei conteúdo suficiente na base de conhecimento para responder à sua pergunta sobre piscicultura e tilápia."
            self._write_semantic_log_block(log_file, request_id, "OUTPUT",
                final_decision="NO_CONTEXT_EMPTY",
                sources_count=0,
                source_files=[]
            )
            return {
                "answer": answer,
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
        response = await self.llm.ainvoke(prompt)
        answer = response.content
        sources = [{"original_file_name": doc.get("original_file_name"), "page": doc.get("metadata", {}).get("page")} for doc in normalized_docs if doc.get("content")]
        sources_count = len(sources)
        source_files = list(set(s["original_file_name"] for s in sources))
        self._write_semantic_log_block(log_file, request_id, "OUTPUT",
            final_decision="ANSWER_FROM_CONTEXT",
            sources_count=sources_count,
            source_files=source_files
        )
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
        except StorageApiError:
            return {"error": "Falha ao baixar arquivo do storage para reindexação."}
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
            total_inserted += len(batch)
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

    async def _delete_existing_document_chunks(self, original_file_id: Optional[str] = None, original_file_name: Optional[str] = None):
        if original_file_id:
            self.supabase.table("documents").delete().eq("original_file_id", original_file_id).execute()
        if original_file_name:
            self.supabase.table("documents").delete().eq("original_file_name", original_file_name).execute()
            try:
                self.supabase.table("documents").delete().eq("metadata->>source", original_file_name).execute()
            except Exception:
                pass

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
