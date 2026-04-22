// CAMINHO: frontend/app/main/admin/page.tsx

'use client';

import { ChangeEvent, useRef } from 'react';
import { useRouter } from 'next/navigation';
import useRagAdmin from '@/hooks/useRagAdmin';

function formatDate(value: Date | null | undefined, hasValid?: boolean): string {
  if (hasValid === false || !value || isNaN(value.getTime())) {
    return 'Data indisponível';
  }
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(value);
}

function getChunks(metadata?: Record<string, any>): number {
  return Number(metadata?.total_chunks ?? metadata?.active_chunks ?? 0);
}

function safeSource(item: any): string {
  const source = item.metadata?.source || item.title;
  if (source.includes('AppData') || source.includes('Temp') || source.includes('tmp')) {
    return item.title;
  }
  return source;
}

export default function AdminPage() {
  const router = useRouter();
  const {
    items,
    isLoadingList,
    isUploading,
    isDeleting,
    isClearing,
    isReindexing,
    selectedItem,
    isDeleteModalOpen,
    operationMessage,
    operationError,
    refreshList,
    uploadFiles,
    openDeleteModal,
    closeDeleteModal,
    deleteSelectedItem,
    clearDatabase,
    reindexDatabase,
    resetFeedback,
  } = useRagAdmin();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/main/hub');
    }
  };

  const handleUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      uploadFiles(files);
      e.target.value = '';
    }
  };

  const handleClear = () => {
    if (window.confirm('Tem certeza que deseja limpar DEFINITIVAMENTE todos os documentos da base RAG? Esta ação é irreversível.')) {
      clearDatabase(true);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={handleBack}
          className="mb-6 text-blue-600 hover:text-blue-800 font-medium text-lg flex items-center"
        >
          ← Voltar
        </button>

        <h1 className="text-3xl font-bold text-gray-900 mb-8">Administração RAG</h1>

        {/* Feedback */}
        {operationMessage && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6 relative">
            {operationMessage}
            <button
              onClick={resetFeedback}
              className="absolute top-2 right-2 text-green-700 hover:text-green-900 text-xl font-bold"
            >
              ×
            </button>
          </div>
        )}
        {operationError?.message && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6 relative">
            {operationError.message}
            <button
              onClick={resetFeedback}
              className="absolute top-2 right-2 text-red-700 hover:text-red-900 text-xl font-bold"
            >
              ×
            </button>
          </div>
        )}

        {/* Upload Area */}
        <div className="bg-white p-6 rounded-lg shadow-md mb-8">
          <h2 className="text-xl font-semibold mb-4">Upload de PDFs</h2>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isUploading ? 'Enviando...' : 'Selecionar PDFs'}
          </button>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mb-8">
          <button
            onClick={refreshList}
            disabled={isLoadingList}
            className="bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isLoadingList ? 'Atualizando...' : 'Atualizar Lista'}
          </button>
          <button
            onClick={reindexDatabase}
            disabled={isReindexing}
            className="bg-yellow-600 text-white px-6 py-3 rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isReindexing ? 'Reindexando...' : 'Reindexar Base'}
          </button>
          <button
            onClick={handleClear}
            disabled={isClearing}
            className="bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isClearing ? 'Limpando...' : 'Limpeza Definitiva'}
          </button>
        </div>

        {/* List */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {isLoadingList ? (
            <div className="p-12 text-center text-gray-500 text-lg">Carregando lista...</div>
          ) : items.length === 0 ? (
            <div className="p-12 text-center text-gray-500 text-lg">Nenhum documento indexado no momento.</div>
          ) : (
            <div className="divide-y divide-gray-200">
              {items.map((item) => (
                <div key={item.id} className="p-6 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 flex-1 pr-4 truncate">
                      {item.title}
                    </h3>
                    <button
                      onClick={() => openDeleteModal(item)}
                      disabled={isDeleting}
                      className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium whitespace-nowrap"
                    >
                      Excluir
                    </button>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-700">
                    <p><strong>ID:</strong> {item.id}</p>
                    <p><strong>Inserido em:</strong> {formatDate(item.createdAt, item.metadata?.hasValidCreatedAt)}</p>
                    <p><strong>Atualizado em:</strong> {formatDate(item.updatedAt, item.metadata?.hasValidUpdatedAt)}</p>
                    <p><strong>Source:</strong> {safeSource(item)}</p>
                    <p className="md:col-span-2"><strong>Chunks:</strong> {getChunks(item.metadata)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Delete Modal */}
        {isDeleteModalOpen && selectedItem && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white p-8 rounded-lg shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Confirmar Exclusão</h3>
              <p className="text-gray-700 mb-6">
                Deseja excluir o documento <strong>{selectedItem.title}</strong> permanentemente?
              </p>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={closeDeleteModal}
                  className="px-6 py-2 text-gray-700 border border-gray-300 hover:bg-gray-50 rounded-lg font-medium transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={deleteSelectedItem}
                  disabled={isDeleting}
                  className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {isDeleting ? 'Excluindo...' : 'Excluir'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}