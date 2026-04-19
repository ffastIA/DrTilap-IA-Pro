# CAMINHO: backend/app/vector_admin_repository.py

import logging
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime
import os.path

from app.database import supabase_admin


class VectorAdminRepository:
    """
    Repositório para operações administrativas na base vetorial.

    Este repositório gerencia arquivos e chunks na tabela 'documents',
    sendo tolerante a dados legados e focado em compatibilidade com endpoints administrativos.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _safe_metadata(self, metadata: Any) -> Dict[str, Any]:
        """
        Trata o campo metadata com segurança, retornando um dict válido.
        """
        if metadata is None:
            return {}
        if isinstance(metadata, dict):
            return metadata
        if isinstance(metadata, str):
            try:
                return json.loads(metadata)
            except json.JSONDecodeError:
                self.logger.warning(f"Falha ao parsear metadata como JSON: {metadata}")
                return {}
        self.logger.warning(f"Tipo inválido para metadata: {type(metadata)}, usando {{}}")
        return {}

    def _get_first_non_empty(self, *values: Optional[str]) -> Optional[str]:
        """
        Retorna o primeiro valor não vazio da lista.
        """
        for value in values:
            if value and isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _normalize_datetime(self, dt: Any) -> Optional[datetime]:
        """
        Normaliza um valor para datetime, se possível.
        """
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, str):
            try:
                return datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                pass
        return None

    def _datetime_to_iso(self, dt: Optional[datetime]) -> Optional[str]:
        """
        Converte datetime para string ISO, se não for None.
        """
        return dt.isoformat() if dt else None

    def _coerce_int(self, value: Any) -> Optional[int]:
        """
        Tenta converter valor para int, retornando None se falhar.
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _extract_document_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai campos de uma linha de documento com fallbacks.
        """
        metadata = self._safe_metadata(row.get('metadata'))

        original_file_id = row.get('original_file_id') or metadata.get('original_file_id')
        original_file_name = self._get_first_non_empty(
            row.get('original_file_name'),
            metadata.get('original_file_name'),
            metadata.get('source'),
            metadata.get('file_name'),
            metadata.get('filename'),
            os.path.basename(metadata.get('storage_path', '')) if metadata.get('storage_path') else None
        )
        storage_bucket = row.get('storage_bucket') or metadata.get('storage_bucket')
        storage_path = row.get('storage_path') or metadata.get('storage_path')
        deleted_at = self._normalize_datetime(row.get('deleted_at') or metadata.get('deleted_at'))
        last_ingested_at = self._normalize_datetime(row.get('last_ingested_at') or metadata.get('last_ingested_at'))
        page = self._coerce_int(row.get('page') or metadata.get('page'))
        chunk_index = self._coerce_int(row.get('chunk_index') or metadata.get('chunk_index'))
        id_ = row.get('id')
        content = row.get('content') or metadata.get('content') or ''
        created_at = self._normalize_datetime(row.get('created_at'))
        updated_at = self._normalize_datetime(row.get('updated_at'))

        return {
            'original_file_id': original_file_id,
            'original_file_name': original_file_name,
            'storage_bucket': storage_bucket,
            'storage_path': storage_path,
            'deleted_at': deleted_at,
            'last_ingested_at': last_ingested_at,
            'page': page,
            'chunk_index': chunk_index,
            'id': id_,
            'content': content,
            'created_at': created_at,
            'updated_at': updated_at,
            'metadata': metadata
        }

    def _fetch_document_rows(self) -> List[Dict[str, Any]]:
        """
        Busca todas as linhas da tabela documents.
        """
        try:
            response = supabase_admin.table("documents").select("*").execute()
            return response.data or []
        except Exception as e:
            self.logger.error(f"Erro ao buscar documentos: {e}")
            raise

    def _group_valid_rows_by_file(self, rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa linhas válidas por original_file_id, ignorando inválidas.
        """
        grouped = defaultdict(list)
        for row in rows:
            fields = self._extract_document_fields(row)
            if fields['original_file_id'] and fields['original_file_name']:
                grouped[fields['original_file_id']].append(fields)
        return dict(grouped)

    def _build_file_summary(self, file_id: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Constrói resumo de arquivo para list_files.
        """
        total_chunks = len(chunks)
        active_chunks = sum(1 for c in chunks if not c['deleted_at'])
        deleted_chunks = total_chunks - active_chunks

        # Usar dados do primeiro chunk como base
        first = chunks[0] if chunks else {}

        return {
            'original_file_id': file_id,
            'original_file_name': first.get('original_file_name'),
            'storage_bucket': first.get('storage_bucket'),
            'storage_path': first.get('storage_path'),
            'total_chunks': total_chunks,
            'active_chunks': active_chunks,
            'deleted_chunks': deleted_chunks,
            'deleted_at': self._datetime_to_iso(first.get('deleted_at')),
            'last_ingested_at': self._datetime_to_iso(first.get('last_ingested_at')),
            'status': 'active' if active_chunks > 0 else 'deleted',
            'metadata': first.get('metadata', {})
        }

    def _build_chunk_item(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Constrói item de chunk para get_file_chunks.
        """
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
            'chunk_index': chunk['chunk_index']
        }

    def _best_effort_delete_ingestion_logs(self, original_file_id: str) -> int:
        """
        Tenta deletar logs de ingestão, ignorando tabelas ausentes.
        """
        deleted = 0
        for table in ['ingestion_logs', 'rag_ingestion_logs']:
            try:
                response = supabase_admin.table(table).delete().eq('original_file_id', original_file_id).execute()
                deleted += len(response.data or [])
            except Exception as e:
                self.logger.warning(f"Falha ao deletar de {table}: {e}")
        return deleted

    def list_files(self) -> List[Dict[str, Any]]:
        """
        Lista arquivos válidos com resumos.
        """
        rows = self._fetch_document_rows()
        grouped = self._group_valid_rows_by_file(rows)
        return [self._build_file_summary(fid, chunks) for fid, chunks in grouped.items()]

    def get_file(self, original_file_id: str) -> Dict[str, Any]:
        """
        Obtém resumo de um arquivo específico.
        """
        rows = self._fetch_document_rows()
        grouped = self._group_valid_rows_by_file(rows)
        if original_file_id not in grouped:
            raise ValueError(f"Arquivo não encontrado: {original_file_id}")
        chunks = grouped[original_file_id]
        return self._build_file_summary(original_file_id, chunks)

    def get_file_chunks(self, original_file_id: str) -> Dict[str, Any]:
        """
        Retorna chunks de um arquivo, compatível com endpoint administrativo.
        """
        file_summary = self.get_file(original_file_id)
        rows = self._fetch_document_rows()
        grouped = self._group_valid_rows_by_file(rows)
        chunks_data = grouped[original_file_id]

        # Ordenar chunks
        def sort_key(c):
            return (c['page'] or 0, c['chunk_index'] or 0, c['created_at'] or datetime.min)

        chunks_data.sort(key=sort_key)

        chunks = [self._build_chunk_item(c) for c in chunks_data]

        return {
            'original_file_id': original_file_id,
            'original_file_name': file_summary['original_file_name'],
            'total_chunks': file_summary['total_chunks'],
            'active_chunks': file_summary['active_chunks'],
            'deleted_chunks': file_summary['deleted_chunks'],
            'chunks': chunks,
            'status': 'success',
            'message': f"Chunks recuperados para {original_file_id}"
        }

    def recover_file_content(self, original_file_id: str) -> Dict[str, Any]:
        """
        Reconstrói conteúdo de arquivo a partir de chunks ativos.
        """
        file_summary = self.get_file(original_file_id)
        rows = self._fetch_document_rows()
        grouped = self._group_valid_rows_by_file(rows)
        chunks_data = grouped[original_file_id]

        # Filtrar chunks ativos com conteúdo
        active_chunks = [c for c in chunks_data if not c['deleted_at'] and c['content']]

        # Ordenar
        def sort_key(c):
            return (c['page'] or 0, c['chunk_index'] or 0, c['created_at'] or datetime.min)

        active_chunks.sort(key=sort_key)

        # Reconstruir conteúdo
        content = '\n'.join(c['content'] for c in active_chunks)

        chunks = [self._build_chunk_item(c) for c in active_chunks]

        return {
            'original_file_id': original_file_id,
            'original_file_name': file_summary['original_file_name'],
            'storage_bucket': file_summary['storage_bucket'],
            'storage_path': file_summary['storage_path'],
            'total_chunks': file_summary['total_chunks'],
            'active_chunks': file_summary['active_chunks'],
            'deleted_chunks': file_summary['deleted_chunks'],
            'content': content,
            'chunks': chunks,
            'status': 'success',
            'message': f"Conteúdo recuperado para {original_file_id}"
        }

    def diagnose_file_recovery(self, original_file_id: str) -> Dict[str, Any]:
        """
        Diagnóstica possibilidades de recuperação de arquivo.
        """
        file_summary = self.get_file(original_file_id)

        # Simulação simples: assumir que se há chunks ativos, é recuperável da tabela
        has_table_data = file_summary['active_chunks'] > 0
        has_storage = bool(file_summary['storage_bucket'] and file_summary['storage_path'])
        recoverable_from_table = has_table_data
        recoverable_from_storage = has_storage  # Assumindo que storage existe se campos preenchidos
        recoverable_from_both = recoverable_from_table and recoverable_from_storage
        recoverable_from_none = not (recoverable_from_table or recoverable_from_storage)

        return {
            'original_file_id': original_file_id,
            'original_file_name': file_summary['original_file_name'],
            'total_chunks': file_summary['total_chunks'],
            'active_chunks': file_summary['active_chunks'],
            'deleted_chunks': file_summary['deleted_chunks'],
            'has_table_data': has_table_data,
            'has_storage': has_storage,
            'recoverable_from_table': recoverable_from_table,
            'recoverable_from_storage': recoverable_from_storage,
            'recoverable_from_both': recoverable_from_both,
            'recoverable_from_none': recoverable_from_none,
            'status': 'success',
            'message': f"Diagnóstico para {original_file_id}"
        }

    def delete_file(self, original_file_id: str, confirmation_phrase: str, reason: Optional[str] = None,
                    hard_delete: bool = True) -> Dict[str, Any]:
        """
        Deleta arquivo, incluindo dados e storage se hard_delete.
        """
        file_summary = self.get_file(original_file_id)

        # Deletar documents
        response = supabase_admin.table("documents").delete().eq('original_file_id', original_file_id).execute()
        documents_deleted = len(response.data or [])

        # Deletar logs
        ingestion_logs_deleted = self._best_effort_delete_ingestion_logs(original_file_id)

        # Deletar storage
        storage_deleted = False
        if hard_delete and file_summary['storage_bucket'] and file_summary['storage_path']:
            try:
                supabase_admin.storage.from_(file_summary['storage_bucket']).remove([file_summary['storage_path']])
                storage_deleted = True
            except Exception as e:
                self.logger.warning(f"Falha ao deletar storage: {e}")

        return {
            'original_file_id': original_file_id,
            'original_file_name': file_summary['original_file_name'],
            'documents_deleted': documents_deleted,
            'ingestion_logs_deleted': ingestion_logs_deleted,
            'storage_deleted': storage_deleted,
            'storage_bucket': file_summary['storage_bucket'],
            'storage_path': file_summary['storage_path'],
            'status': 'success',
            'message': f"Arquivo deletado: {original_file_id}"
        }

    def cleanup_vector_base(self, confirmation_phrase: str) -> Dict[str, Any]:
        """
        Limpa base vetorial, deletando todos os arquivos válidos.
        """
        files = self.list_files()
        total_files_processed = len(files)
        total_documents_deleted = 0
        total_ingestion_logs_deleted = 0
        total_storage_deleted = 0

        for file in files:
            fid = file['original_file_id']
            try:
                result = self.delete_file(fid, confirmation_phrase, hard_delete=True)
                total_documents_deleted += result['documents_deleted']
                total_ingestion_logs_deleted += result['ingestion_logs_deleted']
                total_storage_deleted += 1 if result['storage_deleted'] else 0
            except Exception as e:
                self.logger.error(f"Erro ao deletar {fid}: {e}")

        return {
            'total_files_processed': total_files_processed,
            'total_documents_deleted': total_documents_deleted,
            'total_ingestion_logs_deleted': total_ingestion_logs_deleted,
            'total_storage_deleted': total_storage_deleted,
            'status': 'success',
            'message': "Limpeza da base vetorial concluída"
        }