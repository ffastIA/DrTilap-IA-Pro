# CAMINHO: backend/app/services/vector_admin_service.py
# ARQUIVO: vector_admin_service.py

from typing import Any, Dict, List, Optional
from app.vector_admin_repository import VectorAdminRepository
from app.services.rag_service import rag_service


class VectorAdminService:
    def __init__(self):
        self.repository = VectorAdminRepository()

    def list_files(self) -> List[Dict[str, Any]]:
        # Lista todos os arquivos
        return self.repository.list_files()

    def get_file_detail(self, original_file_id: str) -> Dict[str, Any]:
        # Obtém detalhes de um arquivo específico
        file_detail = self.repository.get_file_summary(original_file_id)
        if not file_detail:
            raise ValueError('Arquivo não encontrado para o original_file_id informado.')
        return file_detail

    def delete_by_file(self, original_file_id: str, deleted_by: str, hard_delete: bool = False, reason: Optional[str] = None) -> Dict[str, Any]:
        # Deleta um arquivo específico
        if hard_delete:
            return self.repository.hard_delete_file(original_file_id)
        else:
            return self.repository.soft_delete_file(original_file_id, deleted_by, reason)

    def cleanup_all(self, deleted_by: str, hard_delete: bool = False, reason: Optional[str] = None) -> Dict[str, Any]:
        # Limpa todos os arquivos
        if hard_delete:
            return self.repository.hard_delete_all()
        else:
            return self.repository.soft_delete_all(deleted_by, reason)

    async def reindex_files(self, original_file_ids: Optional[List[str]] = None, requested_by: Optional[str] = None) -> Dict[str, Any]:
        # Reindexa arquivos específicos ou todos se não especificado
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


vector_admin_service = VectorAdminService()
