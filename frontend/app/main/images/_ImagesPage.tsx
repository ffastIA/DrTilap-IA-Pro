'use client';
// CAMINHO: frontend/app/main/images/_ImagesPage.tsx

import { ChangeEvent, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BarChart2Icon } from 'lucide-react';
import useFishAnalysis from '@/hooks/useFishAnalysis';
import type { ProcessResponse } from '@/types/fishImage';

// ── helpers ───────────────────────────────────────────────────────────────────

function fmt(v: number | null | undefined, decimals = 2): string {
  if (v == null) return '—';
  return v.toFixed(decimals);
}

// ── Janela de upload individual ───────────────────────────────────────────────
// FIX: fatorValue e onFatorChange são controlados pelo pai para que o valor
// esteja sempre disponível no momento de clicar em "Processar",
// independentemente de quando o usuário digitou o fator.

interface UploadWindowProps {
  label: string;
  tag: 'lateral' | 'superior';
  imageId: string | null;
  preview: string | null;
  isUploading: boolean;
  fatorValue: string;
  onFatorChange: (v: string) => void;
  onUpload: (file: File, tag: 'lateral' | 'superior') => void;
}

function UploadWindow({
  label, tag, imageId, preview, isUploading,
  fatorValue, onFatorChange, onUpload,
}: UploadWindowProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    onUpload(file, tag);
    e.target.value = '';
  };

  const borderColor = imageId
    ? (tag === 'lateral' ? 'border-blue-500' : 'border-teal-500')
    : 'border-gray-600';

  return (
    <div className={`border-2 ${borderColor} rounded-lg p-3 bg-gray-800 flex flex-col gap-2`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-white">{label}</span>
        {imageId && (
          <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded-full">✓ Pronta</span>
        )}
      </div>

      {/* Preview */}
      <div className="w-full aspect-video bg-gray-900 rounded flex items-center justify-center overflow-hidden">
        {preview ? (
          <img src={preview} alt={label} className="max-h-full max-w-full object-contain" />
        ) : (
          <span className="text-gray-500 text-xs text-center px-2">
            Selecione uma imagem<br />do disco local
          </span>
        )}
      </div>

      {/* Fator de conversão — controlado pelo pai */}
      <div>
        <label className="text-xs text-gray-400 block mb-1">
          Fator px/cm <span className="text-gray-500">(opcional — usa ArUco se vazio)</span>
        </label>
        <input
          type="number"
          step="0.01"
          min="0"
          placeholder="ex: 56.00"
          value={fatorValue}
          onChange={(e) => onFatorChange(e.target.value)}
          className="w-full bg-gray-700 text-white text-sm px-2 py-1 rounded border border-gray-600 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Botão upload */}
      <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2 rounded transition-colors"
      >
        {isUploading ? 'Enviando…' : 'Selecionar Imagem'}
      </button>
    </div>
  );
}

// ── Painel de resultados ──────────────────────────────────────────────────────

function MetricCard({
  label, valueCm, valuePx, unit = 'cm', color,
}: {
  label: string;
  valueCm: string;
  valuePx?: string;
  unit?: string;
  color: string;
}) {
  const colors: Record<string, string> = {
    blue:   'bg-blue-900 border-blue-600',
    teal:   'bg-teal-900 border-teal-600',
    purple: 'bg-purple-900 border-purple-600',
    orange: 'bg-orange-900 border-orange-600',
  };
  return (
    <div className={`${colors[color] || colors.blue} border rounded-lg p-4`}>
      <p className="text-xs text-gray-300 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">
        {valueCm} <span className="text-sm font-normal text-gray-300">{unit}</span>
      </p>
      {valuePx != null && (
        <p className="text-xs text-gray-400 mt-1">{valuePx} px</p>
      )}
    </div>
  );
}

