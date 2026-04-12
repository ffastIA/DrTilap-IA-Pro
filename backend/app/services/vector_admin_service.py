# CAMINHO: backend/app/services/vector_admin_service.py
# ARQUIVO: vector_admin_service.py

from typing import Any, Dict, List, Optional
from app.vector_admin_repository import VectorAdminRepository
from app.services.rag_service import rag_service


class VectorAdminService:
    """
    Serviço para administração de vetores, incluindo listagem, detalhes, exclusão e reindexação de arquivos.
    """

    def __init__(self):
        """
        Inicializa o serviço com o repositório de administração de vetores.
        """
        self.repository = VectorAdminRepository()

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Lista todos os arquivos disponíveis.

        Returns:
            Lista de dicionários representando os arquivos.
        """
        return self.repository.list_files()

    def get_file_detail(self, original_file_id: str) -> Dict[str, Any]:
        """
        Obtém os detalhes de um arquivo específico.

        Args:
            original_file_id: ID do arquivo original.

        Returns:
            Dicionário com os detalhes do arquivo.

        Raises:
            ValueError: Se o arquivo não for encontrado.
        """
        file_detail = self.repository.get_file_summary(original_file_id)
        if not file_detail:
            raise ValueError('Arquivo não encontrado para o original_file_id informado.')
        return file_detail

    def delete_by_file(self, original_file_id: str, deleted_by: str, hard_delete: bool = False,
                       reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Exclui um arquivo específico, seja por exclusão física ou lógica.

        Args:
            original_file_id: ID do arquivo original.
            deleted_by: Usuário que solicitou a exclusão.
            hard_delete: Se True, realiza exclusão física; caso contrário, lógica.
            reason: Motivo da exclusão (opcional).

        Returns:
            Dicionário com o resultado da operação.
        """
        if hard_delete:
            return self.repository.hard_delete_file(original_file_id)
        else:
            return self.repository.soft_delete_file(original_file_id, deleted_by, reason)

    def cleanup_all(self, deleted_by: str, hard_delete: bool = False, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Limpa todos os arquivos, seja por exclusão física ou lógica.

        Args:
            deleted_by: Usuário que solicitou a limpeza.
            hard_delete: Se True, realiza exclusão física; caso contrário, lógica.
            reason: Motivo da limpeza (opcional).

        Returns:
            Dicionário com o resultado da operação.
        """
        if hard_delete:
            return self.repository.hard_delete_all()
        else:
            return self.repository.soft_delete_all(deleted_by, reason)

    async def reindex_files(self, original_file_ids: Optional[List[str]] = None, requested_by: Optional[str] = None) -> \
    Dict[str, Any]:
        """
        Reindexa arquivos específicos ou todos os reindexáveis.

        Args:
            original_file_ids: Lista de IDs de arquivos para reindexar (opcional).
            requested_by: Usuário que solicitou a reindexação (opcional).

        Returns:
            Dicionário com o resumo da reindexação, incluindo totais e detalhes.
        """
        files_to_reindex = self.repository.list_reindexable_files(original_file_ids)
        total_requested = len(files_to_reindex)
        total_success = 0
        total_failed = 0
        details = []

        for item in files_to_reindex:
            try:
                await rag_service.reindex_file_from_storage(
                    original_file_id=item['original_file_id'],
                    original_file_name=item['original_file_name'],
                    storage_bucket=item['storage_bucket'],
                    storage_path=item['storage_path'],
                    requested_by=requested_by,
                )
                total_success += 1
                details.append({
                    'original_file_id': item['original_file_id'],
                    'original_file_name': item['original_file_name'],
                    'status': 'success'
                })
            except Exception as e:
                total_failed += 1
                details.append({
                    'original_file_id': item['original_file_id'],
                    'original_file_name': item['original_file_name'],
                    'status': 'failed',
                    'error': str(e)
                })

        return {
            'total_requested': total_requested,
            'total_success': total_success,
            'total_failed': total_failed,
            'details': details
        }


# Instância global do serviço
vector_admin_service = VectorAdminService()
