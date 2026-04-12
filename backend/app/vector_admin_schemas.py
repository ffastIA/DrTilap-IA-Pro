# CAMINHO: backend/app/vector_admin_schemas.py
# ARQUIVO: vector_admin_schemas.py

from typing import List, Optional
from pydantic import BaseModel, Field
from typing import Literal

# Frases fixas para confirmação de operações administrativas
CONFIRMAR_EXCLUSAO = 'CONFIRMAR_EXCLUSAO'
CONFIRMAR_LIMPEZA_TOTAL = 'CONFIRMAR_LIMPEZA_TOTAL'
CONFIRMAR_REINDEXACAO = 'CONFIRMAR_REINDEXACAO'


class DeleteFileRequest(BaseModel):
    """
    Schema para requisição de exclusão de um arquivo vetorial específico.
    """
    original_file_id: str = Field(..., description="ID do arquivo original a ser excluído")
    confirmation_phrase: Literal['CONFIRMAR_EXCLUSAO'] = Field(..., description="Frase de confirmação obrigatória")
    reason: Optional[str] = Field(None, description="Razão opcional para a exclusão")
    hard_delete: bool = Field(False, description="Se verdadeiro, realiza exclusão física")


class CleanupRequest(BaseModel):
    """
    Schema para requisição de limpeza total da base vetorial.
    """
    confirmation_phrase: Literal['CONFIRMAR_LIMPEZA_TOTAL'] = Field(..., description="Frase de confirmação obrigatória")
    reason: Optional[str] = Field(None, description="Razão opcional para a limpeza")
    hard_delete: bool = Field(False, description="Se verdadeiro, realiza exclusão física")


class ReindexRequest(BaseModel):
    """
    Schema para requisição de reindexação da base vetorial.
    """
    confirmation_phrase: Literal['CONFIRMAR_REINDEXACAO'] = Field(..., description="Frase de confirmação obrigatória")
    original_file_ids: Optional[List[str]] = Field(None, description="Lista opcional de IDs de arquivos originais para reindexar")


class VectorFileSummary(BaseModel):
    """
    Schema para resumo de um arquivo vetorial.
    """
    original_file_id: str = Field(..., description="ID do arquivo original")
    original_file_name: str = Field(..., description="Nome do arquivo original")
    storage_bucket: str = Field(..., description="Bucket de armazenamento")
    storage_path: str = Field(..., description="Caminho no armazenamento")
    total_chunks: int = Field(..., description="Número total de chunks")
    active_chunks: int = Field(..., description="Número de chunks ativos")
    deleted_chunks: int = Field(..., description="Número de chunks deletados")
    deleted_at: Optional[str] = Field(None, description="Data de exclusão, se aplicável")
    last_ingested_at: str = Field(..., description="Última data de ingestão")
    status: str = Field(..., description="Status do arquivo (ex: ativo, deletado)")


class VectorFileDetail(VectorFileSummary):
    """
    Schema para detalhes de um arquivo vetorial, herdando de VectorFileSummary.
    """
    # Pode adicionar campos adicionais aqui se necessário, por enquanto herda tudo
    pass


class VectorOperationResponse(BaseModel):
    """
    Schema para resposta de operações administrativas na base vetorial.
    """
    message: str = Field(..., description="Mensagem da operação")
    status: str = Field(..., description="Status da operação (ex: sucesso, erro)")
    details: dict = Field(..., description="Detalhes adicionais da operação")
