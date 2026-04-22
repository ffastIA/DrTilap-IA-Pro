// CAMINHO: frontend/lib/ragAdminApi.ts

import api from '@/lib/api';
import type { RagAdminError, RagClearResponse, RagDeletePayload, RagDeleteResponse, RagItem, RagListResponse, RagReindexPayload, RagReindexResponse, RagUploadResponse } from '@/types/rag-admin';

export const RAG_ADMIN_ENDPOINTS = {
  LIST: '/admin/vector-base/files',
  UPLOAD: '/admin/upload',
  DELETE_BASE: '/admin/vector-base/files',
  CLEAR: '/admin/vector-base/cleanup',
  REINDEX: '/admin/vector-base/reindex',
} as const;

export type RagOperationStatusResponse = { status: 'completed' | 'in_progress' | 'failed'; progress?: number; message?: string; jobId?: string };

// Helper functions
function extractBody<T>(response: any): T {
  return response.data || response;
}

function getFirstDefined<T>(...values: (T | undefined | null)[]): T | undefined {
  return values.find(v => v !== undefined && v !== null);
}

function toDate(value: any): Date {
  if (value instanceof Date) return value;
  if (typeof value === 'string' || typeof value === 'number') {
    const date = new Date(value);
    return isNaN(date.getTime()) ? new Date(0) : date;
  }
  return new Date(0);
}

function normalizeItem(raw: any): RagItem | null {
  const id = getFirstDefined(raw.original_file_id, raw.id, raw.file_id, raw.document_id);
  if (!id || typeof id !== 'string' || id.trim() === '') return null;

  const title = getFirstDefined(raw.original_file_name, raw.filename, raw.file_name, raw.title, raw.name) || 'Sem título';
  const content = getFirstDefined(raw.content, raw.summary, raw.text) || '';
  const metadata = (typeof raw.metadata === 'object' && raw.metadata !== null) ? raw.metadata : {};
  const createdAt = toDate(getFirstDefined(raw.created_at, raw.createdAt, raw.uploaded_at));
  const updatedAt = toDate(getFirstDefined(raw.updated_at, raw.updatedAt, raw.indexed_at));

  return { id, title, content, metadata, createdAt, updatedAt };
}

function normalizeUploadItemFromResponse(raw: any, file: File): RagItem {
  let item = normalizeItem(raw);
  if (!item && raw.original_file_id) {
    item = {
      id: raw.original_file_id,
      title: file.name || 'Arquivo enviado',
      content: '',
      metadata: {},
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }
  if (!item) {
    item = {
      id: `upload-${file.name}-${Date.now()}`,
      title: file.name || 'Arquivo enviado',
      content: '',
      metadata: {},
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }
  return item;
}

function normalizeError(error: any): RagAdminError {
  if (typeof error === 'string') return { message: error };
  return {
    message: error?.message || 'Erro desconhecido',
    code: error?.code,
    details: error?.details,
  };
}

export async function listRagDocuments(): Promise<RagListResponse> {
  try {
    const response = await api.get(RAG_ADMIN_ENDPOINTS.LIST);
    const data = extractBody(response);
    const rawItems = Array.isArray(data) ? data : data.items || [];
    const items = rawItems.map(normalizeItem).filter((item): item is RagItem => item !== null && item.id.trim() !== '');
    return { items, total: items.length, page: 1, limit: items.length };
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function uploadRagDocuments(files: File[], extraData?: Record<string, any>): Promise<RagUploadResponse> {
  if (!files || files.length === 0) {
    throw new Error('Nenhum arquivo foi fornecido para upload.');
  }
  const uploaded: RagItem[] = [];
  const failed: { file: string; error: string }[] = [];
  for (const file of files) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (extraData) {
        for (const [key, value] of Object.entries(extraData)) {
          formData.append(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
        }
      }
      const response = await api.post(RAG_ADMIN_ENDPOINTS.UPLOAD, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data = extractBody(response);
      const item = normalizeUploadItemFromResponse(data, file);
      uploaded.push(item);
    } catch (error) {
      failed.push({ file: file.name, error: normalizeError(error).message });
    }
  }
  return { uploaded, failed, totalUploaded: uploaded.length, totalFailed: failed.length };
}

export async function deleteRagDocument(payload: RagDeletePayload | { id?: string; ids?: string[]; delete_chunks?: boolean; [key: string]: unknown }): Promise<RagDeleteResponse> {
  const ids = [
    ...(payload.ids || []),
    ...(payload.id ? [payload.id] : []),
  ].filter(id => id && typeof id === 'string' && id.trim() !== '');

  if (ids.length === 0) {
    throw new Error('Nenhum ID válido foi informado para exclusão.');
  }

  const deleted: string[] = [];
  const failed: { id: string; error: string }[] = [];

  for (const id of ids) {
    try {
      const response = await api.post(`${RAG_ADMIN_ENDPOINTS.DELETE_BASE}/${encodeURIComponent(id)}/delete`, {
        confirmation_phrase: 'CONFIRMADO',
        hard_delete: payload.delete_chunks ?? true,
        delete_chunks: payload.delete_chunks ?? true,
      });
      deleted.push(id);
    } catch (error) {
      failed.push({ id, error: normalizeError(error).message });
    }
  }

  return { deleted, failed };
}

export async function clearRagDatabase(confirm?: boolean): Promise<RagClearResponse> {
  try {
    const response = await api.post(RAG_ADMIN_ENDPOINTS.CLEAR, {
      confirmation_phrase: confirm === true ? 'CONFIRMADO' : 'SIMULACAO',
      dry_run: confirm !== true,
    });
    const data = extractBody(response);
    const count = getFirstDefined(data.total_documents_deleted, data.count, data.affected_count, data.deleted_count, data.total) || 0;
    return { cleared: confirm === true, count };
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function reindexRagDatabase(payload?: RagReindexPayload): Promise<RagReindexResponse> {
  try {
    const response = await api.post(RAG_ADMIN_ENDPOINTS.REINDEX, {
      confirmation_phrase: 'CONFIRMADO',
      original_file_ids: [],
    });
    const data = extractBody(response);
    if (typeof data === 'object' && data !== null) {
      const reindexed = data.status === 'completed';
      const count = data.processed_files ?? 0;
      const status = data.status === 'completed' ? 'completed' : 'in_progress';
      const jobId = data.jobId;
      return { reindexed, count, status, jobId };
    }
    return { reindexed: false, count: 0, status: 'in_progress' };
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getRagOperationStatus(jobId: string): Promise<RagOperationStatusResponse> {
  throw new Error('Status de operação não está disponível no backend atual.');
}

export const ragAdminApi = {
  listRagDocuments,
  uploadRagDocuments,
  deleteRagDocument,
  clearRagDatabase,
  reindexRagDatabase,
  getRagOperationStatus,
};

export default ragAdminApi;