function ResultPanel({ result }: { result: ProcessResponse }) {
  const lat = result.lateral_metrics as Record<string, unknown> | null ?? {};
  const sup = result.superior_metrics as Record<string, unknown> | null ?? {};

  // Comprimento → bbox_width da lateral
  const comprPx  = lat['bbox_width_px']  != null ? fmt(lat['bbox_width_px']  as number, 0) : undefined;
  // Altura → bbox_height da lateral
  const altPx    = lat['bbox_height_px'] != null ? fmt(lat['bbox_height_px'] as number, 0) : undefined;
  // Largura → bbox_height da superior
  const largPx   = sup['bbox_height_px'] != null ? fmt(sup['bbox_height_px'] as number, 0) : undefined;
  // Área máscara
  const areLatPx = lat['mask_area_px']   != null ? fmt(lat['mask_area_px']   as number, 0) : undefined;
  const areSupPx = sup['mask_area_px']   != null ? fmt(sup['mask_area_px']   as number, 0) : undefined;
  const areLatCm = lat['mask_area_cm2']  != null ? fmt(lat['mask_area_cm2']  as number, 2) : '—';
  const areSupCm = sup['mask_area_cm2']  != null ? fmt(sup['mask_area_cm2']  as number, 2) : '—';
  // Fator
  const fatorLat = lat['fator_conversao'] != null ? fmt(lat['fator_conversao'] as number, 2) : '—';
  const fatorSup = sup['fator_conversao'] != null ? fmt(sup['fator_conversao'] as number, 2) : '—';

  return (
    <div className="bg-gray-800 rounded-lg p-6 space-y-6">
      <h2 className="text-xl font-bold text-white">Resultados da Análise</h2>

      {result.warnings.length > 0 && (
        <div className="bg-yellow-900 border border-yellow-600 rounded p-3 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-yellow-300 text-sm">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Métricas principais — cm + px na mesma card */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Dimensões</h3>
        <div className="grid grid-cols-2 gap-4">
          <MetricCard label="Comprimento" valueCm={fmt(result.comprimento_cm)} valuePx={comprPx} color="blue" />
          <MetricCard label="Altura"      valueCm={fmt(result.altura_cm)}      valuePx={altPx}   color="teal" />
          <MetricCard label="Largura"     valueCm={fmt(result.largura_cm)}     valuePx={largPx}  color="purple" />
          {result.kvol != null ? (
            <MetricCard label="Kvol" valueCm={fmt(result.kvol, 6)} unit="" color="orange" />
          ) : (
            <div className="bg-gray-700 border border-gray-600 rounded-lg p-4">
              <p className="text-xs text-gray-400 uppercase tracking-wide">Kvol</p>
              <p className="text-gray-500 text-sm mt-2">Peso não informado</p>
            </div>
          )}
        </div>
      </div>

      {/* Área da máscara */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Área da Máscara</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700 border border-gray-600 rounded-lg p-4">
            <p className="text-xs text-gray-300 uppercase tracking-wide">Lateral</p>
            <p className="text-xl font-bold text-white mt-1">{areLatCm} <span className="text-sm font-normal text-gray-300">cm²</span></p>
            {areLatPx && <p className="text-xs text-gray-400 mt-1">{areLatPx} px²</p>}
          </div>
          <div className="bg-gray-700 border border-gray-600 rounded-lg p-4">
            <p className="text-xs text-gray-300 uppercase tracking-wide">Superior</p>
            <p className="text-xl font-bold text-white mt-1">{areSupCm} <span className="text-sm font-normal text-gray-300">cm²</span></p>
            {areSupPx && <p className="text-xs text-gray-400 mt-1">{areSupPx} px²</p>}
          </div>
        </div>
      </div>

      {/* Fatores de escala usados */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">Fator de Escala Usado</h3>
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-300">
          <p>Lateral: <span className="text-white font-mono">{fatorLat} px/cm</span></p>
          <p>Superior: <span className="text-white font-mono">{fatorSup} px/cm</span></p>
        </div>
      </div>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function ImagesPage() {
  const router = useRouter();
  const {
    lateralId, superiorId,
    uploadImage, processImages, resetFeedback,
    isUploading, isProcessing,
    lastResult, feedback, error,
  } = useFishAnalysis();

  // Previews locais
  const [lateralPreview,  setLateralPreview]  = useState<string | null>(null);
  const [superiorPreview, setSuperiorPreview] = useState<string | null>(null);

  // FIX: fatores controlados pelo pai — sempre refletem o valor atual do campo
  const [fatorLateralStr,  setFatorLateralStr]  = useState<string>('');
  const [fatorSuperiorStr, setFatorSuperiorStr] = useState<string>('');

  const [pesoG, setPesoG] = useState<string>('');

  const canProcess = !!lateralId && !!superiorId && !isProcessing;

  const handleUpload = async (file: File, tag: 'lateral' | 'superior') => {
    const url = URL.createObjectURL(file);
    if (tag === 'lateral') setLateralPreview(url);
    else setSuperiorPreview(url);
    // FIX: fator NÃO é capturado aqui — será lido em handleProcess
    await uploadImage(file, tag, null);
  };

  const handleProcess = async () => {
    if (!lateralId || !superiorId) return;
    // lê os fatores do estado do pai no momento do clique — sempre atualizado
    const fatorLateral  = fatorLateralStr  ? parseFloat(fatorLateralStr)  : null;
    const fatorSuperior = fatorSuperiorStr ? parseFloat(fatorSuperiorStr) : null;
    const result = await processImages({
      lateralId,
      superiorId,
      fatorLateral,
      fatorSuperior,
      pesoG: pesoG ? parseFloat(pesoG) : null,
    });
    // Substitui previews pelas imagens processadas (máscara + bbox)
    if (result?.lateral_viz_b64) {
      setLateralPreview(`data:image/jpeg;base64,${result.lateral_viz_b64}`);
    }
    if (result?.superior_viz_b64) {
      setSuperiorPreview(`data:image/jpeg;base64,${result.superior_viz_b64}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => router.back()} className="text-blue-400 hover:text-blue-300 font-medium">
            ← Voltar
          </button>
          <h1 className="text-2xl font-bold">Análise de Imagens por IA</h1>
        </div>
        <button
          onClick={() => router.push('/main/images/dashboard')}
          className="flex items-center gap-2 bg-purple-700 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <BarChart2Icon size={16} />
          Dashboards
        </button>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className="mx-6 mt-4 bg-green-800 border border-green-600 text-green-200 px-4 py-3 rounded flex justify-between items-center">
          <span>{feedback}</span>
          <button onClick={resetFeedback} className="text-green-400 hover:text-white text-xl font-bold ml-4">×</button>
        </div>
      )}
      {error && (
        <div className="mx-6 mt-4 bg-red-900 border border-red-600 text-red-200 px-4 py-3 rounded flex justify-between items-center">
          <span>{error.message}</span>
          <button onClick={resetFeedback} className="text-red-400 hover:text-white text-xl font-bold ml-4">×</button>
        </div>
      )}

      {/* Layout */}
      <div className="flex" style={{ height: 'calc(100vh - 65px)' }}>

        {/* ── Coluna esquerda: uploads (25%) ── */}
        <aside className="w-1/4 min-w-[220px] max-w-xs border-r border-gray-700 p-4 flex flex-col gap-4 overflow-y-auto">

          <UploadWindow
            label="Imagem Lateral"
            tag="lateral"
            imageId={lateralId}
            preview={lateralPreview}
            isUploading={isUploading}
            fatorValue={fatorLateralStr}
            onFatorChange={setFatorLateralStr}
            onUpload={handleUpload}
          />

          <UploadWindow
            label="Imagem Superior"
            tag="superior"
            imageId={superiorId}
            preview={superiorPreview}
            isUploading={isUploading}
            fatorValue={fatorSuperiorStr}
            onFatorChange={setFatorSuperiorStr}
            onUpload={handleUpload}
          />

          {/* Peso */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Peso do peixe (g)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              placeholder="ex: 250.0"
              value={pesoG}
              onChange={(e) => setPesoG(e.target.value)}
              className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:outline-none focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">Necessário para calcular Kvol</p>
          </div>

          {/* Botão Processar */}
          <button
            onClick={handleProcess}
            disabled={!canProcess}
            className="w-full bg-green-600 hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg transition-colors text-sm"
          >
            {isProcessing ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Processando…
              </span>
            ) : '▶ Processar'}
          </button>

          {!lateralId && (
            <p className="text-xs text-gray-500 text-center">
              Faça upload das 2 imagens para habilitar o processamento
            </p>
          )}
        </aside>

        {/* ── Área direita: resultados (75%) ── */}
        <main className="flex-1 overflow-y-auto p-6">
          {lastResult ? (
            <ResultPanel result={lastResult} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
              <div className="text-6xl mb-4">🐟</div>
              <p className="text-lg font-medium">Nenhuma análise ainda</p>
              <p className="text-sm mt-2 max-w-sm">
                Faça upload das imagens lateral e superior, informe o fator px/cm
                (ou use o marcador ArUco) e clique em <strong className="text-white">▶ Processar</strong>.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
