// components/ChatMessage.tsx
import React from 'react';
import { colors } from '@/lib/colors'; // Importa a paleta de cores

interface ChatMessageProps {
  message: string; // Conteúdo da mensagem<br/>
  isUser: boolean; // True se a mensagem for do usuário, false para o assistente<br/>
  sources?: string[]; // Fontes da informação (opcional)
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isUser, sources }) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[70%] p-4 rounded-lg shadow-md ${
          isUser
            ? 'bg-primary text-white' // Estilo para mensagens do usuário
            : 'glass-effect text-text' // Estilo glassmorphism para mensagens do assistente
        }`}
        style={{
          backgroundColor: isUser ? colors.primary : colors.glassLight, // Usa cores da paleta<br/>
          borderColor: isUser ? 'transparent' : colors.glassBorder,
        }}
      >
        <p className="text-sm md:text-base whitespace-pre-wrap">{message}</p> {/* Exibe a mensagem */}
        {sources && sources.length > 0 && !isUser && ( // Exibe fontes apenas para mensagens do assistente
          <div className="mt-2 text-xs text-textSecondary italic">
            <p>Fontes:</p>
            <ul className="list-disc list-inside">
              {sources.map((source, index) => (
                <li key={index}>{source}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;