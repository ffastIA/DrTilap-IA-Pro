'use client';
// CAMINHO: frontend/app/main/images/dashboard/_DashboardPage.tsx

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { listFishAnalyses, listFishImages } from '@/lib/fishImageApi';
import type { FishAnalysisItem, FishImageItem } from '@/types/fishImage';

// ── Utilitários ───────────────────────────────────────────────────────────────

function fmt(v: number | null | undefined, d = 4): string {
  if (v == null) return '—';
  return v.toFixed(d);
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ── Export para Excel (sem dependência externa) ────────────────────────────────
function exportCsv(filename: string, headers: string[], rows: (string | number | null | undefined)[][]) {
  const bom = '﻿';   // BOM para UTF-8 — Excel reconhece acentos
  const sep = ';';
  const lines = [
    headers.join(sep),
    ...rows.map((r) => r.map((c) => (c == null ? '' : String(c).replace(/;/g, ','))).join(sep)),
  ];
  const blob = new Blob([bom + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Mini gráfico de linha (SVG puro — sem dependência externa) ─────────────────

interface LineChartProps {
  data: { x: string; y: number }[];
  label: string;
  color: string;
}

function LineChart({ data, label, color }: LineChartProps) {
  if (data.length === 0) return <p className="text-gray-500 text-sm text-center py-8">Sem dados</p>;

  const W = 320, H = 160, PAD = 32;
  const ys = data.map((d) => d.y);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const rangeY = maxY - minY || 1;

  const toX = (i: number) => PAD + (i / Math.max(data.length - 1, 1)) * (W - PAD * 2);
  const toY = (v: number) => PAD + ((maxY - v) / rangeY) * (H - PAD * 2);

  const points = data.map((d, i) => `${toX(i)},${toY(d.y)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 180 }}>
      {/* Eixos */}
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#4b5563" strokeWidth="1" />
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#4b5563" strokeWidth="1" />
      {/* Linha */}
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* Pontos */}
      {data.map((d, i) => (
        <circle key={i} cx={toX(i)} cy={toY(d.y)} r="3" fill={color}>
          <title>{`${d.x}: ${d.y.toFixed(4)}`}</title>
        </circle>
      ))}
      {/* Labels eixo Y */}
      <text x={PAD - 4} y={PAD + 4} textAnchor="end" fontSize="9" fill="#9ca3af">{maxY.toFixed(2)}</text>
      <text x={PAD - 4} y={H - PAD + 4} textAnchor="end" fontSize="9" fill="#9ca3af">{minY.toFixed(2)}</text>
      {/* Título */}
      <text x={W / 2} y={12} textAnchor="middle" fontSize="10" fill="#d1d5db">{label}</text>
    </svg>
  );
}

// ── Componente de dashboard individual ────────────────────────────────────────

interface DashboardPanelProps {
  title: string;
  color: string;
  headers: string[];
  rows: (string | number | null | undefined)[][];
  chartData: { x: string; y: number }[];
  chartLabel: string;
  chartColor: string;
  isLoading: boolean;
  exportFilename: string;
}

function DashboardPanel({
  title, color, headers, rows, chartData, chartLabel, chartColor, isLoading, exportFilename,
}: DashboardPanelProps) {
  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className={`px-4 py-3 flex items-center justify-between ${color}`}>
        <h2 className="text-white font-semibold">{title}</h2>
        <button
          onClick={() => exportCsv(exportFilename, headers, rows)}
          className="text-xs bg-white bg-opacity-20 hover:bg-opacity-30 text-white px-3 py-1 rounded transition-colors"
        >
          ⬇ Exportar CSV
        </button>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-gray-400">Carregando…</div>
      ) : rows.length === 0 ? (
        <div className="p-8 text-center text-gray-500">Nenhum dado disponível</div>
      ) : (
        <div className="flex flex-col md:flex-row">
          {/* Tabela */}
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-700">
                <tr>
                  {headers.map((h) => (
                    <th key={h} className="text-left px-3 py-2 text-gray-300 font-medium text-xs whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-750">
                    {row.map((cell, j) => (
                      <td key={j} className="px-3 py-2 text-gray-300 text-xs whitespace-nowrap">
                        {cell == null ? '—' : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Gráfico */}
          <div className="w-full md:w-72 p-4 border-t md:border-t-0 md:border-l border-gray-700">
            <LineChart data={chartData} label={chartLabel} color={chartColor} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Página de dashboards ──────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();

  const [analyses, setAnalyses] = useState<FishAnalysisItem[]>([]);
  const [lateralImgs, setLateralImgs] = useState<FishImageItem[]>([]);
  const [superiorImgs, setSuperiorImgs] = useState<FishImageItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [analysesData, lateralData, superiorData] = await Promise.all([
        listFishAnalyses(),
        listFishImages({ tag: 'lateral' }),
        listFishImages({ tag: 'superior' }),
      ]);
      setAnalyses(analysesData.items);
      setLateralImgs(lateralData.items.filter((i) => i.processing_status === 'done'));
      setSuperiorImgs(superiorData.items.filter((i) => i.processing_status === 'done'));
    } catch (e) {
      console.error('Erro ao carregar dashboards', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // ── KVol ──────────────────────────────────────────────────────────────────
  const kvolRows = analyses
    .filter((a) => a.kvol != null)
    .map((a) => [
      formatDate(a.created_at),
      fmt(a.kvol, 6),
      fmt(a.comprimento_cm),
      fmt(a.altura_cm),
      fmt(a.largura_cm),
      fmt(a.peso_g, 1),
    ]);

  const kvolChart = analyses
    .filter((a) => a.kvol != null)
    .reverse()
    .map((a) => ({ x: formatDate(a.created_at), y: a.kvol as number }));

  // ── Comprimento (lateral) ─────────────────────────────────────────────────
  const comprRows = lateralImgs
    .filter((i) => i.bbox_width_cm != null)
    .map((i) => [formatDate(i.uploaded_at), fmt(i.bbox_width_cm), fmt(i.bbox_width_px, 0), fmt(i.fator_conversao)]);

  const comprChart = [...comprRows].reverse().map((r, idx) => ({
    x: String(r[0]),
    y: parseFloat(String(comprRows[comprRows.length - 1 - idx]?.[1]) || '0') || 0,
  }));

  // ── Altura (lateral) ──────────────────────────────────────────────────────
  const altRows = lateralImgs
    .filter((i) => i.bbox_height_cm != null)
    .map((i) => [formatDate(i.uploaded_at), fmt(i.bbox_height_cm), fmt(i.bbox_height_px, 0), fmt(i.fator_conversao)]);

  const altChart = lateralImgs
    .filter((i) => i.bbox_height_cm != null)
    .reverse()
    .map((i) => ({ x: formatDate(i.uploaded_at), y: i.bbox_height_cm as number }));

  // ── Largura (superior) ────────────────────────────────────────────────────
  const largRows = superiorImgs
    .filter((i) => i.bbox_height_cm != null)
    .map((i) => [formatDate(i.uploaded_at), fmt(i.bbox_height_cm), fmt(i.bbox_height_px, 0), fmt(i.fator_conversao)]);

  const largChart = superiorImgs
    .filter((i) => i.bbox_height_cm != null)
    .reverse()
    .map((i) => ({ x: formatDate(i.uploaded_at), y: i.bbox_height_cm as number }));

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="text-blue-400 hover:text-blue-300 font-medium"
        >
          ← Voltar
        </button>
        <h1 className="text-2xl font-bold">Dashboards Biométricos</h1>
        <button
          onClick={loadData}
          className="ml-auto text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-3 py-1.5 rounded transition-colors"
        >
          ↺ Atualizar
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* KVol */}
        <DashboardPanel
          title="Kvol — Índice Volumétrico"
          color="bg-orange-800"
          headers={['Data', 'Kvol', 'Compr. (cm)', 'Altura (cm)', 'Largura (cm)', 'Peso (g)']}
          rows={kvolRows}
          chartData={kvolChart}
          chartLabel="Evolução do Kvol"
          chartColor="#f97316"
          isLoading={isLoading}
          exportFilename="kvol.csv"
        />

        {/* Comprimento */}
        <DashboardPanel
          title="Comprimento — Imagens Laterais"
          color="bg-blue-800"
          headers={['Data', 'Comprimento (cm)', 'Comprimento (px)', 'Fator px/cm']}
          rows={comprRows}
          chartData={comprChart}
          chartLabel="Evolução do Comprimento"
          chartColor="#3b82f6"
          isLoading={isLoading}
          exportFilename="comprimento.csv"
        />

        {/* Altura */}
        <DashboardPanel
          title="Altura — Imagens Laterais"
          color="bg-teal-800"
          headers={['Data', 'Altura (cm)', 'Altura (px)', 'Fator px/cm']}
          rows={altRows}
          chartData={altChart}
          chartLabel="Evolução da Altura"
          chartColor="#14b8a6"
          isLoading={isLoading}
          exportFilename="altura.csv"
        />

        {/* Largura */}
        <DashboardPanel
          title="Largura — Imagens Superiores"
          color="bg-purple-800"
          headers={['Data', 'Largura (cm)', 'Largura (px)', 'Fator px/cm']}
          rows={largRows}
          chartData={largChart}
          chartLabel="Evolução da Largura"
          chartColor="#a855f7"
          isLoading={isLoading}
          exportFilename="largura.csv"
        />
      </div>
    </div>
  );
}
