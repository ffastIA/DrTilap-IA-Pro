// CAMINHO: frontend/components/admin/RagDocumentsList.tsx
'use client';

import { useMemo } from 'react';
import type { RagAdminError, RagItem } from '@/types/rag-admin';

interface RagDocumentsListProps {
  items?: RagItem[] | null;
  total?: number;
  isLoading?: boolean;
  error?: RagAdminError | null;
  onRefresh?: () => void;
  onDelete?: (item: RagItem) => void;
  title?: string;
  description?: string;
  emptyTitle?: string;
  emptyDescription?: string;
}

function RagDocumentsList({
  items,
  total,
  isLoading = false,
  error,
  onRefresh,
  onDelete,
  title = 'Documentos RAG',
  description = 'Lista de documentos processados para o sistema RAG.',
  emptyTitle = 'Nenhum documento encontrado',
  emptyDescription = 'Não há documentos disponíveis no momento.',
}: RagDocumentsListProps) {
  // Normalizar items para evitar erro de map
  const safeItems = Array.isArray(items) ? items : [];

  // Calcular total seguro
  const safeTotal = typeof total === 'number' && !isNaN(total) ? total : safeItems.length;

  // Memoizar dados processados
  const processedItems = useMemo(() => {
    return safeItems.map((item) => ({
      ...item,
      formattedCreatedAt: formatDate(item.createdAt),
      formattedUpdatedAt: formatDate(item.updatedAt),
      summarizedContent: summarizeText(item.content, 150),
      metadataList: extractMetadata(item.metadata),
    }));
  }, [safeItems]);

  if (isLoading) {
    return (
      <div className="p-6 bg-gray-900/50 backdrop-blur-sm rounded-lg border border-gray-700/50">
        <h2 className="text-xl font-semibold text-white mb-2">{title}</h2>
        <p className="text-gray-400 mb-4">{description}</p>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-800/50 rounded-lg p-4">
              <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-700 rounded w-1/2 mb-1"></div>
              <div className="h-3 bg-gray-700 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-gray-900/50 backdrop-blur-sm rounded-lg border border-red-500/50">
        <h2 className="text-xl font-semibold text-white mb-2">Erro</h2>
        <p className="text-red-400 mb-4">{error.message || 'Ocorreu um erro ao carregar os documentos.'}</p>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
          >
            Tentar Novamente
          </button>
        )}
      </div>
    );
  }

  if (processedItems.length === 0) {
    return (
      <div className="p-6 bg-gray-900/50 backdrop-blur-sm rounded-lg border border-gray-700/50 text-center">
        <h2 className="text-xl font-semibold text-white mb-2">{emptyTitle}</h2>
        <p className="text-gray-400">{emptyDescription}</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900/50 backdrop-blur-sm rounded-lg border border-gray-700/50">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-semibold text-white">{title}</h2>
          <p className="text-gray-400">{description}</p>
        </div>
        <div className="text-gray-400 text-sm">
          Total: {safeTotal}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {processedItems.map((item) => (
          <div key={item.id} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50 hover:bg-gray-800/70 transition-colors">
            <h3 className="text-lg font-medium text-white mb-2">
              {item.title || 'Sem título'}
            </h3>
            <p className="text-gray-400 text-sm mb-1">ID: {item.id}</p>
            <p className="text-gray-400 text-sm mb-1">Criado em: {item.formattedCreatedAt}</p>
            <p className="text-gray-400 text-sm mb-2">Atualizado em: {item.formattedUpdatedAt}</p>
            <p className="text-gray-300 text-sm mb-2">{item.summarizedContent}</p>
            {item.metadataList.length > 0 && (
              <div className="mb-2">
                <p className="text-gray-400 text-sm font-medium">Metadados:</p>
                <ul className="text-gray-300 text-xs space-y-1">
                  {item.metadataList.slice(0, 3).map((meta, idx) => (
                    <li key={idx}>
                      <strong>{meta.key}:</strong> {meta.value}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(item)}
                className="mt-2 px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
              >
                Excluir
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Helpers internos

function formatDate(date: Date | string | null | undefined): string {
  if (!date) return 'Data indisponível';
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return 'Data indisponível';
    return d.toLocaleDateString('pt-BR');
  } catch {
    return 'Data indisponível';
  }
}

function summarizeText(text: string | null | undefined, maxLength = 100): string {
  if (!text) return 'Sem prévia de conteúdo';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

function extractMetadata(metadata: Record<string, any> | null | undefined): Array<{ key: string; value: string }> {
  if (!metadata || typeof metadata !== 'object') return [];
  return Object.entries(metadata)
    .filter(([key, value]) => value != null)
    .map(([key, value]) => ({ key, value: String(value) }));
}

export default RagDocumentsList;
