import os
import time
from typing import List, Optional, Dict, Any, Tuple
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import SupabaseVectorStore
import supabase
from app.utils.pdf_cleaning import clean_loaded_pages, is_editorial_or_low_value, contains_scientific_signal


class CleanReindexService:
    def __init__(self, openai_api_key: str, supabase_url: str, supabase_key: str):
        # Inicializa embeddings e vectorstore
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.supabase_admin = supabase.create_client(supabase_url, supabase_key)
        self.vectorstore = SupabaseVectorStore(
            client=self.supabase_admin, embedding=self.embeddings, table_name="documents"
        )
        # OTIMIZAÇÃO CRÍTICA: Chunks maiores para preservar tabelas/seções inteiras
        self.default_chunk_size = 4000  # Aumentado de 2500
        self.default_chunk_overlap = 500  # Aumentado de 300

    def validate_reindex_input(
        self,
        file_path: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
        dry_run: bool = True,
    ) -> None:
        # Valida parâmetros de entrada
        if not os.path.exists(file_path):
            raise ValueError(f"Arquivo não encontrado: {file_path}")

        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap

        if chunk_size <= 0:
            raise ValueError("chunk_size deve ser maior que 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap deve ser >= 0 e < chunk_size")

        if not dry_run:
            id_payload, _ = self._resolve_identification_payload(
                original_file_name, storage_bucket, storage_path, source
            )
            if not id_payload:
                raise ValueError(
                    "Para dry_run=False, forneça original_file_name ou "
                    "storage_bucket+storage_path ou source"
                )

    def _resolve_identification_payload(
        self,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        # Resolve payload de identificação por prioridade
        if storage_bucket and storage_path:
            return {"storage_bucket": storage_bucket, "storage_path": storage_path}, "storage_bucket_path"
        elif original_file_name:
            return {"original_file_name": original_file_name}, "original_file_name"
        elif source:
            return {"source": source}, "source"
        return {}, None

    def _apply_document_filters(
        self, query: Any, identification: Dict[str, Any]
    ) -> Tuple[Any, str]:
        # Aplica filtros na query Supabase
        strategy = None
        if "storage_bucket" in identification and "storage_path" in identification:
            query = query.eq("storage_bucket", identification["storage_bucket"]).eq(
                "storage_path", identification["storage_path"]
            )
            strategy = "storage_bucket_path"
        elif "original_file_name" in identification:
            query = query.eq("original_file_name", identification["original_file_name"])
            strategy = "original_file_name"
        elif "source" in identification:
            query = query.filter("metadata->>source", "eq", identification["source"])
            strategy = "source"
        else:
            raise ValueError("Nenhum identificador válido")
        return query, strategy

    def count_existing_vectors_for_file(
        self,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        # Conta vetores existentes
        id_payload, _ = self._resolve_identification_payload(
            original_file_name, storage_bucket, storage_path, source
        )
        if not id_payload:
            return 0
        query = self.supabase_admin.table("documents").select("id", count="exact")
        query, _ = self._apply_document_filters(query, id_payload)
        response = query.execute()
        return response.count or 0

    def delete_vectors_for_file(
        self,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        # Deleta vetores existentes
        id_payload, _ = self._resolve_identification_payload(
            original_file_name, storage_bucket, storage_path, source
        )
        if not id_payload:
            return 0
        query = self.supabase_admin.table("documents").delete()
        query, _ = self._apply_document_filters(query, id_payload)
        response = query.execute()
        return len(response.data) if response.data else 0

    def _load_and_clean_pages(self, file_path: str) -> Tuple[List[Document], List[Document]]:
        # Carrega e limpa páginas do PDF
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()  # List[Document]
        cleaned_docs = clean_loaded_pages(raw_docs)  # List[Document]
        return raw_docs, cleaned_docs

    def _build_splitter(self, chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
        # Constrói splitter com parâmetros otimizados
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Separadores preservam estrutura de seções antes de quebrar
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def build_clean_splits(
        self,
        file_path: str,
        chunk_size: int,
        chunk_overlap: int,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Document]:
        # Gera splits limpos
        raw_docs, cleaned_docs = self._load_and_clean_pages(file_path)
        splitter = self._build_splitter(chunk_size, chunk_overlap)
        all_chunks = splitter.split_documents(cleaned_docs)
        filtered_chunks = self.filter_low_value_chunks(all_chunks)

        # Enriquecer metadata
        identification, _ = self._resolve_identification_payload(
            original_file_name, storage_bucket, storage_path, source
        )
        for doc in filtered_chunks:
            doc.metadata["clean_reindex"] = True
            doc.metadata["cleaning_version"] = "v3"
            for key in ["original_file_name", "storage_bucket", "storage_path", "source"]:
                if key in identification:
                    doc.metadata[key] = identification[key]
        return filtered_chunks

    def filter_low_value_chunks(self, docs: List[Document]) -> List[Document]:
        # Filtra chunks de baixo valor
        filtered = []
        for doc in docs:
            content = doc.page_content.strip()
            if not content:
                continue
            if len(content) < 120:
                continue
            if is_editorial_or_low_value(content) and not contains_scientific_signal(content):
                continue
            filtered.append(doc)
        return filtered

    def _compute_processing_stats(
        self, raw_count: int, cleaned_count: int, all_chunks_count: int, filtered_count: int
    ) -> Dict[str, int]:
        # Calcula estatísticas de processamento
        return {
            "pages_loaded": raw_count,
            "pages_kept": cleaned_count,
            "pages_discarded": raw_count - cleaned_count,
            "chunks_generated": all_chunks_count,
            "chunks_kept": filtered_count,
            "chunks_discarded": all_chunks_count - filtered_count,
        }

    def _build_sample_previews(self, docs: List[Document]) -> List[str]:
        # Gera previews de amostra
        previews = []
        for doc in docs[:3]:
            content = doc.page_content
            preview = content[:200] + "..." if len(content) > 200 else content
            previews.append(preview)
        return previews

    def add_clean_documents(self, docs: List[Document]) -> int:
        # Adiciona documentos limpos ao vectorstore
        if not docs:
            raise ValueError("Lista de documentos vazia")
        self.vectorstore.add_documents(docs)
        return len(docs)

    def build_operation_report(
        self,
        success: bool,
        mode: str,
        file_path: str,
        stats: Dict[str, int],
        candidate_delete_count: int,
        vectors_deleted: int,
        vectors_inserted: int,
        duration_seconds: float,
        identification_strategy: Optional[str],
        sample_previews: List[str],
        notes: str = "",
        error_code: str = "",
        message: str = "",
    ) -> Dict[str, Any]:
        # Constrói relatório da operação
        report = {
            "success": success,
            "mode": mode,
            "file_path": file_path,
            **stats,
            "candidate_delete_count": candidate_delete_count,
            "vectors_deleted": vectors_deleted,
            "vectors_inserted": vectors_inserted,
            "duration_seconds": round(duration_seconds, 2),
            "identification_strategy": identification_strategy,
            "sample_previews": sample_previews,
            "notes": notes,
            "error_code": error_code,
            "message": message,
        }
        return report

    def preview_clean_reindex(
        self,
        file_path: str,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        # Pré-visualiza reindexação limpa
        start_time = time.time()
        try:
            self.validate_reindex_input(
                file_path,
                chunk_size,
                chunk_overlap,
                original_file_name,
                storage_bucket,
                storage_path,
                source,
                dry_run=True,
            )
            chunk_size = chunk_size or self.default_chunk_size
            chunk_overlap = chunk_overlap or self.default_chunk_overlap

            raw_docs, cleaned_docs = self._load_and_clean_pages(file_path)
            splitter = self._build_splitter(chunk_size, chunk_overlap)
            all_chunks = splitter.split_documents(cleaned_docs)
            filtered_chunks = self.filter_low_value_chunks(all_chunks)

            stats = self._compute_processing_stats(
                len(raw_docs), len(cleaned_docs), len(all_chunks), len(filtered_chunks)
            )

            id_payload, id_strategy = self._resolve_identification_payload(
                original_file_name, storage_bucket, storage_path, source
            )
            candidate_delete_count = (
                self.count_existing_vectors_for_file(
                    original_file_name=original_file_name,
                    storage_bucket=storage_bucket,
                    storage_path=storage_path,
                    source=source,
                )
                if id_payload
                else 0
            )

            duration = time.time() - start_time
            sample_previews = self._build_sample_previews(filtered_chunks)

            return self.build_operation_report(
                success=True,
                mode="preview",
                file_path=file_path,
                stats=stats,
                candidate_delete_count=candidate_delete_count,
                vectors_deleted=0,
                vectors_inserted=0,
                duration_seconds=duration,
                identification_strategy=id_strategy,
                sample_previews=sample_previews,
                notes="Pré-visualização concluída com sucesso.",
            )
        except Exception as e:
            duration = time.time() - start_time
            zero_stats = self._compute_processing_stats(0, 0, 0, 0)
            return self.build_operation_report(
                success=False,
                mode="preview",
                file_path=file_path,
                stats=zero_stats,
                candidate_delete_count=0,
                vectors_deleted=0,
                vectors_inserted=0,
                duration_seconds=duration,
                identification_strategy=None,
                sample_previews=[],
                notes=str(e),
                error_code="PREVIEW_ERROR",
                message="Falha na pré-visualização.",
            )

    def reindex_file_clean(
        self,
        file_path: str,
        original_file_name: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        source: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        # Reindexa arquivo com limpeza
        if dry_run:
            return self.preview_clean_reindex(
                file_path,
                original_file_name,
                storage_bucket,
                storage_path,
                source,
                chunk_size,
                chunk_overlap,
            )

        start_time = time.time()
        try:
            self.validate_reindex_input(
                file_path,
                chunk_size,
                chunk_overlap,
                original_file_name,
                storage_bucket,
                storage_path,
                source,
                dry_run=False,
            )
            chunk_size = chunk_size or self.default_chunk_size
            chunk_overlap = chunk_overlap or self.default_chunk_overlap

            raw_docs, cleaned_docs = self._load_and_clean_pages(file_path)
            splitter = self._build_splitter(chunk_size, chunk_overlap)
            all_chunks = splitter.split_documents(cleaned_docs)
            filtered_chunks = self.filter_low_value_chunks(all_chunks)

            if len(filtered_chunks) == 0:
                raise ValueError("Nenhum chunk útil após filtragem")

            stats = self._compute_processing_stats(
                len(raw_docs), len(cleaned_docs), len(all_chunks), len(filtered_chunks)
            )

            candidate_delete_count = self.count_existing_vectors_for_file(
                original_file_name=original_file_name,
                storage_bucket=storage_bucket,
                storage_path=storage_path,
                source=source,
            )
            vectors_deleted = self.delete_vectors_for_file(
                original_file_name=original_file_name,
                storage_bucket=storage_bucket,
                storage_path=storage_path,
                source=source,
            )
            vectors_inserted = self.add_clean_documents(filtered_chunks)

            duration = time.time() - start_time
            sample_previews = self._build_sample_previews(filtered_chunks)

            notes = (
                f"Reindexação concluída. "
                f"Deletados: {vectors_deleted}, Inseridos: {vectors_inserted}."
            )

            return self.build_operation_report(
                success=True,
                mode="reindex",
                file_path=file_path,
                stats=stats,
                candidate_delete_count=candidate_delete_count,
                vectors_deleted=vectors_deleted,
                vectors_inserted=vectors_inserted,
                duration_seconds=duration,
                identification_strategy=self._resolve_identification_payload(
                    original_file_name, storage_bucket, storage_path, source
                )[1],
                sample_previews=sample_previews,
                notes=notes,
            )
        except Exception as e:
            duration = time.time() - start_time
            zero_stats = self._compute_processing_stats(0, 0, 0, 0)
            return self.build_operation_report(
                success=False,
                mode="reindex",
                file_path=file_path,
                stats=zero_stats,
                candidate_delete_count=0,
                vectors_deleted=0,
                vectors_inserted=0,
                duration_seconds=duration,
                identification_strategy=None,
                sample_previews=[],
                notes=str(e),
                error_code="REINDEX_ERROR",
                message="Falha na reindexação.",
            )