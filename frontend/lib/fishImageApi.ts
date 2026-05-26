// CAMINHO: frontend/lib/fishImageApi.ts

import api from '@/lib/api';
import type {
  FishImageListResponse,
  FishImageUploadResponse,
  FishImageDeleteResponse,
  FishAnalysisListResponse,
  ProcessRequest,
  ProcessResponse,
} from '@/types/fishImage';

// ── Imagens ───────────────────────────────────────────────────────────────────

export async function uploadFishImage(
  file: File,
  tag: 'lateral' | 'superior',
  fatorConversao?: number | null,
): Promise<FishImageUploadResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('tag', tag);
  if (fatorConversao != null) {
    form.append('fator_conversao', String(fatorConversao));
  }
  const response = await api.post('/fish/images/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function listFishImages(params?: {
  tag?: string;
  date_from?: string;
  date_to?: string;
}): Promise<FishImageListResponse> {
  const response = await api.get('/fish/images', { params });
  return response.data;
}

export async function deleteFishImage(imageId: string): Promise<FishImageDeleteResponse> {
  const response = await api.delete(`/fish/images/${imageId}`);
  return response.data;
}

// ── Análises ──────────────────────────────────────────────────────────────────

export async function processFishAnalysis(
  data: ProcessRequest,
): Promise<ProcessResponse> {
  const response = await api.post('/fish/analyses/process', data);
  return response.data;
}

export async function listFishAnalyses(params?: {
  date_from?: string;
  date_to?: string;
  kvol_min?: number;
  kvol_max?: number;
}): Promise<FishAnalysisListResponse> {
  const response = await api.get('/fish/analyses', { params });
  return response.data;
}

export async function deleteFishAnalysis(analysisId: string): Promise<{ id: string; status: string; message: string }> {
  const response = await api.delete(`/fish/analyses/${analysisId}`);
  return response.data;
}
