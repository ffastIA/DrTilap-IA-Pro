// CAMINHO: frontend/app/main/admin/page.tsx

'use client';

import { ChangeEvent, useMemo, useRef } from 'react';
import useRagAdmin from '@/hooks/useRagAdmin';

type Metadata = Record<string, any>;

type Document = {
  id: string;
  title: string;
  createdAt: Date | null;
  updatedAt: Date | null;
  metadata?: Metadata;
};

function formatDate(value: Date | null | undefined, hasValid?: boolean): string {
  if (hasValid === false || !value || isNaN(value.getTime())) {
    return 'Data indisponível';
  }
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(value);
}

function getChunks(metadata?: Metadata): number {
  return Number(metadata?.total_chunks ?? metadata?.active_chunks ?? 0);
}

function safeSource(item: Document): string {
  const source = item.metadata?.source || item.title;
  if (source.includes('AppData') || source.includes('Temp') || source.includes('tmp')) {
    return item.title;
  }
  return source;
}

export default function Page() {
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (validFiles.length > 0) {
      uploadFiles(validFiles);
    }
    e.target.value = '';
  };

  const handleClearDatabase = () => {
    if (window.confirm('Limpeza definitiva da base de dados? Todos os documentos serão removidos permanentemente.')) {
      clearDatabase(true);
    }
  };

  return (
    <div className="container mx-auto p-8 max-w-7xl">
      {/* Feedback Messages */}
      {operationMessage && (
        <div className="bg-green-500 text-white p-4 rounded mb-4 flex justify-between items-center">
          <span>{operationMessage}</span>
          <button
            onClick={resetFeedback}
            className="ml-4 px-2 py-1 bg-green-600 rounded hover:bg-green-700"
          >
            ✕
          </button>
        </div>
      )}
      {operationError?.message && (
        <div className="bg-red-500 text-white p-4 rounded mb-4 flex justify-between items-center">
          <span>{operationError.message}</span>
          <button
            onClick={resetFeedback}
            className="ml-4 px-2 py-1 bg-red-600 rounded hover:bg-red-700"
          >
            ✕
          </button>
        </div>
      )}

      {/* Upload Area */}
      <div className="mb-8">
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isUploading ? 'Enviando...' : 'Carregar PDFs'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Main Actions */}
      <div className="flex flex-wrap gap-4 mb-8">
        <button
          onClick={refreshList}
          disabled={isLoadingList}
          className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Atualizar lista
        </button>
        <button
          onClick={() => reindexDatabase()}
          disabled={isReindexing}
          className="bg-yellow-500 hover:bg-yellow-600 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reindexar base
        </button>
        <button
          onClick={handleClearDatabase}
          disabled={isClearing}
          className="bg-red-500 hover:bg-red-600 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Limpeza definitiva
        </button>
      </div>

      {/* Documents List */}
      <div>
        {isLoadingList ? (
          <div className="text-center py-12 text-lg">Carregando documentos...</div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-lg text-gray-500">Nenhum documento indexado no momento.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => (
              <div key={item.id} className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow">
                <h3 className="text-xl font-semibold mb-2 truncate">{item.title}</h3>
                <p className="text-sm text-gray-600 mb-1"><strong>ID:</strong> {item.id}</p>
                <p className="text-sm text-gray-600 mb-1"><strong>Inserido em:</strong> {formatDate(item.createdAt, item.metadata?.hasValidCreatedAt)}</p>
                <p className="text-sm text-gray-600 mb-1"><strong>Atualizado em:</strong> {formatDate(item.updatedAt, item.metadata?.hasValidUpdatedAt)}</p>
                <p className="text-sm text-gray-600 mb-3"><strong>Source:</strong> {safeSource(item)}</p>
                <p className="text-sm text-gray-600 mb-4"><strong>Chunks:</strong> {getChunks(item.metadata)}</p>
                <button
                  onClick={() => openDeleteModal(item)}
                  className="w-full bg-red-500 hover:bg-red-600 text-white py-2 px-4 rounded-md font-medium transition-colors"
                >
                  Excluir
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Modal */}
      {isDeleteModalOpen && selectedItem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Confirmar exclusão</h2>
              <p className="text-lg text-gray-700 mb-6">
                Tem certeza que deseja excluir o documento <strong>&quot;{selectedItem.title}&quot;</strong>?
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={closeDeleteModal}
                  disabled={isDeleting}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 font-medium disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={deleteSelectedItem}
                  disabled={isDeleting}
                  className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-md font-medium disabled:opacity-50 transition-colors"
                >
                  {isDeleting ? 'Excluindo...' : 'Confirmar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
