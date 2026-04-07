// components/DocumentCard.tsx
import React from 'react';
import { FaFilePdf, FaCheckCircle, FaTimesCircle, FaSpinner } from 'react-icons/fa'; // Ícones

interface DocumentCardProps {
  filename: string; // Nome do arquivo<br/>
  status: 'pending' | 'processed' | 'failed'; // Status do documento<br/>
  onDelete?: (filename: string) => void; // Função para deletar (opcional)
}

const DocumentCard: React.FC<DocumentCardProps> = ({ filename, status, onDelete }) => {
  const statusColors = {
    pending: 'text-accent', // Amarelo para pendente<br/>
    processed: 'text-success', // Verde para processado<br/>
    failed: 'text-error', // Vermelho para falha
  };

  const statusIcons = {
    pending: <FaSpinner className="animate-spin" />, // Spinner para pendente<br/>
    processed: <FaCheckCircle />, // Check para processado<br/>
    failed: <FaTimesCircle />, // X para falha
  };

  return (
    <GlassContainer className="flex items-center justify-between p-4 mb-4">
      <div className="flex items-center">
        <FaFilePdf className="text-secondary text-2xl mr-3" /> {/* Ícone de PDF */}
        <span className="text-text font-medium">{filename}</span> {/* Nome do arquivo */}
      </div>
      <div className="flex items-center">
        <span className={`${statusColors[status]} mr-2`}>
          {statusIcons[status]} {/* Ícone de status */}
        </span>
        <span className={`text-sm capitalize ${statusColors[status]}`}>
          {status === 'pending' ? 'Processando...' : status === 'processed' ? 'Processado' : 'Falha'}
        </span>
        {onDelete && status !== 'pending' && ( // Botão de deletar, visível se não estiver pendente
          <button
            onClick={() => onDelete(filename)}
            className="ml-4 text-textSecondary hover:text-error transition-colors duration-200"
            title="Remover documento"
          >
            &times; {/* Ícone de fechar/remover */}
          </button>
        )}
      </div>
    </GlassContainer>
  );
};

export default DocumentCard;