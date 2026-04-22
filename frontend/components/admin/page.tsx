// CAMINHO: frontend/app/main/admin/page.tsx
'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { useRagAdmin } from '@/hooks/useRagAdmin';
import RagUploadPanel from '@/components/admin/RagUploadPanel';
import RagDocumentsList from '@/components/admin/RagDocumentsList';
import ConfirmActionModal from '@/components/admin/ConfirmActionModal';

const AdminPage: React.FC = () => {
  const {
    items,
    total,
    page,
    limit,
    selectedItem,
    criticalAction,
    isDeleteModalOpen,
    isLoadingList,
    isUploading,
    isDeleting,
    isClearing,
    isReindexing,
    listError,
    operationMessage,
    operationError,
    lastUploadResponse,
    lastDeleteResponse,
    lastClearResponse,
    lastReindexResponse,
    refreshList,
    uploadFiles,
    openDeleteModal,
    closeDeleteModal,
    deleteSelectedItem,
    clearDatabase,
    reindexDatabase,
    resetFeedback,
  } = useRagAdmin();

  // Estados locais para modais de ações críticas
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isReindexModalOpen, setIsReindexModalOpen] = useState(false);

  // Helper para fechar todos os modais locais
  const closeAllLocalModals = useCallback(() => {
    setIsClearModalOpen(false);
    setIsReindexModalOpen(false);
  }, []);

  // Derivar status resumido da operação atual
  const currentStatus = useMemo(() => {
    if (isUploading) return 'Enviando arquivos...';
    if (isDeleting) return 'Excluindo documento...';
    if (isClearing) return 'Limpando base de dados...';
    if (isReindexing) return 'Reindexando base de dados...';
    if (isLoadingList) return 'Carregando lista...';
    return 'Pronto';
  }, [isUploading, isDeleting, isClearing, isReindexing, isLoadingList]);

  // Montar texto curto de resumo operacional
  const operationSummary = useMemo(() => {
    if (lastDeleteResponse) return `Documento excluído: ${lastDeleteResponse.message || 'Sucesso'}`;
    if (lastClearResponse) return `Base limpa: ${lastClearResponse.message || 'Sucesso'}`;
    if (lastReindexResponse) return `Reindexação concluída: ${lastReindexResponse.message || 'Sucesso'}`;
    return null;
  }, [lastDeleteResponse, lastClearResponse, lastReindexResponse]);

  // Handlers para ações críticas
  const handleOpenClearModal = useCallback(() => {
    if (!isClearing && !isReindexing && !isDeleting) {
      setIsClearModalOpen(true);
    }
  }, [isClearing, isReindexing, isDeleting]);

  const handleConfirmClear = useCallback(async () => {
    await clearDatabase(true);
    closeAllLocalModals();
  }, [clearDatabase, closeAllLocalModals]);

  const handleOpenReindexModal = useCallback(() => {
    if (!isClearing && !isReindexing && !isDeleting) {
      setIsReindexModalOpen(true);
    }
  }, [isClearing, isReindexing, isDeleting]);

  const handleConfirmReindex = useCallback(async () => {
    await reindexDatabase();
    closeAllLocalModals();
  }, [reindexDatabase, closeAllLocalModals]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6 space-y-8">
      {/* Cabeçalho */}
      <header className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Administração do RAG - DrTilápia</h1>
        <p className="text-gray-300">Gerencie documentos, uploads e operações críticas do sistema de RAG.</p>
        <div className="flex justify-center space-x-4">
          <span className="bg-blue-600 px-4 py-2 rounded-lg">Total de Documentos: {total}</span>
          <span className={`px-4 py-2 rounded-lg ${currentStatus === 'Pronto' ? 'bg-green-600' : 'bg-yellow-600'}`}>Status: {currentStatus}</span>
        </div>
      </header>

      {/* Grid principal */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Painel de Upload */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <RagUploadPanel
            isUploading={isUploading}
            operationMessage={operationMessage}
            operationError={operationError}
            lastUploadResponse={lastUploadResponse}
            onUpload={uploadFiles}
            onResetFeedback={resetFeedback}
            title="Upload de Documentos"
            description="Selecione arquivos para adicionar ao RAG."
            accept=".pdf,.txt,.docx"
            multiple={true}
            showMetadataFields={true}
          />
        </div>

        {/* Resumo Operacional */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg space-y-4">
          <h2 className="text-xl font-semibold">Resumo Operacional</h2>
          {operationSummary && (
            <div className="bg-green-700 p-4 rounded-lg">
              <p>{operationSummary}</p>
            </div>
          )}
          {operationMessage && (
            <div className="bg-blue-700 p-4 rounded-lg">
              <p>{operationMessage}</p>
            </div>
          )}
          {operationError && (
            <div className="bg-red-700 p-4 rounded-lg">
              <p>{operationError}</p>
            </div>
          )}
        </div>
      </div>

      {/* Lista de Documentos */}
      <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
        <RagDocumentsList
          items={items}
          total={total}
          isLoading={isLoadingList}
          error={listError}
          onRefresh={refreshList}
          onDelete={openDeleteModal}
          title="Documentos no RAG"
          description="Lista de documentos carregados."
          emptyTitle="Nenhum documento encontrado"
          emptyDescription="Faça upload de documentos para começar."
        />
      </div>

      {/* Zona Crítica */}
      <div className="bg-red-900 p-6 rounded-lg shadow-lg space-y-4">
        <h2 className="text-xl font-semibold text-red-200">Zona Crítica</h2>
        <p className="text-red-300">Ações irreversíveis. Use com cautela.</p>
        <div className="flex space-x-4">
          <button
            onClick={handleOpenClearModal}
            disabled={isClearing || isReindexing || isDeleting}
            className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 px-4 py-2 rounded-lg transition"
          >
            Limpar Base de Dados
          </button>
          <button
            onClick={handleOpenReindexModal}
            disabled={isClearing || isReindexing || isDeleting}
            className="bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 px-4 py-2 rounded-lg transition"
          >
            Reindexar Base
          </button>
        </div>
      </div>

      {/* Modais */}
      <ConfirmActionModal
        isOpen={isDeleteModalOpen}
        actionType="delete"
        selectedItem={selectedItem}
        isDeleting={isDeleting}
        isClearing={false}
        isReindexing={false}
        onClose={closeDeleteModal}
        onConfirmDelete={deleteSelectedItem}
        onConfirmClear={() => {}}
        onConfirmReindex={() => {}}
      />
      <ConfirmActionModal
        isOpen={isClearModalOpen}
        actionType="clear_all"
        selectedItem={null}
        isDeleting={false}
        isClearing={isClearing}
        isReindexing={false}
        onClose={closeAllLocalModals}
        onConfirmDelete={() => {}}
        onConfirmClear={handleConfirmClear}
        onConfirmReindex={() => {}}
      />
      <ConfirmActionModal
        isOpen={isReindexModalOpen}
        actionType="reindex"
        selectedItem={null}
        isDeleting={false}
        isClearing={false}
        isReindexing={isReindexing}
        onClose={closeAllLocalModals}
        onConfirmDelete={() => {}}
        onConfirmClear={() => {}}
        onConfirmReindex={handleConfirmReindex}
      />
    </div>
  );
};

export default AdminPage;
