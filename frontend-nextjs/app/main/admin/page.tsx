'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { uploadApi } from '@/lib/api';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

export default function AdminPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Redirecionar se não for admin
  if (user?.role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="text-center">
          <div className="text-6xl mb-4">🚫</div>
          <h1 className="text-2xl font-bold text-white mb-2">Acesso Negado</h1>
          <p className="text-slate-400 mb-6">
            Você não tem permissão para acessar esta página.
          </p>
          <Link
            href="/main/hub"
            className="text-cyan-400 hover:text-cyan-300 font-medium"
          >
            ← Voltar ao Hub
          </Link>
        </div>
      </div>
    );
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadApi.uploadPdf(file),
    onSuccess: (response) => {
      setUploadSuccess(true);
      setFile(null);

      // Limpar mensagem após 5 segundos
      setTimeout(() => {
        setUploadSuccess(false);
      }, 5000);
    },
    onError: (error: any) => {
      console.error('Upload error:', error);
    },
  });

  const handleUpload = () => {
    if (!file) return;
    uploadMutation.mutate(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles && droppedFiles[0]) {
      const droppedFile = droppedFiles[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
      } else {
        alert('Por favor, selecione um arquivo PDF');
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link href="/main/hub" className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
            ← Voltar
          </Link>
          <h1 className="text-4xl font-bold text-white mt-4 mb-2">
            ⚙️ Administração RAG
          </h1>
          <p className="text-slate-400">
            Faça upload de documentos PDF para expandir a base de conhecimento da IA
          </p>
        </div>

        {/* Upload Form */}
        <div className="glass p-8 space-y-6 rounded-2xl">
          {/* Success Message */}
          {uploadSuccess && (
            <div className="p-4 bg-green-500/20 border border-green-500/50 rounded-lg animate-pulse">
              <p className="text-green-200 text-sm font-medium">
                ✅ Upload realizado com sucesso!
              </p>
              {uploadMutation.data && (
                <p className="text-green-200 text-xs mt-2">
                  {uploadMutation.data.chunks_criados} chunks criados e indexados.
                </p>
              )}
            </div>
          )}

          {/* Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
              dragActive
                ? 'border-cyan-500 bg-cyan-500/10'
                : 'border-slate-600 hover:border-slate-500'
            }`}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  setFile(e.target.files[0]);
                }
              }}
              className="hidden"
              id="file-input"
            />
            <label htmlFor="file-input" className="cursor-pointer block">
              <div className="text-4xl mb-3">📄</div>
              <p className="font-semibold text-white mb-1">
                Clique para selecionar ou arraste um PDF
              </p>
              <p className="text-sm text-slate-400">
                Máximo de arquivo: 50MB
              </p>
            </label>
          </div>

          {/* File Preview */}
          {file && (
            <div className="bg-slate-700/30 border border-slate-600/50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">📄</span>
                  <div>
                    <p className="font-medium text-white truncate">{file.name}</p>
                    <p className="text-sm text-slate-400">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setFile(null)}
                  className="text-slate-400 hover:text-white transition duration-200"
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!file || uploadMutation.isPending}
            className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 disabled:from-slate-600 disabled:to-slate-600 text-white font-semibold rounded-lg transition-all duration-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {uploadMutation.isPending ? (
              <>
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Enviando...</span>
              </>
            ) : (
              <>
                <span>📤 Fazer Upload</span>
              </>
            )}
          </button>

          {/* Error Message */}
          {uploadMutation.isError && (
            <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg">
              <p className="text-red-200 text-sm font-medium">
                ❌ Erro ao fazer upload
              </p>
              <p className="text-red-200 text-xs mt-2">
                {uploadMutation.error instanceof Error
                  ? uploadMutation.error.message
                  : 'Erro desconhecido'}
              </p>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className="mt-8 bg-slate-700/30 border border-slate-600/50 rounded-lg p-6">
          <h3 className="font-semibold text-white mb-3">ℹ️ Como Funciona</h3>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>
              <span className="font-medium">1.</span> Faça upload de um documento PDF
            </li>
            <li>
              <span className="font-medium">2.</span> O sistema analisa e cria "chunks" (pedaços)
            </li>
            <li>
              <span className="font-medium">3.</span> Cada chunk é vetorizado e indexado
            </li>
            <li>
              <span className="font-medium">4.</span> A IA usa esses dados para responder perguntas
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}