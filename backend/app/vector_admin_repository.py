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
        Retorna o timestamp UTC atual em formato ISO.
        """
        return datetime.now(timezone.utc).isoformat()

    def _safe_data(self, response) -> List[Dict[str, Any]]:
        """
        Extrai dados seguros da resposta do Supabase, retornando lista vazia se erro.
        """
        if response and hasattr(response, 'data') and response.data:
            return response.data
        return []

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

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Lista arquivos agrupados por original_file_id com resumos calculados.
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
            deleted_at = min((r['deleted_at'] for r in file_rows if r.get('deleted_at')), default=None)
            last_ingested_at = max((r['created_at'] for r in file_rows if r.get('created_at')), default=None)
            status = 'deleted' if active_chunks == 0 and deleted_chunks > 0 else 'active' if active_chunks > 0 else 'unknown'
            # Pegar dados do primeiro row para campos comuns
            first_row = file_rows[0]
            files.append({
                'original_file_id': file_id,
                'original_file_name': first_row.get('original_file_name'),
                'storage_bucket': first_row.get('storage_bucket'),
                'storage_path': first_row.get('storage_path'),
                'total_chunks': total_chunks,
                'active_chunks': active_chunks,
                'deleted_chunks': deleted_chunks,
                'deleted_at': deleted_at,
                'last_ingested_at': last_ingested_at,
                'status': status,
                'metadata': first_row.get('metadata')
            })
        # Ordenar por original_file_name
        files.sort(key=lambda x: x['original_file_name'] or '')
        return files

    def get_file_rows(self, original_file_id: str, include_deleted: bool = True) -> List[Dict[str, Any]]:
        """
        Retorna todas as linhas de um arquivo, opcionalmente incluindo deletadas.
        """
        response = supabase.table('documents').select('*').eq('original_file_id', original_file_id).execute()
        rows = self._safe_data(response)
        if not include_deleted:
            rows = [r for r in rows if r.get('deleted_at') is None]
        return rows

    def get_file_summary(self, original_file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retorna resumo de um arquivo usando get_file_rows.
        """
        rows = self.get_file_rows(original_file_id, include_deleted=True)
        if not rows:
            return None
        total_chunks = len(rows)
        active_chunks = sum(1 for r in rows if r.get('deleted_at') is None)
        deleted_chunks = total_chunks - active_chunks
        deleted_at = min((r['deleted_at'] for r in rows if r.get('deleted_at')), default=None)
        last_ingested_at = max((r['created_at'] for r in rows if r.get('created_at')), default=None)
        status = 'deleted' if active_chunks == 0 and deleted_chunks > 0 else 'active' if active_chunks > 0 else 'unknown'
        first_row = rows[0]
        return {
            'original_file_id': original_file_id,
            'original_file_name': first_row.get('original_file_name'),
            'storage_bucket': first_row.get('storage_bucket'),
            'storage_path': first_row.get('storage_path'),
            'total_chunks': total_chunks,
            'active_chunks': active_chunks,
            'deleted_chunks': deleted_chunks,
            'deleted_at': deleted_at,
            'last_ingested_at': last_ingested_at,
            'status': status,
            'metadata': first_row.get('metadata')
        }

    def soft_delete_file(self, original_file_id: str, deleted_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Faz soft delete das linhas ativas de um arquivo.
        """
        rows = self.get_file_rows(original_file_id, include_deleted=False)
        if not rows:
            return {'original_file_id': original_file_id, 'affected_rows': 0, 'status': 'soft_deleted'}
        ids = [r['id'] for r in rows]
        now = self._utc_now_iso()
        # Atualizar em lotes (simples, um por vez para conservadorismo)
        affected = 0
        for row_id in ids:
            supabase.table('documents').update({
                'deleted_at': now,
                'deleted_by': deleted_by,
                'deletion_reason': reason
            }).eq('id', row_id).execute()
            affected += 1
        return {'original_file_id': original_file_id, 'affected_rows': affected, 'status': 'soft_deleted'}

    def hard_delete_file(self, original_file_id: str) -> Dict[str, Any]:
        """
        Faz hard delete de um arquivo, removendo do storage e logs.
        """
        summary = self.get_file_summary(original_file_id)
        if not summary:
            return {'original_file_id': original_file_id, 'deleted_rows': 0, 'storage_deleted': False, 'storage_bucket': None, 'storage_path': None, 'status': 'hard_deleted'}
        rows = self.get_file_rows(original_file_id, include_deleted=True)
        ids = [r['id'] for r in rows]
        # Remover do storage
        bucket = summary.get('storage_bucket')
        path = summary.get('storage_path')
        storage_deleted = self.remove_storage_object(bucket, path)
        # Deletar logs
        self.delete_ingestion_logs_by_file(original_file_id)
        # Deletar rows em lotes
        deleted_rows = 0
        for row_id in ids:
            supabase.table('documents').delete().eq('id', row_id).execute()
            deleted_rows += 1
        return {
            'original_file_id': original_file_id,
            'deleted_rows': deleted_rows,
            'storage_deleted': storage_deleted,
            'storage_bucket': bucket,
            'storage_path': path,
            'status': 'hard_deleted'
        }

    def soft_delete_all(self, deleted_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Faz soft delete de todos os arquivos ativos.
        """
        files = self.list_files()
        active_files = [f for f in files if f['status'] == 'active']
        total_affected = 0
        deleted_list = []
        for file in active_files:
            result = self.soft_delete_file(file['original_file_id'], deleted_by, reason)
            total_affected += result['affected_rows']
            deleted_list.append(result)
        return {
            'total_files': len(active_files),
            'total_affected_rows': total_affected,
            'deleted_files': deleted_list,
            'status': 'soft_deleted_all'
        }

    def hard_delete_all(self) -> Dict[str, Any]:
        """
        Faz hard delete de todos os arquivos.
        """
        files = self.list_files()
        total_deleted_rows = 0
        deleted_list = []
        for file in files:
            result = self.hard_delete_file(file['original_file_id'])
            total_deleted_rows += result['deleted_rows']
            deleted_list.append(result)
        # Deletar todos os logs
        logs_deleted = self.delete_all_ingestion_logs()
        return {
            'total_files': len(files),
            'total_deleted_rows': total_deleted_rows,
            'logs_deleted': logs_deleted,
            'deleted_files': deleted_list,
            'status': 'hard_deleted_all'
        }

    def list_reindexable_files(self, original_file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lista arquivos ativos com storage preenchido, opcionalmente filtrados por IDs.
        """
        files = self.list_files()
        reindexable = [f for f in files if f['status'] == 'active' and f.get('storage_bucket') and f.get('storage_path')]
        if original_file_ids:
            reindexable = [f for f in reindexable if f['original_file_id'] in original_file_ids]
        return reindexable

    def delete_ingestion_logs_by_file(self, original_file_id: str) -> int:
        """
        Deleta logs de ingestão por arquivo.
        """
        response = supabase.table('rag_ingestion_logs').select('id').eq('original_file_id', original_file_id).execute()
        logs = self._safe_data(response)
        ids = [l['id'] for l in logs]
        deleted = 0
        for log_id in ids:
            supabase.table('rag_ingestion_logs').delete().eq('id', log_id).execute()
            deleted += 1
        return deleted

    def delete_all_ingestion_logs(self) -> int:
        """
        Deleta todos os logs de ingestão.
        """
        response = supabase.table('rag_ingestion_logs').select('id').execute()
        logs = self._safe_data(response)
        ids = [l['id'] for l in logs]
        deleted = 0
        for log_id in ids:
            supabase.table('rag_ingestion_logs').delete().eq('id', log_id).execute()
            deleted += 1
        return deleted

    def remove_storage_object(self, bucket: Optional[str], path: Optional[str]) -> bool:
        """
        Remove objeto do storage, retornando False se bucket/path faltarem ou erro.
        """
        if not bucket or not path:
            return False
        try:
            supabase.storage.from_(bucket).remove([path])
            return True
        except Exception:
            return False