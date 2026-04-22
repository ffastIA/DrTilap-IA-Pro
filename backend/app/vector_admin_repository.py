# CAMINHO: backend/app/vector_admin_repository.py

import logging
import json
import os.path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from app.database import supabase_admin


class VectorAdminRepository:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.CONFIRMAR_EXCLUSAO = 'CONFIRMAR_EXCLUSAO'
        self.CONFIRMAR_LIMPEZA_TOTAL = 'CONFIRMAR_LIMPEZA_TOTAL'

    def _safe_metadata(self, metadata: Any) -> Dict[str, Any]:
        if metadata is None:
            return {}
        if isinstance(metadata, dict):
            return metadata
        if isinstance(metadata, str):
            try:
                return json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    def _get_first_non_empty(self, *values: Any) -> Optional[str]:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _normalize_datetime(self, dt: Any) -> Optional[datetime]:
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, str):
            dt_str = dt.replace('Z', '+00:00')
            try:
                return datetime.fromisoformat(dt_str)
            except ValueError:
                pass
        return None

    def _datetime_to_iso(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    def _coerce_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _extract_document_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        metadata = self._safe_metadata(row.get('metadata'))
        original_file_id = row.get('original_file_id') or metadata.get('original_file_id')
        original_file_name_candidates = [
            row.get('original_file_name'),
            metadata.get('original_file_name'),
            metadata.get('source'),
            os.path.basename(row.get('storage_path') or '')
        ]
        original_file_name = self._get_first_non_empty(*original_file_name_candidates)
        deleted_at = self._normalize_datetime(row.get('deleted_at'))
        created_at = self._normalize_datetime(row.get('created_at'))
        updated_at = self._normalize_datetime(row.get('updated_at'))
        last_ingested_at = None
        candidates = [
            row.get('last_ingested_at'),
            metadata.get('last_ingested_at'),
            row.get('updated_at'),
            row.get('created_at')
        ]
        for cand in candidates:
            dt = self._normalize_datetime(cand)
            if dt:
                last_ingested_at = dt
                break
        page = self._coerce_int(metadata.get('page'))
        chunk_index = self._coerce_int(metadata.get('chunk_index'))
        return {
            'id': row.get('id'),
            'content': row.get('content'),
            'metadata': metadata,
            'original_file_id': original_file_id,
            'original_file_name': original_file_name,
            'storage_bucket': row.get('storage_bucket'),
            'storage_path': row.get('storage_path'),
            'deleted_at': deleted_at,
            'created_at': created_at,
            'updated_at': updated_at,
            'last_ingested_at': last_ingested_at,
            'page': page,
            'chunk_index': chunk_index,
        }

    def _fetch_all_documents(self) -> List[Dict[str, Any]]:
        response = supabase_admin.table('documents').select('*').execute()
        return response.data or []

    def _group_valid_rows_by_file(self, rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            extracted = self._extract_document_fields(row)
            if extracted['original_file_id'] and extracted['original_file_name']:
                groups[extracted['original_file_id']].append(extracted)
        return dict(groups)

    def _build_file_summary(self, file_id: str, chunks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not chunks:
            return None
        total_chunks = len(chunks)
        active_chunks_count = sum(1 for chunk in chunks if chunk['deleted_at'] is None)
        deleted_chunks = total_chunks - active_chunks_count
        first = chunks[0]
        # Maior last_ingested_at por chunk
        max_last_ingested = None
        max_deleted_at = None
        for chunk in chunks:
            cand_dates = [chunk['last_ingested_at'], chunk['updated_at'], chunk['created_at']]
            for cd in cand_dates:
                if cd and (max_last_ingested is None or cd > max_last_ingested):
                    max_last_ingested = cd
                    break
            if chunk['deleted_at'] and (max_deleted_at is None or chunk['deleted_at'] > max_deleted_at):
                max_deleted_at = chunk['deleted_at']
        status = 'active' if active_chunks_count > 0 else 'deleted'
        summary_metadata = {
            'source': first['original_file_name'],
            'total_chunks': total_chunks,
            'active_chunks': active_chunks_count,
            'deleted_chunks': deleted_chunks,
        }
        return {
            'original_file_id': file_id,
            'original_file_name': first['original_file_name'],
            'storage_bucket': first['storage_bucket'],
            'storage_path': first['storage_path'],
            'total_chunks': total_chunks,
            'active_chunks': active_chunks_count,
            'deleted_chunks': deleted_chunks,
            'deleted_at': self._datetime_to_iso(max_deleted_at),
            'last_ingested_at': self._datetime_to_iso(max_last_ingested),
            'status': status,
            'metadata': summary_metadata,
        }

    def _build_chunk_item(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': str(chunk['id']),
            'content': chunk['content'],
            'metadata': chunk['metadata'],
            'original_file_id': chunk['original_file_id'],
            'original_file_name': chunk['original_file_name'],
            'storage_bucket': chunk['storage_bucket'],
            'storage_path': chunk['storage_path'],
            'deleted_at': self._datetime_to_iso(chunk['deleted_at']),
            'created_at': self._datetime_to_iso(chunk['created_at']),
            'updated_at': self._datetime_to_iso(chunk['updated_at']),
            'page': chunk['page'],
            'chunk_index': chunk['chunk_index'],
        }

    def list_files(self) -> List[Dict[str, Any]]:
        all_docs = self._fetch_all_documents()
        grouped = self._group_valid_rows_by_file(all_docs)
        summaries = [
            self._build_file_summary(file_id, chunks)
            for file_id, chunks in grouped.items()
            if self._build_file_summary(file_id, chunks)
        ]
        # Ordenar por last_ingested_at descendente (ISO str funciona), None por último
        summaries.sort(key=lambda s: s.get('last_ingested_at', ''), reverse=True)
        return summaries

    def get_file(self, original_file_id: str) -> Dict[str, Any]:
        files = self.list_files()
        for f in files:
            if f['original_file_id'] == original_file_id:
                return f
        raise ValueError(f'Arquivo não encontrado: {original_file_id}')

    def get_file_chunks(self, original_file_id: str) -> Dict[str, Any]:
        all_docs = self._fetch_all_documents()
        extracted = []
        for row in all_docs:
            ext = self._extract_document_fields(row)
            if ext['original_file_id'] == original_file_id:
                extracted.append(ext)
        # Ordenar: chunk_index (None último), page (None último), created_at (None último, asc)
        def chunk_sort_key(c):
            return (
                (0 if c['chunk_index'] is not None else 1, c['chunk_index'] or 0),
                (0 if c['page'] is not None else 1, c['page'] or 0),
                (0 if c['created_at'] is not None else 1, c['created_at'].timestamp() if c['created_at'] else 0)
            )
        extracted.sort(key=chunk_sort_key)
        total_chunks = len(extracted)
        active_chunks_count = sum(1 for c in extracted if c['deleted_at'] is None)
        deleted_chunks = total_chunks - active_chunks_count
        original_file_name = extracted[0]['original_file_name'] if extracted else None
        chunks = [self._build_chunk_item(c) for c in extracted]
        return {
            'original_file_id': original_file_id,
            'original_file_name': original_file_name,
            'total_chunks': total_chunks,
            'active_chunks': active_chunks_count,
            'deleted_chunks': deleted_chunks,
            'chunks': chunks,
            'status': 'success',
            'message': 'Chunks recuperados com sucesso'
        }

    def recover_file_content(self, original_file_id: str) -> Dict[str, Any]:
        chunk_data = self.get_file_chunks(original_file_id)
        active_chunks = [c for c in chunk_data['chunks'] if c['deleted_at'] is None]
        if active_chunks:
            recovered_content = '\n\n'.join(c['content'] for c in active_chunks)
        else:
            recovered_content = '\n\n'.join(c['content'] for c in chunk_data['chunks'])
        return {
            'original_file_id': original_file_id,
            'original_file_name': chunk_data['original_file_name'],
            'recovered_content': recovered_content,
            'status': 'success',
            'message': 'Conteúdo do arquivo recuperado com sucesso.'
        }

    def diagnose_file_recovery(self, original_file_id: str) -> Dict[str, Any]:
        chunk_data = self.get_file_chunks(original_file_id)
        chunks = chunk_data['chunks']
        total_chunks = len(chunks)
        active_chunks_count = sum(1 for c in chunks if c['deleted_at'] is None)
        deleted_chunks = total_chunks - active_chunks_count
        has_table_data = total_chunks > 0
        has_storage = bool(chunk_data.get('storage_bucket') and chunk_data.get('storage_path'))
        recoverable_from_table = active_chunks_count > 0
        recoverable_from_storage = has_storage
        recoverable_from_both = recoverable_from_table and recoverable_from_storage
        recoverable_from_none = not recoverable_from_table and not recoverable_from_storage
        return {
            'original_file_id': original_file_id,
            'original_file_name': chunk_data['original_file_name'],
            'total_chunks': total_chunks,
            'active_chunks': active_chunks_count,
            'deleted_chunks': deleted_chunks,
            'has_table_data': has_table_data,
            'has_storage': has_storage,
            'recoverable_from_table': recoverable_from_table,
            'recoverable_from_storage': recoverable_from_storage,
            'recoverable_from_both': recoverable_from_both,
            'recoverable_from_none': recoverable_from_none,
            'status': 'success',
            'message': 'Diagnóstico recuperado com sucesso'
        }

    def _best_effort_delete_ingestion_logs(self, original_file_id: str) -> int:
        total_deleted = 0
        for table_name in ['ingestion_logs', 'rag_ingestion_logs']:
            try:
                response = supabase_admin.table(table_name).delete().eq('original_file_id', original_file_id).execute()
                deleted_count = len(response.data or [])
                total_deleted += deleted_count
                self.logger.info(f'Deletados {deleted_count} logs da tabela {table_name}')
            except Exception as e:
                self.logger.warning(f'Falha ao deletar logs da tabela {table_name}: {e}')
        return total_deleted

    def delete_file(self, original_file_id: str, confirmation_phrase: str, reason: Optional[str] = None, hard_delete: bool = True) -> Dict[str, Any]:
        if confirmation_phrase != self.CONFIRMAR_EXCLUSAO:
            raise ValueError('Frase de confirmação inválida')
        file_summary = self.get_file(original_file_id)
        # Deletar documents
        response = supabase_admin.table('documents').delete().eq('original_file_id', original_file_id).execute()
        documents_deleted = len(response.data or [])
        # Deletar logs
        ingestion_logs_deleted = self._best_effort_delete_ingestion_logs(original_file_id)
        # Deletar storage se aplicável
        storage_deleted = False
        storage_bucket = file_summary['storage_bucket']
        storage_path = file_summary['storage_path']
        if hard_delete and storage_bucket and storage_path:
            try:
                resp_storage = supabase_admin.storage.from_(storage_bucket).remove(storage_path)
                storage_deleted = 'error' not in resp_storage
                self.logger.info(f'Storage deletado: {storage_path} de {storage_bucket}')
            except Exception as e:
                self.logger.error(f'Falha ao deletar storage {storage_path}: {e}')
                storage_deleted = False
        message = f'Arquivo deletado. {documents_deleted} documentos, {ingestion_logs_deleted} logs de ingestão.'
        if storage_deleted:
            message += ' Storage removido.'
        return {
            'original_file_id': original_file_id,
            'original_file_name': file_summary['original_file_name'],
            'documents_deleted': documents_deleted,
            'ingestion_logs_deleted': ingestion_logs_deleted,
            'storage_deleted': storage_deleted,
            'storage_bucket': storage_bucket,
            'storage_path': storage_path,
            'status': 'success',
            'message': message
        }

    def cleanup_vector_base(self, confirmation_phrase: str) -> Dict[str, Any]:
        if confirmation_phrase != self.CONFIRMAR_LIMPEZA_TOTAL:
            raise ValueError('Frase de confirmação inválida para limpeza total')
        files = self.list_files()
        total_files_processed = len(files)
        total_documents_deleted = 0
        total_ingestion_logs_deleted = 0
        total_storage_deleted = 0
        for file_info in files:
            try:
                del_resp = self.delete_file(
                    file_info['original_file_id'],
                    self.CONFIRMAR_EXCLUSAO,
                    hard_delete=True
                )
                total_documents_deleted += del_resp['documents_deleted']
                total_ingestion_logs_deleted += del_resp['ingestion_logs_deleted']
                if del_resp['storage_deleted']:
                    total_storage_deleted += 1
            except Exception as e:
                self.logger.error(f'Falha ao deletar arquivo {file_info["original_file_id"]}: {e}')
        message = (
            f'Limpeza total concluída. '
            f'Processados: {total_files_processed} arquivos, '
            f'deletados: {total_documents_deleted} docs, '
            f'{total_ingestion_logs_deleted} logs, '
            f'{total_storage_deleted} storages.'
        )
        return {
            'total_files_processed': total_files_processed,
            'total_documents_deleted': total_documents_deleted,
            'total_ingestion_logs_deleted': total_ingestion_logs_deleted,
            'total_storage_deleted': total_storage_deleted,
            'status': 'success',
            'message': message
        }


vector_admin_repository = VectorAdminRepository()
