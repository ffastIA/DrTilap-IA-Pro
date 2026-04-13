# CAMINHO: backend/app/vector_admin_repository.py
# ARQUIVO: vector_admin_repository.py

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import supabase


class VectorAdminRepository:
    """
    Repositório para administração vetorial, gerenciando arquivos e chunks na tabela documents.
    """

    def _utc_now_iso(self) -> str:
        """
        Retorna a data e hora atual em UTC no formato ISO.
        """
        return datetime.now(timezone.utc).isoformat()

    def _safe_data(self, response) -> List[Dict[str, Any]]:
        """
        Extrai dados seguros de uma resposta do Supabase.
        """
        return response.data if response and hasattr(response, 'data') else []

    def _group_rows_by_file(self, rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa linhas por original_file_id.
        """
        grouped = {}
        for row in rows:
            file_id = row.get('original_file_id')
            if file_id:
                if file_id not in grouped:
                    grouped[file_id] = []
                grouped[file_id].append(row)
        return grouped

    def _chunked_ids(self, ids: List[Any], size: int = 100) -> List[List[Any]]:
        """
        Divide uma lista de IDs em chunks de tamanho especificado.
        """
        return [ids[i:i + size] for i in range(0, len(ids), size)]

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Lista arquivos agrupados por original_file_id com resumos.
        """
        response = supabase.table('documents').select(
            'id, original_file_id, original_file_name, storage_bucket, storage_path, deleted_at, created_at, updated_at, metadata'
        ).execute()
        rows = self._safe_data(response)
        grouped = self._group_rows_by_file(rows)
        files = []
        for file_id, file_rows in grouped.items():
            total_chunks = len(file_rows)
            active_chunks = sum(1 for r in file_rows if r.get('deleted_at') is None)
            deleted_chunks = total_chunks - active_chunks
            deleted_at = next((r['deleted_at'] for r in file_rows if r.get('deleted_at')), None)
            last_ingested_at = max((r['created_at'] for r in file_rows if r.get('created_at')), default=None)
            status = 'deleted' if active_chunks == 0 and deleted_chunks > 0 else 'active' if active_chunks > 0 else 'unknown'
            metadata = file_rows[0].get('metadata', {}) if file_rows else {}
            original_file_name = file_rows[0].get('original_file_name') if file_rows else None
            storage_bucket = file_rows[0].get('storage_bucket') if file_rows else None
            storage_path = file_rows[0].get('storage_path') if file_rows else None
            files.append({
                'original_file_id': file_id,
                'original_file_name': original_file_name,
                'storage_bucket': storage_bucket,
                'storage_path': storage_path,
                'total_chunks': total_chunks,
                'active_chunks': active_chunks,
                'deleted_chunks': deleted_chunks,
                'deleted_at': deleted_at,
                'last_ingested_at': last_ingested_at,
                'status': status,
                'metadata': metadata
            })
        files.sort(key=lambda x: x['original_file_name'] or '')
        return files

    def get_file_rows(self, original_file_id: str, include_deleted: bool = True) -> List[Dict[str, Any]]:
        """
        Obtém todas as linhas de um arquivo específico.
        """
        response = supabase.table('documents').select('*').eq('original_file_id', original_file_id).execute()
        rows = self._safe_data(response)
        if not include_deleted:
            rows = [r for r in rows if r.get('deleted_at') is None]
        return rows

    def get_file_summary(self, original_file_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém o resumo de um arquivo específico.
        """
        rows = self.get_file_rows(original_file_id, include_deleted=True)
        if not rows:
            return None
        total_chunks = len(rows)
        active_chunks = sum(1 for r in rows if r.get('deleted_at') is None)
        deleted_chunks = total_chunks - active_chunks
        deleted_at = next((r['deleted_at'] for r in rows if r.get('deleted_at')), None)
        last_ingested_at = max((r['created_at'] for r in rows if r.get('created_at')), default=None)
        status = 'deleted' if active_chunks == 0 and deleted_chunks > 0 else 'active' if active_chunks > 0 else 'unknown'
        metadata = rows[0].get('metadata', {})
        original_file_name = rows[0].get('original_file_name')
        storage_bucket = rows[0].get('storage_bucket')
        storage_path = rows[0].get('storage_path')
        return {
            'original_file_id': original_file_id,
            'original_file_name': original_file_name,
            'storage_bucket': storage_bucket,
            'storage_path': storage_path,
            'total_chunks': total_chunks,
            'active_chunks': active_chunks,
            'deleted_chunks': deleted_chunks,
            'deleted_at': deleted_at,
            'last_ingested_at': last_ingested_at,
            'status': status,
            'metadata': metadata
        }

    def soft_delete_file(self, original_file_id: str, deleted_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Realiza exclusão suave de um arquivo.
        """
        rows = self.get_file_rows(original_file_id, include_deleted=False)
        if not rows:
            return {'original_file_id': original_file_id, 'affected_rows': 0, 'status': 'soft_deleted'}
        ids = [r['id'] for r in rows]
        now = self._utc_now_iso()
        update_data = {
            'deleted_at': now,
            'deleted_by': deleted_by,
            'deletion_reason': reason,
            'updated_at': now
        }
        affected_rows = 0
        for chunk in self._chunked_ids(ids):
            response = supabase.table('documents').update(update_data).in_('id', chunk).execute()
            affected_rows += len(self._safe_data(response))
        return {'original_file_id': original_file_id, 'affected_rows': affected_rows, 'status': 'soft_deleted'}

    def hard_delete_file(self, original_file_id: str) -> Dict[str, Any]:
        """
        Realiza exclusão definitiva de um arquivo.
        """
        summary = self.get_file_summary(original_file_id)
        if not summary:
            return {'original_file_id': original_file_id, 'deleted_rows': 0, 'storage_deleted': False, 'storage_bucket': None, 'storage_path': None, 'status': 'hard_deleted'}
        rows = self.get_file_rows(original_file_id, include_deleted=True)
        ids = [r['id'] for r in rows]
        storage_deleted = self.remove_storage_object(summary['storage_bucket'], summary['storage_path'])
        self.delete_ingestion_logs_by_file(original_file_id)
        deleted_rows = 0
        for chunk in self._chunked_ids(ids):
            response = supabase.table('documents').delete().in_('id', chunk).execute()
            deleted_rows += len(self._safe_data(response))
        return {
            'original_file_id': original_file_id,
            'deleted_rows': deleted_rows,
            'storage_deleted': storage_deleted,
            'storage_bucket': summary['storage_bucket'],
            'storage_path': summary['storage_path'],
            'status': 'hard_deleted'
        }

    def soft_delete_all(self, deleted_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Realiza exclusão suave de todos os arquivos ativos.
        """
        files = self.list_files()
        active_files = [f for f in files if f['status'] == 'active']
        total_affected = 0
        processed = []
        for file in active_files:
            result = self.soft_delete_file(file['original_file_id'], deleted_by, reason)
            total_affected += result['affected_rows']
            processed.append(result)
        return {
            'total_affected_rows': total_affected,
            'processed_files': processed,
            'status': 'soft_deleted_all'
        }

    def hard_delete_all(self) -> Dict[str, Any]:
        """
        Realiza exclusão definitiva de todos os arquivos.
        """
        files = self.list_files()
        total_deleted = 0
        processed = []
        for file in files:
            result = self.hard_delete_file(file['original_file_id'])
            total_deleted += result['deleted_rows']
            processed.append(result)
        logs_deleted = self.delete_all_ingestion_logs()
        return {
            'total_deleted_rows': total_deleted,
            'logs_deleted': logs_deleted,
            'processed_files': processed,
            'status': 'hard_deleted_all'
        }

    def list_reindexable_files(self, original_file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lista arquivos reindexáveis (ativos com storage).
        """
        files = self.list_files()
        reindexable = [f for f in files if f['status'] == 'active' and f['storage_bucket'] and f['storage_path']]
        if original_file_ids:
            reindexable = [f for f in reindexable if f['original_file_id'] in original_file_ids]
        return reindexable

    def delete_ingestion_logs_by_file(self, original_file_id: str) -> int:
        """
        Deleta logs de ingestão por arquivo.
        """
        response = supabase.table('rag_ingestion_logs').select('id').eq('original_file_id', original_file_id).execute()
        ids = [r['id'] for r in self._safe_data(response)]
        deleted = 0
        for chunk in self._chunked_ids(ids):
            response = supabase.table('rag_ingestion_logs').delete().in_('id', chunk).execute()
            deleted += len(self._safe_data(response))
        return deleted

    def delete_all_ingestion_logs(self) -> int:
        """
        Deleta todos os logs de ingestão.
        """
        response = supabase.table('rag_ingestion_logs').select('id').execute()
        ids = [r['id'] for r in self._safe_data(response)]
        deleted = 0
        for chunk in self._chunked_ids(ids):
            response = supabase.table('rag_ingestion_logs').delete().in_('id', chunk).execute()
            deleted += len(self._safe_data(response))
        return deleted

    def remove_storage_object(self, bucket: Optional[str], path: Optional[str]) -> bool:
        """
        Remove objeto do storage.
        """
        if not bucket or not path:
            return False
        try:
            supabase.storage.from_(bucket).remove([path])
            return True
        except Exception:
            return False