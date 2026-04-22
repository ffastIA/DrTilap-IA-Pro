// CAMINHO: frontend/app/main/admin/page.tsx
'use client';

import { useCallback, useMemo, useState } from 'react';
import useRagAdmin from '@/hooks/useRagAdmin';
import RagUploadPanel from '@/components/admin/RagUploadPanel';
import RagDocumentsList from '@/components/admin/RagDocumentsList';
import ConfirmActionModal from '@/components/admin/ConfirmActionModal';

export default function AdminPage() {
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

  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isReindexModalOpen, setIsReindexModalOpen] = useState(false);
  const [clearMode, setClearMode] = useState<'simulate' | 'execute'>('simulate');

  const closeAllLocalModals = useCallback(() => {
    setIsClearModalOpen(false);
    setIsReindexModalOpen(false);
  }, []);

  const statusBadge = useMemo(() => {
    if (isUploading) return { text: 'Enviando', color: 'bg-blue-500' };
    if (isDeleting) return { text: 'Excluindo', color: 'bg-red-500' };
    if (isClearing) return { text: 'Limpando', color: 'bg-orange-500' };
    if (isReindexing) return { text: 'Reindexando', color: 'bg-purple-500' };
    return { text: 'Pronto', color: 'bg-green-500' };
  }, [isUploading, isDeleting, isClearing, isReindexing]);

  const recentActivity = useMemo(() => {
    const activities = [];
    if (lastDeleteResponse) {
      activities.push(
        `Exclusão: ${lastDeleteResponse.deleted?.length || 0} deletados, ${lastDeleteResponse.failed?.length || 0} falharam.`
      );
    }
    if (lastClearResponse) {
      activities.push(
        `Limpeza: ${lastClearResponse.cleared || 0} limpos, total ${lastClearResponse.count || 0}.`
      );
    }
    if (lastReindexResponse) {
      activities.push(
        `Reindexação: ${lastReindexResponse.reindexed || 0} reindexados, total ${lastReindexResponse.count || 0}, status: ${lastReindexResponse.status || 'Desconhecido'}.`
      );
    }
    return activities;
  }, [lastDeleteResponse, lastClearResponse, lastReindexResponse]);

  const handleClearSimulate = useCallback(() => {
    setClearMode('simulate');
    setIsClearModalOpen(true);
  }, []);

  const handleClearExecute = useCallback(() => {
    setClearMode('execute');
    setIsClearModalOpen(true);
  }, []);

  const handleReindex = useCallback(() => {
    setIsReindexModalOpen(true);
  }, []);

  const handleConfirmClear = useCallback(async () => {
    await clearDatabase(clearMode === 'execute');
    closeAllLocalModals();
  }, [clearDatabase, clearMode, closeAllLocalModals]);

  const handleConfirmReindex = useCallback(async () => {
    await reindexDatabase();
    closeAllLocalModals();
  }, [reindexDatabase, closeAllLocalModals]);

  const isAnyCriticalAction = isDeleting || isClearing || isReindexing;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Cabeçalho */}
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h1 className="text-3xl font-bold mb-2">Administração do RAG</h1>
          <p className="text-gray-300 mb-4">
            Gerencie documentos e base de conhecimento. Upload ainda depende da confirmação do endpoint real do backend.
          </p>
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="bg-gray-700 px-3 py-1 rounded">Total: {total}</span>
            <span className="bg-gray-700 px-3 py-1 rounded">Página: {page}</span>
            <span className="bg-gray-700 px-3 py-1 rounded">Limite: {limit}</span>
            <span className={`px-3 py-1 rounded text-white ${statusBadge.color}`}>{statusBadge.text}</span>
          </div>
        </div>

        {/* Grid Principal */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upload */}
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <RagUploadPanel
              isUploading={isUploading}
              operationMessage={operationMessage}
              operationError={operationError}
              lastUploadResponse={lastUploadResponse}
              onUpload={uploadFiles}
              onResetFeedback={resetFeedback}
              title="Upload de Documentos"
              description="Selecione arquivos para adicionar à base de conhecimento."
              accept=".pdf,.txt,.docx"
              multiple={true}
              showMetadataFields={true}
            />
          </div>

          {/* Feedback e Atividade */}
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700 space-y-4">
            <h2 className="text-xl font-semibold">Atividade Recente</h2>
            {recentActivity.length > 0 ? (
              <ul className="space-y-2 text-sm text-gray-300">
                {recentActivity.map((activity, index) => (
                  <li key={index} className="bg-gray-700/50 p-2 rounded">{activity}</li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">Nenhuma atividade recente.</p>
            )}
          </div>
        </div>

        {/* Lista de Documentos */}
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <RagDocumentsList
            items={items}
            total={total}
            isLoading={isLoadingList}
            error={listError}
            onRefresh={refreshList}
            onDelete={openDeleteModal}
            title="Documentos na Base"
            description="Lista de documentos carregados."
            emptyTitle="Nenhum documento encontrado"
            emptyDescription="Faça upload de documentos para começar."
          />
        </div>

        {/* Zona Crítica */}
        <div className="bg-red-900/20 backdrop-blur-sm rounded-lg p-6 border border-red-700">
          <h2 className="text-xl font-semibold text-red-400 mb-4">Zona Crítica</h2>
          <p className="text-gray-300 mb-4">Ações destrutivas. Use com cautela.</p>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={handleClearSimulate}
              disabled={isAnyCriticalAction}
              className="bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 px-4 py-2 rounded text-white"
            >
              Simular Limpeza
            </button>
            <button
              onClick={handleClearExecute}
              disabled={isAnyCriticalAction}
              className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 px-4 py-2 rounded text-white"
            >
              Executar Limpeza
            </button>
            <button
              onClick={handleReindex}
              disabled={isAnyCriticalAction}
              className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 px-4 py-2 rounded text-white"
            >
              Reindexar Base
            </button>
          </div>
        </div>
      </div>

      {/* Modais */}
      <ConfirmActionModal
        isOpen={isDeleteModalOpen}
        actionType={criticalAction}
        selectedItem={selectedItem}
        isDeleting={isDeleting}
        isClearing={isClearing}
        isReindexing={isReindexing}
        onClose={closeDeleteModal}
        onConfirmDelete={async () => { await deleteSelectedItem(); }}
        onConfirmClear={() => {}}
        onConfirmReindex={() => {}}
      />

      <ConfirmActionModal
        isOpen={isClearModalOpen}
        actionType="clear_all"
        selectedItem={null}
        isDeleting={isDeleting}
        isClearing={isClearing}
        isReindexing={isReindexing}
        onClose={closeAllLocalModals}
        onConfirmDelete={() => {}}
        onConfirmClear={handleConfirmClear}
        onConfirmReindex={() => {}}
        title={clearMode === 'simulate' ? 'Simular Limpeza da Base' : 'Executar Limpeza da Base'}
        description={clearMode === 'simulate' ? 'Isso simulará a limpeza sem afetar os dados.' : 'Isso removerá todos os documentos permanentemente.'}
        confirmLabel={clearMode === 'simulate' ? 'Simular' : 'Executar'}
        cancelLabel="Cancelar"
      />

      <ConfirmActionModal
        isOpen={isReindexModalOpen}
        actionType="reindex"
        selectedItem={null}
        isDeleting={isDeleting}
        isClearing={isClearing}
        isReindexing={isReindexing}
        onClose={closeAllLocalModals}
        onConfirmDelete={() => {}}
        onConfirmClear={() => {}}
        onConfirmReindex={handleConfirmReindex}
        title="Reindexar Base de Dados"
        description="Isso reindexará todos os documentos para otimizar a busca."
        confirmLabel="Reindexar"
        cancelLabel="Cancelar"
      />
    </div>
  );
}
