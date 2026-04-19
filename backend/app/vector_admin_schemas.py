# CAMINHO: backend/app/vector_admin_schemas.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VectorFileSummary(BaseModel):
    """
    Resumo de um arquivo vetorial, contendo informações básicas sobre o arquivo e seus chunks.
    """
    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    total_chunks: int
    active_chunks: int
    deleted_chunks: int
    deleted_at: Optional[datetime] = None
    last_ingested_at: Optional[datetime] = None
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorFileDetail(BaseModel):
    """
    Detalhes completos de um arquivo vetorial, incluindo metadados e estatísticas de chunks.
    """
    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    total_chunks: int
    active_chunks: int
    deleted_chunks: int
    deleted_at: Optional[datetime] = None
    last_ingested_at: Optional[datetime] = None
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeleteFileRequest(BaseModel):
    """
    Solicitação para deletar um arquivo vetorial, com confirmação e opções.
    """
    confirmation_phrase: str
    reason: Optional[str] = None
    hard_delete: bool = True


class DeleteFileResponse(BaseModel):
    """
    Resposta da operação de deletar um arquivo vetorial, com estatísticas da exclusão.
    """
    original_file_id: str
    original_file_name: str
    documents_deleted: int
    ingestion_logs_deleted: int
    storage_deleted: bool
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    status: str
    message: str


class CleanupVectorBaseRequest(BaseModel):
    """
    Solicitação para limpeza da base vetorial, com confirmação obrigatória.
    """
    confirmation_phrase: str


class CleanupVectorBaseResponse(BaseModel):
    """
    Resposta da operação de limpeza da base vetorial, com estatísticas da limpeza.
    """
    total_files_processed: int
    total_documents_deleted: int
    total_ingestion_logs_deleted: int
    total_storage_deleted: int
    status: str
    message: str


class ReindexFileRequest(BaseModel):
    """
    Solicitação para reindexar arquivos vetoriais, com confirmação e lista opcional de IDs.
    """
    confirmation_phrase: str
    original_file_ids: Optional[List[str]] = None


class ReindexFileResponse(BaseModel):
    """
    Resposta da operação de reindexação de arquivos vetoriais, com estatísticas do processamento.
    """
    processed_files: int
    failed_files: int
    total_chunks_created: int
    status: str
    message: str


class VectorChunk(BaseModel):
    """
    Representa um chunk vetorial, com conteúdo, metadados e informações do arquivo original.
    """
    id: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    page: int = 0
    chunk_index: int = 0


class VectorChunksResponse(BaseModel):
    """
    Resposta contendo a lista de chunks vetoriais de um arquivo, com estatísticas.
    """
    original_file_id: str
    original_file_name: str
    total_chunks: int
    active_chunks: int
    deleted_chunks: int
    chunks: List[VectorChunk]
    status: str
    message: str


class RecoverFileContentResponse(BaseModel):
    """
    Resposta da recuperação de conteúdo de um arquivo vetorial, incluindo chunks e conteúdo reconstruído.
    """
    original_file_id: str
    original_file_name: str
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    total_chunks: int
    active_chunks: int
    deleted_chunks: int
    content: str
    chunks: List[VectorChunk]
    status: str
    message: str


class RecoveryDiagnosisResponse(BaseModel):
    """
    Resposta do diagnóstico de recuperação de um arquivo vetorial, indicando possibilidades de recuperação.
    """
    original_file_id: str
    original_file_name: str
    total_chunks: int
    active_chunks: int
    deleted_chunks: int
    has_table_data: bool
    has_storage: bool
    recoverable_from_table: bool
    recoverable_from_storage: bool
    recoverable_from_both: bool
    recoverable_from_none: bool
    status: str
    message: str