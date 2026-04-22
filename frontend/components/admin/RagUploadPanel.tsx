// CAMINHO: frontend/components/admin/RagUploadPanel.tsx
'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RagUploadResponse } from '@/types/rag-admin';

interface RagUploadPanelProps {
  isUploading?: boolean;
  operationMessage?: { type: 'success' | 'error' | 'info'; text: string } | string | null;
  operationError?: { message: string; code?: string; details?: any } | string | null;
  lastUploadResponse?: RagUploadResponse | null;
  onUpload: (files: File[], extraData?: Record<string, any>) => Promise<void> | void;
  onResetFeedback?: () => void;
  title?: string;
  description?: string;
  accept?: string;
  multiple?: boolean;
  showMetadataFields?: boolean;
}

const RagUploadPanel: React.FC<RagUploadPanelProps> = ({
  isUploading = false,
  operationMessage,
  operationError,
  lastUploadResponse,
  onUpload,
  onResetFeedback,
  title = 'Upload de Documentos',
  description = 'Arraste e solte arquivos aqui ou clique para selecionar.',
  accept = '.pdf,.txt,.doc,.docx',
  multiple = true,
  showMetadataFields = false,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [metadata, setMetadata] = useState({
    categoria: '',
    origem: '',
    observacoes: '',
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  const normalizeMessage = useCallback((msg: any): { type: 'success' | 'error' | 'info'; text: string } | null => {
    if (!msg) return null;
    if (typeof msg === 'string') {
      return { type: 'info', text: msg };
    }
    return msg;
  }, []);

  const normalizeErrorMessage = useCallback((err: any): string => {
    if (!err) return '';
    if (typeof err === 'string') return err;
    return err.message || 'Erro desconhecido';
  }, []);

  const isUploadSuccess = useCallback((): boolean => {
    if (lastUploadResponse?.totalUploaded > 0) return true;
    const msg = normalizeMessage(operationMessage);
    if (msg && msg.type === 'success') return true;
    if (typeof operationMessage === 'string' && /sucesso|enviado|upload realizado/i.test(operationMessage)) return true;
    return false;
  }, [lastUploadResponse, operationMessage]);

  const buildExtraData = useCallback((): Record<string, any> => {
    const extra: Record<string, any> = {};
    if (metadata.categoria) extra.categoria = metadata.categoria;
    if (metadata.origem) extra.origem = metadata.origem;
    if (metadata.observacoes) extra.observacoes = metadata.observacoes;
    return extra;
  }, [metadata]);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;
    const newFiles = Array.from(files);
    setSelectedFiles(prev => {
      const combined = [...prev, ...newFiles];
      const unique = combined.filter((file, index, self) =>
        self.findIndex(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified) === index
      );
      return unique;
    });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
  }, [handleFileSelect]);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedFiles([]);
    setMetadata({ categoria: '', origem: '', observacoes: '' });
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0 || isUploading) return;
    const extraData = buildExtraData();
    await onUpload(selectedFiles, extraData);
  }, [selectedFiles, isUploading, buildExtraData, onUpload]);

  useEffect(() => {
    if (isUploadSuccess()) {
      clearSelection();
    }
  }, [isUploadSuccess, clearSelection]);

  const normalizedMessage = useMemo(() => normalizeMessage(operationMessage), [operationMessage]);
  const normalizedError = useMemo(() => normalizeErrorMessage(operationError), [operationError]);

  return (
    <div className="bg-gray-900 bg-opacity-80 backdrop-blur-md rounded-lg p-6 shadow-lg max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-white mb-4">{title}</h2>
      <p className="text-gray-300 mb-6">{description}</p>

      <div
        className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-gray-500 transition-colors"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={handleClick}
      >
        <p className="text-gray-400">Arraste e solte arquivos aqui ou clique para selecionar</p>
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      {selectedFiles.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-white mb-4">Arquivos Selecionados</h3>
          <ul className="space-y-2">
            {selectedFiles.map((file, index) => (
              <li key={index} className="flex justify-between items-center bg-gray-800 p-3 rounded">
                <span className="text-gray-200">{file.name} ({formatFileSize(file.size)})</span>
                <button
                  onClick={() => removeFile(index)}
                  className="text-red-400 hover:text-red-300"
                  disabled={isUploading}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {showMetadataFields && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Categoria"
            value={metadata.categoria}
            onChange={(e) => setMetadata(prev => ({ ...prev, categoria: e.target.value }))}
            className="bg-gray-800 text-white p-3 rounded border border-gray-600 focus:border-blue-500"
            disabled={isUploading}
          />
          <input
            type="text"
            placeholder="Origem"
            value={metadata.origem}
            onChange={(e) => setMetadata(prev => ({ ...prev, origem: e.target.value }))}
            className="bg-gray-800 text-white p-3 rounded border border-gray-600 focus:border-blue-500"
            disabled={isUploading}
          />
          <textarea
            placeholder="Observações"
            value={metadata.observacoes}
            onChange={(e) => setMetadata(prev => ({ ...prev, observacoes: e.target.value }))}
            className="bg-gray-800 text-white p-3 rounded border border-gray-600 focus:border-blue-500"
            disabled={isUploading}
          />
        </div>
      )}

      <div className="mt-6 flex space-x-4">
        <button
          onClick={handleUpload}
          disabled={selectedFiles.length === 0 || isUploading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-2 rounded transition-colors"
        >
          {isUploading ? 'Enviando...' : 'Enviar'}
        </button>
        <button
          onClick={clearSelection}
          disabled={isUploading}
          className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 text-white px-6 py-2 rounded transition-colors"
        >
          Limpar Seleção
        </button>
      </div>

      {normalizedMessage && (
        <div className={`mt-4 p-3 rounded ${normalizedMessage.type === 'success' ? 'bg-green-800' : normalizedMessage.type === 'error' ? 'bg-red-800' : 'bg-blue-800'} text-white`}>
          {normalizedMessage.text}
        </div>
      )}

      {normalizedError && (
        <div className="mt-4 p-3 rounded bg-red-800 text-white">
          {normalizedError}
        </div>
      )}

      {lastUploadResponse && (
        <div className="mt-6 bg-gray-800 p-4 rounded">
          <h3 className="text-lg font-semibold text-white mb-4">Resumo do Último Upload</h3>
          <p className="text-gray-300">Enviados: {lastUploadResponse.totalUploaded}</p>
          <p className="text-gray-300">Falhas: {lastUploadResponse.totalFailed}</p>
          {lastUploadResponse.uploaded.length > 0 && (
            <div className="mt-4">
              <h4 className="text-md font-semibold text-white">Enviados:</h4>
              <ul className="list-disc list-inside text-gray-300">
                {lastUploadResponse.uploaded.map((item, index) => (
                  <li key={index}>{item.title || item.id}</li>
                ))}
              </ul>
            </div>
          )}
          {lastUploadResponse.failed.length > 0 && (
            <div className="mt-4">
              <h4 className="text-md font-semibold text-white">Falhas:</h4>
              <ul className="list-disc list-inside text-gray-300">
                {lastUploadResponse.failed.map((fail, index) => (
                  <li key={index}>{fail.file}: {fail.error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RagUploadPanel;
