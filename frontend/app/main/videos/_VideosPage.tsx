'use client';

import { ChangeEvent, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import useVideos from '@/hooks/useVideos';
import useVideoAdmin from '@/hooks/useVideoAdmin';
import type { VideoItem } from '@/types/video';

// ── Categorias ────────────────────────────────────────────────────────────────

const VIDEO_CATEGORIES = [
  { value: 'geral',        label: 'Geral'        },
  { value: 'nutricao',     label: 'Nutrição'      },
  { value: 'genetica',     label: 'Genética'      },
  { value: 'manejo',       label: 'Manejo'        },
  { value: 'sanidade',     label: 'Sanidade'      },
  { value: 'pos-colheita', label: 'Pós-colheita'  },
] as const;

type CategoryValue = typeof VIDEO_CATEGORIES[number]['value'];

// ── Tema visual por categoria ─────────────────────────────────────────────────

const CATEGORY_THEME: Record<string, { gradient: string; badge: string; label: string }> = {
  geral:          { gradient: 'from-gray-700/70 to-gray-900/70',   badge: 'bg-gray-600/70 text-gray-100',    label: 'Geral'        },
  nutricao:       { gradient: 'from-orange-900/60 to-gray-900/70', badge: 'bg-orange-500/60 text-orange-100', label: 'Nutrição'     },
  genetica:       { gradient: 'from-purple-900/60 to-gray-900/70', badge: 'bg-purple-500/60 text-purple-100', label: 'Genética'     },
  manejo:         { gradient: 'from-blue-900/60 to-gray-900/70',   badge: 'bg-blue-500/60 text-blue-100',    label: 'Manejo'       },
  sanidade:       { gradient: 'from-red-900/60 to-gray-900/70',    badge: 'bg-red-500/60 text-red-100',      label: 'Sanidade'     },
  'pos-colheita': { gradient: 'from-green-900/60 to-gray-900/70',  badge: 'bg-green-500/60 text-green-100',  label: 'Pós-colheita' },
};

function getTheme(category: string) {
  return CATEGORY_THEME[category] ?? CATEGORY_THEME['geral'];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatSize(bytes?: number | null): string {
  if (!bytes) return '';
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

// ── Componente ────────────────────────────────────────────────────────────────

export default function VideosPage() {
  const router  = useRouter();
  const user    = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';

  // Data & operations
  const { videos, isLoading, error: listError, refresh } = useVideos();
  const {
    isUploading,
    isDeleting,
    feedback,
    error: adminError,
    uploadVideo,
    deleteVideo,
    resetFeedback,
  } = useVideoAdmin(refresh);

  // Player
  const [selectedVideo, setSelectedVideo] = useState<VideoItem | null>(null);

  // Upload modal
  const [showUpload,     setShowUpload]     = useState(false);
  const [uploadTitle,    setUploadTitle]    = useState('');
  const [uploadDesc,     setUploadDesc]     = useState('');
  const [uploadCategory, setUploadCategory] = useState<CategoryValue>('geral');
  const [uploadFile,     setUploadFile]     = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // ── Handlers ───────────────────────────────────────────────────────────────

  function handleBack() {
    if (window.history.length > 1) router.back();
    else router.push('/main/hub');
  }

  function resetForm() {
    setUploadTitle('');
    setUploadDesc('');
    setUploadCategory('geral');
    setUploadFile(null);
    if (fileRef.current) fileRef.current.value = '';
  }

  function openUpload() {
    resetFeedback();
    setShowUpload(true);
  }

  function closeUpload() {
    setShowUpload(false);
    resetForm();
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setUploadFile(e.target.files?.[0] ?? null);
  }

  async function handleUploadSubmit() {
    if (!uploadFile || !uploadTitle.trim()) return;
    const ok = await uploadVideo(uploadFile, uploadTitle.trim(), uploadDesc, uploadCategory);
    if (ok) closeUpload();
  }

  async function handleDelete(video: VideoItem) {
    if (!window.confirm(`Excluir "${video.title}" permanentemente? Esta ação não pode ser desfeita.`)) return;
    await deleteVideo(video.id);
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-black text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <div className="flex items-center justify-between gap-4 mb-8">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-full border border-white/20 transition-all hover:scale-105 text-sm font-medium shrink-0"
          >
            ← Voltar
          </button>

          <h1 className="text-3xl sm:text-4xl font-bold text-center flex-1">
            Biblioteca de Vídeos
          </h1>

          {isAdmin ? (
            <button
              onClick={openUpload}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-full border border-purple-400/30 transition-all hover:scale-105 text-sm font-semibold shrink-0"
            >
              + Enviar Vídeo
            </button>
          ) : (
            <div className="w-32 shrink-0" />
          )}
        </div>

        {/* Feedback (admin) */}
        {feedback && (
          <div className="mb-6 flex items-center justify-between bg-green-500/20 border border-green-400/40 text-green-300 px-4 py-3 rounded-xl">
            <span>{feedback}</span>
            <button onClick={resetFeedback} className="ml-4 text-xl font-bold hover:text-white">×</button>
          </div>
        )}
        {adminError?.message && (
          <div className="mb-6 flex items-center justify-between bg-red-500/20 border border-red-400/40 text-red-300 px-4 py-3 rounded-xl">
            <span>{adminError.message}</span>
            <button onClick={resetFeedback} className="ml-4 text-xl font-bold hover:text-white">×</button>
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex justify-center items-center py-28">
            <div className="animate-spin rounded-full h-14 w-14 border-b-2 border-purple-400 border-t-transparent" />
          </div>
        )}

        {/* Erro de listagem */}
        {!isLoading && listError && (
          <div className="text-center py-28">
            <p className="text-red-400 text-lg mb-6">{listError.message}</p>
            <button
              onClick={() => void refresh()}
              className="px-6 py-2 bg-white/10 hover:bg-white/20 rounded-xl border border-white/20 transition"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !listError && videos.length === 0 && (
          <div className="text-center py-28">
            <div className="text-6xl mb-6">🎬</div>
            <p className="text-gray-400 text-xl font-medium mb-2">Nenhum vídeo disponível</p>
            {isAdmin && (
              <p className="text-gray-500 text-sm">
                Clique em{' '}
                <span className="text-purple-400 font-semibold">+ Enviar Vídeo</span>
                {' '}para adicionar o primeiro.
              </p>
            )}
          </div>
        )}

        {/* Grid */}
        {!isLoading && !listError && videos.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {videos.map((video) => {
              const theme  = getTheme(video.category);
              const hasUrl = Boolean(video.url);
              return (
                <div
                  key={video.id}
                  className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden hover:border-white/25 hover:-translate-y-1 transition-all duration-300 shadow-xl flex flex-col"
                >
                  {/* Thumbnail */}
                  <div className={`relative h-44 bg-gradient-to-br ${theme.gradient} flex items-center justify-center`}>
                    <button
                      onClick={() => { if (hasUrl) setSelectedVideo(video); }}
                      disabled={!hasUrl}
                      className="w-16 h-16 bg-white/20 hover:bg-white/35 disabled:opacity-30 disabled:cursor-not-allowed rounded-full flex items-center justify-center border border-white/30 transition-all hover:scale-110"
                      title={hasUrl ? 'Assistir' : 'URL indisponível'}
                    >
                      <span className="text-3xl ml-1">▶</span>
                    </button>
                    {video.file_size ? (
                      <span className="absolute bottom-2 right-2 text-xs bg-black/60 text-white px-2 py-0.5 rounded-full">
                        {formatSize(video.file_size)}
                      </span>
                    ) : null}
                  </div>

                  {/* Body */}
                  <div className="p-5 flex flex-col flex-1">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="text-white font-semibold text-base leading-snug flex-1">
                        {video.title}
                      </h3>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium whitespace-nowrap ${theme.badge}`}>
                        {theme.label}
                      </span>
                    </div>

                    {video.description ? (
                      <p className="text-gray-400 text-sm leading-relaxed mb-3 line-clamp-2">
                        {video.description}
                      </p>
                    ) : null}

                    <div className="mt-auto pt-3 flex items-center gap-2">
                      <button
                        onClick={() => { if (hasUrl) setSelectedVideo(video); }}
                        disabled={!hasUrl}
                        className="flex-1 py-2 bg-purple-600/70 hover:bg-purple-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors"
                      >
                        ▶ Assistir
                      </button>
                      {isAdmin && (
                        <button
                          onClick={() => void handleDelete(video)}
                          disabled={isDeleting}
                          className="p-2 bg-red-600/30 hover:bg-red-600/60 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-red-300 text-sm transition-colors"
                          title="Excluir vídeo"
                        >
                          🗑
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal: Player */}
      {selectedVideo !== null && (
        <div
          className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedVideo(null)}
        >
          <div
            className="bg-gray-900 rounded-2xl max-w-4xl w-full border border-white/20 shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 gap-4">
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold text-lg truncate">{selectedVideo.title}</h3>
                <span className={`inline-block text-xs px-2 py-0.5 rounded-full mt-1 ${getTheme(selectedVideo.category).badge}`}>
                  {getTheme(selectedVideo.category).label}
                </span>
              </div>
              <button
                onClick={() => setSelectedVideo(null)}
                className="text-gray-400 hover:text-white text-3xl font-light w-10 h-10 flex items-center justify-center rounded-lg hover:bg-white/10 transition shrink-0"
              >
                ×
              </button>
            </div>

            {/* Video */}
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video
              src={selectedVideo.url}
              controls
              autoPlay
              className="w-full max-h-[65vh] bg-black"
            />

            {/* Description */}
            {selectedVideo.description ? (
              <p className="px-5 py-3 text-gray-400 text-sm border-t border-white/10">
                {selectedVideo.description}
              </p>
            ) : null}
          </div>
        </div>
      )}

      {/* Modal: Upload (admin) */}
      {showUpload && isAdmin && (
        <div
          className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={closeUpload}
        >
          <div
            className="bg-gray-900 rounded-2xl max-w-lg w-full border border-white/20 shadow-2xl p-6 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-white font-bold text-xl">Enviar Vídeo</h3>
              <button
                onClick={closeUpload}
                className="text-gray-400 hover:text-white text-3xl font-light w-10 h-10 flex items-center justify-center rounded-lg hover:bg-white/10 transition"
              >
                ×
              </button>
            </div>

            {/* Erro dentro do modal */}
            {adminError?.message && (
              <div className="mb-4 bg-red-500/20 border border-red-400/40 text-red-300 px-3 py-2 rounded-lg text-sm">
                {adminError.message}
              </div>
            )}

            {/* Título */}
            <div className="mb-4">
              <label className="text-gray-300 text-sm font-medium block mb-1">
                Título <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                maxLength={120}
                placeholder="Nome descritivo do vídeo"
                className="w-full bg-white/10 border border-white/20 focus:border-purple-400 rounded-lg px-3 py-2 text-white placeholder-gray-500 outline-none transition-colors"
              />
            </div>

            {/* Descrição */}
            <div className="mb-4">
              <label className="text-gray-300 text-sm font-medium block mb-1">Descrição</label>
              <textarea
                value={uploadDesc}
                onChange={(e) => setUploadDesc(e.target.value)}
                maxLength={400}
                rows={3}
                placeholder="Descrição breve (opcional)"
                className="w-full bg-white/10 border border-white/20 focus:border-purple-400 rounded-lg px-3 py-2 text-white placeholder-gray-500 outline-none transition-colors resize-none"
              />
            </div>

            {/* Categoria */}
            <div className="mb-4">
              <label className="text-gray-300 text-sm font-medium block mb-1">Categoria</label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value as CategoryValue)}
                className="w-full bg-gray-800 border border-white/20 focus:border-purple-400 rounded-lg px-3 py-2 text-white outline-none transition-colors cursor-pointer"
              >
                {VIDEO_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>

            {/* Arquivo */}
            <div className="mb-6">
              <label className="text-gray-300 text-sm font-medium block mb-1">
                Arquivo <span className="text-red-400">*</span>{' '}
                <span className="text-gray-500 font-normal">(MP4, WebM, MOV)</span>
              </label>
              <input
                ref={fileRef}
                type="file"
                accept=".mp4,.webm,.mov,video/mp4,video/webm,video/quicktime"
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="w-full py-2 bg-white/10 hover:bg-white/20 border border-dashed border-white/20 rounded-lg text-sm transition-colors text-left px-3"
              >
                {uploadFile ? (
                  <span className="text-green-400">
                    ✓ {uploadFile.name}{' '}
                    <span className="text-green-300 font-normal">({formatSize(uploadFile.size)})</span>
                  </span>
                ) : (
                  <span className="text-gray-400">Clique para selecionar o arquivo...</span>
                )}
              </button>
            </div>

            {/* Submit */}
            <button
              onClick={() => void handleUploadSubmit()}
              disabled={isUploading || !uploadFile || !uploadTitle.trim()}
              className="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-semibold text-white transition-colors"
            >
              {isUploading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white border-t-transparent" />
                  Enviando...
                </span>
              ) : (
                'Enviar Vídeo'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
