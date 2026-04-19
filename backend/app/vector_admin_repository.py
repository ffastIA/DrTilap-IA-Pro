# CAMINHO: backend/app/vector_admin_repository.py

from app.database import supabase_admin
from typing import List, Dict, Any, Optional
from datetime import datetime


class VectorAdminRepository:
    """
    Repositório para administração de vetores no Supabase.
    """

    def __init__(self):
        self.supabase = supabase_admin

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Lista todos os arquivos agregados por original_file_id.
        """
        rows = self._fetch_documents_rows()
        return self._aggregate_rows(rows)

    def get_file(self, original_file_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém os detalhes de um arquivo específico.
        """
        files = self.list_files()
        for file in files:
            if file['original_file_id'] == original_file_id:
                return file
        return None

    def purge_file(self, original_file_id: str) -> Dict[str, Any]:
        """
        Remove completamente um arquivo do sistema.
        """
        file_info = self.get_file(original_file_id)
        if not file_info:
            return {
                'original_file_id': original_file_id,
                'original_file_name': None,
                'documents_deleted': 0,
                'ingestion_logs_deleted': 0,
                'storage_deleted': False,
                'storage_bucket': None,
                'storage_path': None,
                'status': 'error',
                'message': 'Arquivo não encontrado.'
            }

        documents_deleted = self._delete_documents_by_original_file_id(original_file_id)
        ingestion_logs_deleted = self._delete_ingestion_logs_best_effort(original_file_id)
        storage_deleted = self._delete_storage_object(file_info.get('storage_bucket'), file_info.get('storage_path'))

        return {
            'original_file_id': original_file_id,
            'original_file_name': file_info.get('original_file_name'),
            'documents_deleted': documents_deleted,
            'ingestion_logs_deleted': ingestion_logs_deleted,
            'storage_deleted': storage_deleted,
            'storage_bucket': file_info.get('storage_bucket'),
            'storage_path': file_info.get('storage_path'),
            'status': 'success',
            'message': 'Arquivo removido com sucesso.'
        }

    def cleanup_vector_base(self) -> Dict[str, Any]:
        """
        Limpa a base de vetores removendo arquivos deletados.
        """
        files = self.list_files()
        total_files_processed = 0
        total_documents_deleted = 0
        total_ingestion_logs_deleted = 0
        total_storage_deleted = 0

        for file in files:
            if file.get('deleted_at'):
                result = self.purge_file(file['original_file_id'])
                total_files_processed += 1
                total_documents_deleted += result['documents_deleted']
                total_ingestion_logs_deleted += result['ingestion_logs_deleted']
                if result['storage_deleted']:
                    total_storage_deleted += 1

        return {
            'total_files_processed': total_files_processed,
            'total_documents_deleted': total_documents_deleted,
            'total_ingestion_logs_deleted': total_ingestion_logs_deleted,
            'total_storage_deleted': total_storage_deleted,
            'status': 'success',
            'message': 'Limpeza concluída.'
        }

    def list_reindexable_files(self, original_file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lista arquivos que podem ser reindexados.
        """
        files = self.list_files()
        if original_file_ids:
            files = [f for f in files if f['original_file_id'] in original_file_ids]
        return [f for f in files if f.get('status') == 'active']

    def get_document_chunks(self, original_file_id: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Obtém os chunks de um documento.
        """
        response = self.supabase.table('documents').select('*').eq('original_file_id', original_file_id)
        if not include_deleted:
            response = response.is_('deleted_at', None)
        rows = response.execute().data
        chunks = [self._normalize_document_row(row) for row in rows]
        return self._sort_chunks(chunks)

    def get_active_document_chunks(self, original_file_id: str) -> List[Dict[str, Any]]:
        """
        Obtém os chunks ativos de um documento.
        """
        return self.get_document_chunks(original_file_id, include_deleted=False)

    def rebuild_document_content(self, original_file_id: str, include_deleted: bool = False) -> Dict[str, Any]:
        """
        Reconstrói o conteúdo do documento a partir dos chunks.
        """
        chunks = self.get_document_chunks(original_file_id, include_deleted)
        content = ''.join([chunk.get('content', '') for chunk in chunks])
        return {
            'original_file_id': original_file_id,
            'content': content,
            'chunks': chunks
        }

    def get_file_recovery_diagnosis(self, original_file_id: str) -> Dict[str, Any]:
        """
        Diagnóstico de recuperação para um arquivo.
        """
        file_info = self.get_file(original_file_id)
        if not file_info:
            return {
                'original_file_id': original_file_id,
                'original_file_name': None,
                'total_chunks': 0,
                'active_chunks': 0,
                'deleted_chunks': 0,
                'has_table_data': False,
                'has_storage': False,
                'recoverable_from_table': False,
                'recoverable_from_storage': False,
                'recoverable_from_both': False,
                'recoverable_from_none': True,
                'status': 'error',
                'message': 'Arquivo não encontrado.'
            }

        total_chunks = file_info.get('total_chunks', 0)
        active_chunks = file_info.get('active_chunks', 0)
        deleted_chunks = file_info.get('deleted_chunks', 0)
        has_table_data = total_chunks > 0
        has_storage = self._check_storage_object_exists(file_info.get('storage_bucket'), file_info.get('storage_path'))
        recoverable_from_table = has_table_data
        recoverable_from_storage = has_storage
        recoverable_from_both = has_table_data and has_storage
        recoverable_from_none = not has_table_data and not has_storage

        return {
            'original_file_id': original_file_id,
            'original_file_name': file_info.get('original_file_name'),
            'total_chunks': total_chunks,
            'active_chunks': active_chunks,
            'deleted_chunks': deleted_chunks,
            'has_table_data': has_table_data,
            'has_storage': has_storage,
            'recoverable_from_table': recoverable_from_table,
            'recoverable_from_storage': recoverable_from_storage,
            'recoverable_from_both': recoverable_from_both,
            'recoverable_from_none': recoverable_from_none,
            'status': 'success',
            'message': 'Diagnóstico concluído.'
        }

    def _fetch_documents_rows(self) -> List[Dict[str, Any]]:
        """
        Busca todas as linhas da tabela documents.
        """
        return self.supabase.table('documents').select('*').execute().data

    def _aggregate_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agrega as linhas por original_file_id.
        """
        aggregated = {}
        for row in rows:
            oid = row.get('original_file_id')
            if oid not in aggregated:
                aggregated[oid] = {
                    'original_file_id': oid,
                    'original_file_name': row.get('original_file_name'),
                    'storage_bucket': row.get('storage_bucket'),
                    'storage_path': row.get('storage_path'),
                    'total_chunks': 0,
                    'active_chunks': 0,
                    'deleted_chunks': 0,
                    'deleted_at': None,
                    'last_ingested_at': None,
                    'status': 'active',
                    'metadata': {}
                }
            agg = aggregated[oid]
            agg['total_chunks'] += 1
            if row.get('deleted_at'):
                agg['deleted_chunks'] += 1
                agg['deleted_at'] = self._parse_datetime(row.get('deleted_at'))
            else:
                agg['active_chunks'] += 1
            ingested_at = self._parse_datetime(row.get('ingested_at'))
            if ingested_at and (not agg['last_ingested_at'] or ingested_at > agg['last_ingested_at']):
                agg['last_ingested_at'] = ingested_at
            agg['metadata'] = self._normalize_metadata(row.get('metadata'))
        return list(aggregated.values())

    def _delete_storage_object(self, bucket: Optional[str], path: Optional[str]) -> bool:
        """
        Deleta um objeto do storage.
        """
        if not bucket or not path:
            return False
        try:
            self.supabase.storage.from_(bucket).remove([path])
            return True
        except:
            return False

    def _delete_ingestion_logs_best_effort(self, original_file_id: str) -> int:
        """
        Deleta logs de ingestão.
        """
        try:
            response = self.supabase.table('ingestion_logs').delete().eq('original_file_id', original_file_id).execute()
            return len(response.data)
        except:
            return 0

    def _delete_documents_by_original_file_id(self, original_file_id: str) -> int:
        """
        Deleta documentos por original_file_id.
        """
        response = self.supabase.table('documents').delete().eq('original_file_id', original_file_id).execute()
        return len(response.data)

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string para datetime.
        """
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None

    def _normalize_metadata(self, metadata: Any) -> Dict[str, Any]:
        """
        Normaliza metadata.
        """
        if isinstance(metadata, dict):
            return metadata
        return {}

    def _normalize_document_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza uma linha de documento.
        """
        return {
            'id': row.get('id'),
            'original_file_id': row.get('original_file_id'),
            'content': row.get('content', ''),
            'metadata': self._normalize_metadata(row.get('metadata')),
            'deleted_at': row.get('deleted_at'),
            'ingested_at': row.get('ingested_at')
        }

    def _extract_page(self, metadata: Dict[str, Any]) -> int:
        """
        Extrai o número da página.
        """
        return metadata.get('page', 0)

    def _extract_chunk_index(self, metadata: Dict[str, Any]) -> int:
        """
        Extrai o índice do chunk.
        """
        return metadata.get('chunk_index', 0)

    def _sort_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ordena os chunks por página e índice.
        """
        return sorted(chunks, key=lambda c: (self._extract_page(c.get('metadata', {})), self._extract_chunk_index(c.get('metadata', {}))))

    def _check_storage_object_exists(self, bucket: Optional[str], path: Optional[str]) -> bool:
        """
        Verifica se um objeto existe no storage.
        """
        if not bucket or not path:
            return False
        try:
            self.supabase.storage.from_(bucket).list(path=path)
            return True
        except:
            return False