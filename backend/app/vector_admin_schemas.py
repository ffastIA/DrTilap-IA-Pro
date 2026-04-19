# CAMINHO: backend/app/vector_admin_schemas.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class VectorFileSummary(BaseModel):
    """
    Modelo para resumo de arquivo vetorial.
    """
    model_config = ConfigDict(extra="ignore")

    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    total_chunks: int = 0
    active_chunks: int = 0
    deleted_chunks: int = 0
    deleted_at: Optional[str] = None
    last_ingested_at: Optional[str] = None
    status: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorFileDetail(VectorFileSummary):
    """
    Modelo para detalhes de arquivo vetorial, herda de VectorFileSummary.
    """
    pass


class DeleteFileRequest(BaseModel):
    """
    Modelo para requisição de exclusão de arquivo.
    """
    model_config = ConfigDict(extra="ignore")

    confirmation_phrase: str
    reason: Optional[str] = None
    hard_delete: bool = True


class DeleteFileResponse(BaseModel):
    """
    Modelo para resposta de exclusão de arquivo.
    """
    model_config = ConfigDict(extra="ignore")

    original_file_id: str
    original_file_name: str
    documents_deleted: int = 0
    ingestion_logs_deleted: int = 0
    storage_deleted: bool = False
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    status: str
    message: str


class CleanupVectorBaseRequest(BaseModel):
    """
    Modelo para requisição de limpeza da base vetorial.
    """
    model_config = ConfigDict(extra="ignore")

    confirmation_phrase: str


class CleanupVectorBaseResponse(BaseModel):
    """
    Modelo para resposta de limpeza da base vetorial.
    """
    model_config = ConfigDict(extra="ignore")

    total_files_processed: int = 0
    total_documents_deleted: int = 0
    total_ingestion_logs_deleted: int = 0
    total_storage_deleted: int = 0
    status: str
    message: str


class ReindexFileRequest(BaseModel):
    """
    Modelo para requisição de reindexação de arquivo.
    """
    model_config = ConfigDict(extra="ignore")

    confirmation_phrase: str
    original_file_ids: Optional[List[str]] = None


class ReindexFileResponse(BaseModel):
    """
    Modelo para resposta de reindexação de arquivo.
    """
    model_config = ConfigDict(extra="ignore")

    processed_files: int = 0
    failed_files: int = 0
    total_chunks_created: int = 0
    status: str
    message: str


class VectorChunk(BaseModel):
    """
    Modelo para chunk vetorial.
    """
    model_config = ConfigDict(extra="ignore")

    id: str
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    deleted_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    page: Optional[int] = None
    chunk_index: Optional[int] = None


class VectorChunksResponse(BaseModel):
    """
    Modelo para resposta de chunks vetoriais.
    """
    model_config = ConfigDict(extra="ignore")

    original_file_id: str
    original_file_name: str
    total_chunks: int = 0
    active_chunks: int = 0
    deleted_chunks: int = 0
    chunks: List[VectorChunk] = Field(default_factory=list)
    status: str
    message: str


class RecoverFileContentResponse(BaseModel):
    """
    Modelo para resposta de recuperação de conteúdo de arquivo.
    """
    model_config = ConfigDict(extra="ignore")

    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    total_chunks: int = 0
    active_chunks: int = 0
    deleted_chunks: int = 0
    content: str = ""
    chunks: List[VectorChunk] = Field(default_factory=list)
    status: str
    message: str


class RecoveryDiagnosisResponse(BaseModel):
    """
    Modelo para resposta de diagnóstico de recuperação.
    """
    model_config = ConfigDict(extra="ignore")

    original_file_id: str
    original_file_name: str
    total_chunks: int = 0
    active_chunks: int = 0
    deleted_chunks: int = 0
    has_table_data: bool = False
    has_storage: bool = False
    recoverable_from_table: bool = False
    recoverable_from_storage: bool = False
    recoverable_from_both: bool = False
    recoverable_from_none: bool = False
    status: str
    message: str