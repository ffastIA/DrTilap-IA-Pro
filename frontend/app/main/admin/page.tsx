'use client';

import React, { useState, useRef } from 'react';
import { useUpload } from '@/hooks/useUpload';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { UploadCloudIcon, FileTextIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';

export default function AdminPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { uploadFile, isUploading, uploadProgress, error, successMessage } = useUpload();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadClick = () => {
    if (selectedFile) {
      uploadFile(selectedFile)
        .then(() => {
          setSelectedFile(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        })
        .catch((err) => {
          console.error('Upload failed:', err);
        });
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-white mb-4">Administração RAG</h1>
      <p className="text-text-secondary text-lg mb-8">
        Faça upload de documentos PDF para expandir a base de conhecimento do consultor de IA.
      </p>

      <div className="glass-effect p-8 rounded-lg max-w-2xl mx-auto">
        <div
          className="border-2 border-dashed border-gray-600 rounded-lg p-10 text-center cursor-pointer hover:border-primary transition-colors duration-200"
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf"
            className="hidden"
            disabled={isUploading}
          />
          <UploadCloudIcon size={48} className="text-primary mx-auto mb-4" />
          <p className="text-white text-lg font-medium">
            {selectedFile ? selectedFile.name : 'Arraste e solte seu PDF aqui, ou clique para selecionar'}
          </p>
          <p className="text-text-secondary text-sm mt-2">Apenas arquivos .pdf são aceitos.</p>
        </div>

        {selectedFile && (
          <div className="mt-6 flex items-center justify-between bg-background p-4 rounded-lg border border-gray-700">
            <div className="flex items-center">
              <FileTextIcon size={20} className="text-secondary mr-3" />
              <span className="text-white">{selectedFile.name}</span>
            </div>
            <Button onClick={handleUploadClick} isLoading={isUploading} disabled={isUploading}>
              {isUploading ? 'Enviando...' : 'Fazer Upload'}
            </Button>
          </div>
        )}

        {isUploading && (
          <div className="mt-4">
            <div className="w-full bg-gray-700 rounded-full h-2.5">
              <div className="bg-primary h-2.5 rounded-full" style={{ width: `${uploadProgress}%` }}></div>
            </div>
            <p className="text-text-secondary text-sm mt-2 text-center">{uploadProgress}% Concluído</p>
          </div>
        )}

        {successMessage && (
          <div className="mt-6 flex items-center bg-success/20 text-success p-4 rounded-lg">
            <CheckCircleIcon size={20} className="mr-3" />
            <span>{successMessage}</span>
          </div>
        )}

        {error && (
          <div className="mt-6 flex items-center bg-error/20 text-error p-4 rounded-lg">
            <XCircleIcon size={20} className="mr-3" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}