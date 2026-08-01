// components/ChatMessage.tsx
import React from 'react';
import type { ChatSource } from '@/hooks/useChat';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
  sources?: ChatSource[];
}

function formatSource(source: ChatSource): string {
  if (source.page_start == null) {
    return source.file;
  }
  const pages =
    source.page_end != null && source.page_end !== source.page_start
      ? `p. ${source.page_start + 1}-${source.page_end + 1}`
      : `p. ${source.page_start + 1}`;
  return `${source.file} (${pages})`;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isUser, sources }) => {
  return (
    <div className={`flex mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-3 rounded-lg ${
          isUser
            ? 'bg-primary text-white rounded-br-none'
            : 'bg-surface text-text-secondary border border-gray-700 rounded-bl-none'
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{message}</p>
        {!isUser && sources && sources.length > 0 && (
          <div className="mt-3 pt-2 border-t border-gray-700/50 text-xs text-text-secondary/80">
            <span className="font-medium">Fontes: </span>
            {sources.map(formatSource).join(' · ')}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
