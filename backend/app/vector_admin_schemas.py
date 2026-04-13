# CAMINHO: backend/app/vector_admin_schemas.py
# ARQUIVO: vector_admin_schemas.py

from typing import Any, Dict, List, Optional
from typing import Literal
from pydantic import BaseModel, Field

# Constantes para frases de confirmação obrigatórias
CONFIRMAR_EXCLUSAO = 'CONFIRMAR_EXCLUSAO'
CONFIRMAR_LIMPEZA_TOTAL = 'CONFIRMAR_LIMPEZA_TOTAL'
CONFIRMAR_REINDEXACAO = 'CONFIRMAR_REINDEXACAO'


class DeleteFileRequest(BaseModel):
    # Requisição para exclusão seletiva de arquivo vetorial
    original_file_id: str = Field(..., description="ID do arquivo original a ser excluído")
    confirmation_phrase: Literal['CONFIRMAR_EXCLUSAO'] = Field(..., description="Frase de confirmação obrigatória")
    reason: Optional[str] = Field(default=None, description="Motivo opcional da exclusão")
    hard_delete: bool = Field(default=False, description="Se verdadeiro, realiza exclusão física")


class CleanupRequest(BaseModel):
    # Requisição para limpeza geral da base vetorial
    confirmation_phrase: Literal['CONFIRMAR_LIMPEZA_TOTAL'] = Field(..., description="Frase de confirmação obrigatória")
    reason: Optional[str] = Field(default=None, description="Motivo opcional da limpeza")
    hard_delete: bool = Field(default=False, description="Se verdadeiro, realiza exclusão física")


class ReindexRequest(BaseModel):
    # Requisição para reindexação da base vetorial
    confirmation_phrase: Literal['CONFIRMAR_REINDEXACAO'] = Field(..., description="Frase de confirmação obrigatória")
    original_file_ids: Optional[List[str]] = Field(default=None, description="Lista opcional de IDs de arquivos para reindexar")


class VectorFileSummary(BaseModel):
    # Resumo de arquivo vetorial
    original_file_id: str
    original_file_name: Optional[str] = None
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    total_chunks: int = 0
    active_chunks: int = 0
    deleted_chunks: int = 0
    deleted_at: Optional[str] = None
    last_ingested_at: Optional[str] = None
    status: str = 'unknown'


class VectorFileDetail(VectorFileSummary):
    # Detalhes completos de arquivo vetorial, herdando de VectorFileSummary
    metadata: Optional[Dict[str, Any]] = None


class VectorOperationResponse(BaseModel):
    # Resposta para operações administrativas na base vetorial
    message: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class VectorFileListResponse(BaseModel):
    # Resposta para listagem de arquivos vetoriais
    files: List[VectorFileSummary] = Field(default_factory=list)