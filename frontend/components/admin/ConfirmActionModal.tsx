// CAMINHO: frontend/components/admin/ConfirmActionModal.tsx
'use client';

import { useEffect, useMemo } from 'react';
import type { CriticalActionType, RagItem } from '@/types/rag-admin';

interface ConfirmActionModalProps {
  isOpen: boolean;
  actionType: CriticalActionType | null;
  selectedItem?: RagItem | null;
  isDeleting?: boolean;
  isClearing?: boolean;
  isReindexing?: boolean;
  onClose: () => void;
  onConfirmDelete?: () => Promise<void> | void;
  onConfirmClear?: () => Promise<void> | void;
  onConfirmReindex?: () => Promise<void> | void;
  title?: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

const ConfirmActionModal: React.FC<ConfirmActionModalProps> = ({
  isOpen,
  actionType,
  selectedItem,
  isDeleting = false,
  isClearing = false,
  isReindexing = false,
  onClose,
  onConfirmDelete,
  onConfirmClear,
  onConfirmReindex,
  title,
  description,
  confirmLabel,
  cancelLabel,
}) => {
  const getLoadingState = (action: CriticalActionType | null): boolean => {
    switch (action) {
      case 'delete_item':
        return isDeleting;
      case 'clear_all':
        return isClearing;
      case 'reindex':
        return isReindexing;
      default:
        return false;
    }
  };

  const getDefaultTexts = (action: CriticalActionType | null) => {
    switch (action) {
      case 'delete_item':
        return {
          title: 'Confirmar Exclusão',
          description: `Tem certeza de que deseja excluir o item ${selectedItem?.title || selectedItem?.id || 'selecionado'}? Esta ação não pode ser desfeita.`,
          confirmLabel: 'Excluir',
          cancelLabel: 'Cancelar',
        };
      case 'clear_all':
        return {
          title: 'Confirmar Limpeza',
          description: 'Tem certeza de que deseja limpar todos os itens? Esta ação não pode ser desfeita.',
          confirmLabel: 'Limpar Tudo',
          cancelLabel: 'Cancelar',
        };
      case 'reindex':
        return {
          title: 'Confirmar Reindexação',
          description: 'Tem certeza de que deseja reindexar todos os itens? Esta ação pode levar algum tempo.',
          confirmLabel: 'Reindexar',
          cancelLabel: 'Cancelar',
        };
      default:
        return {
          title: 'Confirmação',
          description: 'Tem certeza de que deseja prosseguir?',
          confirmLabel: 'Confirmar',
          cancelLabel: 'Cancelar',
        };
    }
  };

  const getConfirmButtonClasses = (action: CriticalActionType | null): string => {
    const baseClasses = 'px-4 py-2 rounded-md font-medium transition-colors';
    const loadingClasses = 'opacity-50 cursor-not-allowed';
    const isLoading = getLoadingState(action);

    switch (action) {
      case 'delete_item':
        return `${baseClasses} ${isLoading ? loadingClasses : 'bg-red-600 hover:bg-red-700 text-white'}`;
      case 'clear_all':
        return `${baseClasses} ${isLoading ? loadingClasses : 'bg-orange-600 hover:bg-orange-700 text-white'}`;
      case 'reindex':
        return `${baseClasses} ${isLoading ? loadingClasses : 'bg-blue-600 hover:bg-blue-700 text-white'}`;
      default:
        return `${baseClasses} ${isLoading ? loadingClasses : 'bg-gray-600 hover:bg-gray-700 text-white'}`;
    }
  };

  const isLoading = useMemo(() => getLoadingState(actionType), [actionType, isDeleting, isClearing, isReindexing]);
  const defaultTexts = useMemo(() => getDefaultTexts(actionType), [actionType, selectedItem]);

  const displayTitle = title || defaultTexts.title;
  const displayDescription = description || defaultTexts.description;
  const displayConfirmLabel = confirmLabel || defaultTexts.confirmLabel;
  const displayCancelLabel = cancelLabel || defaultTexts.cancelLabel;

  const handleConfirm = async () => {
    if (isLoading) return;
    switch (actionType) {
      case 'delete_item':
        if (onConfirmDelete) await onConfirmDelete();
        break;
      case 'clear_all':
        if (onConfirmClear) await onConfirmClear();
        break;
      case 'reindex':
        if (onConfirmReindex) await onConfirmReindex();
        break;
    }
  };

  const handleClose = () => {
    if (!isLoading) onClose();
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && !isLoading) {
      onClose();
    }
  };

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, isLoading]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-description"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="modal-title" className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          {displayTitle}
        </h2>
        <p id="modal-description" className="text-gray-700 dark:text-gray-300 mb-6">
          {displayDescription}
        </p>
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={isLoading}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${isLoading ? 'opacity-50 cursor-not-allowed' : 'bg-gray-200 hover:bg-gray-300 text-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white'}`}
          >
            {displayCancelLabel}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            className={getConfirmButtonClasses(actionType)}
          >
            {isLoading ? 'Processando...' : displayConfirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmActionModal;
