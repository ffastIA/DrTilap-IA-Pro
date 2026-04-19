# CAMINHO: backend/app/services/vector_admin_service.py

import logging
from typing import Optional, Dict, Any, List
from app.vector_admin_repository import VectorAdminRepository
from app.services.rag_service import rag_service


class VectorAdminService:
    """
    Serviço para administração de vetores, incluindo operações de listagem, exclusão,
    limpeza e reindexação de arquivos no sistema de RAG.
    """

    DELETE_CONFIRMATION = "CONFIRMAR_EXCLUSAO"
    CLEANUP_CONFIRMATION = "CONFIRMAR_LIMPEZA_TOTAL"
    REINDEX_CONFIRMATION = "CONFIRMAR_REINDEXACAO"

    def __init__(self):
        """
        Inicializa o serviço com o repositório e o logger.
        """
        self.repository = VectorAdminRepository()
        self.logger = logging.getLogger(__name__)

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Lista todos os arquivos disponíveis no repositório.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários representando os arquivos.
        """
        self.logger.info("Listando arquivos.")
        return self.repository.list_files()

    def get_file(self, original_file_id: str) -> Dict[str, Any]:
        """
        Obtém informações de um arquivo específico.

        Args:
            original_file_id (str): ID do arquivo original.

        Returns:
            Dict[str, Any]: Dicionário com informações do arquivo.

        Raises:
            ValueError: Se o arquivo não existir.
        """
        self.logger.info(f"Obtendo arquivo com ID: {original_file_id}.")
        file_info = self.repository.get_file(original_file_id)
        if not file_info:
            raise ValueError(f"Arquivo com ID {original_file_id} não encontrado.")
        return file_info

    def delete_file(self, original_file_id: str, confirmation_phrase: str, reason: Optional[str] = None, hard_delete: bool = True) -> Dict[str, Any]:
        """
        Exclui um arquivo após validação da frase de confirmação.

        Args:
            original_file_id (str): ID do arquivo original.
            confirmation_phrase (str): Frase de confirmação.
            reason (Optional[str]): Motivo da exclusão.
            hard_delete (bool): Se deve fazer exclusão física.

        Returns:
            Dict[str, Any]: Resultado da operação de exclusão.

        Raises:
            ValueError: Se a frase de confirmação for inválida.
        """
        if confirmation_phrase != self.DELETE_CONFIRMATION:
            raise ValueError("Frase de confirmação inválida para exclusão.")
        self.logger.info(f"Excluindo arquivo {original_file_id} com motivo: {reason}.")
        return self.repository.purge_file(original_file_id)

    def cleanup_vector_base(self, confirmation_phrase: str) -> Dict[str, Any]:
        """
        Limpa a base de vetores após validação da frase de confirmação.

        Args:
            confirmation_phrase (str): Frase de confirmação.

        Returns:
            Dict[str, Any]: Resultado da operação de limpeza.

        Raises:
            ValueError: Se a frase de confirmação for inválida.
        """
        if confirmation_phrase != self.CLEANUP_CONFIRMATION:
            raise ValueError("Frase de confirmação inválida para limpeza total.")
        self.logger.info("Iniciando limpeza total da base de vetores.")
        return self.repository.cleanup_vector_base()

    async def reindex_files(self, confirmation_phrase: str, original_file_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Reindexa arquivos específicos ou todos após validação da frase de confirmação.

        Args:
            confirmation_phrase (str): Frase de confirmação.
            original_file_ids (Optional[List[str]]): IDs dos arquivos a reindexar.

        Returns:
            Dict[str, Any]: Resultado da reindexação com contadores e status.

        Raises:
            ValueError: Se a frase de confirmação for inválida.
        """
        if confirmation_phrase != self.REINDEX_CONFIRMATION:
            raise ValueError("Frase de confirmação inválida para reindexação.")
        self.logger.info(f"Iniciando reindexação para IDs: {original_file_ids}.")
        files_to_reindex = self.repository.list_reindexable_files(original_file_ids)
        processed_files = 0
        failed_files = 0
        total_chunks_created = 0
        for file_info in files_to_reindex:
            try:
                result = await rag_service.reindex_file_from_storage(file_info)
                if isinstance(result, int):
                    total_chunks_created += result
                elif isinstance(result, dict):
                    total_chunks_created += result.get('chunks_created', 0)
                processed_files += 1
            except Exception as e:
                self.logger.error(f"Falha ao reindexar arquivo {file_info.get('original_file_id')}: {str(e)}")
                failed_files += 1
        status = "success" if failed_files == 0 else "partial_success"
        message = f"Reindexação concluída: {processed_files} processados, {failed_files} falharam, {total_chunks_created} chunks criados."
        self.logger.info(message)
        return {
            "processed_files": processed_files,
            "failed_files": failed_files,
            "total_chunks_created": total_chunks_created,
            "status": status,
            "message": message
        }

    def get_file_chunks(self, original_file_id: str, include_deleted: bool = False) -> Dict[str, Any]:
        """
        Obtém os chunks de um arquivo.

        Args:
            original_file_id (str): ID do arquivo original.
            include_deleted (bool): Se deve incluir chunks deletados.

        Returns:
            Dict[str, Any]: Payload com informações dos chunks.
        """
        self.logger.info(f"Obtendo chunks do arquivo {original_file_id}.")
        chunks_data = self.repository.get_document_chunks(original_file_id, include_deleted)
        return {
            "original_file_id": original_file_id,
            "original_file_name": chunks_data.get("original_file_name", ""),
            "total_chunks": chunks_data.get("total_chunks", 0),
            "active_chunks": chunks_data.get("active_chunks", 0),
            "deleted_chunks": chunks_data.get("deleted_chunks", 0),
            "chunks": chunks_data.get("chunks", []),
            "status": chunks_data.get("status", "success"),
            "message": chunks_data.get("message", "Chunks obtidos com sucesso.")
        }

    def recover_file_content(self, original_file_id: str, include_deleted: bool = False) -> Dict[str, Any]:
        """
        Recupera o conteúdo de um arquivo.

        Args:
            original_file_id (str): ID do arquivo original.
            include_deleted (bool): Se deve incluir conteúdo deletado.

        Returns:
            Dict[str, Any]: Conteúdo recuperado do arquivo.
        """
        self.logger.info(f"Recuperando conteúdo do arquivo {original_file_id}.")
        content_data = self.repository.rebuild_document_content(original_file_id, include_deleted)
        if "message" not in content_data:
            content_data["message"] = "Conteúdo recuperado com sucesso."
        return content_data

    def diagnose_file_recovery(self, original_file_id: str) -> Dict[str, Any]:
        """
        Diagnóstica a recuperação de um arquivo.

        Args:
            original_file_id (str): ID do arquivo original.

        Returns:
            Dict[str, Any]: Diagnóstico da recuperação.
        """
        self.logger.info(f"Diagnosticando recuperação do arquivo {original_file_id}.")
        return self.repository.get_file_recovery_diagnosis(original_file_id)


# Instância global do serviço
vector_admin_service = VectorAdminService()
