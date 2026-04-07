'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import ChatMessage from '@/components/ChatMessage';
import LoadingSpinner from '@/components/LoadingSpinner';
import Button from '@/components/Button';
import { SendIcon, Trash2Icon, MessageSquareTextIcon } from 'lucide-react';

export default function ConsultoriaPage() {
  const [inputMessage, setInputMessage] = useState('');
  const { messages, isLoading, error, sendMessage, clearChat } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      sendMessage(inputMessage);
      setInputMessage('');
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] gap-6">
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Consultoria de IA</h1>
        <p className="text-text-secondary">
          Faça perguntas sobre piscicultura e receba respostas baseadas em documentos
        </p>
      </div>

      {/* Área de Mensagens */}
      <div className="flex-1 overflow-y-auto glass-effect rounded-lg p-6 flex flex-col">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-secondary">
            <MessageSquareTextIcon size={64} className="mb-4 text-primary" />
            <p className="text-xl font-medium">Comece sua consultoria fazendo uma pergunta!</p>
            <p className="text-sm mt-2">Exemplo: "O que é o BIA?"</p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg.text}
                isUser={msg.sender === 'user'}
              />
            ))}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="flex items-center gap-2 text-text-secondary">
                  <LoadingSpinner size="w-5 h-5" />
                  <span>Consultando a base de conhecimento...</span>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Mensagem de Erro */}
      {error && (
        <div className="bg-error/20 text-error p-4 rounded-lg text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Input de Mensagem */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Pergunte algo sobre piscicultura..."
          className="flex-1 p-4 rounded-lg bg-surface border border-gray-700 text-white placeholder-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isLoading}
        />
        <Button
          type="submit"
          isLoading={isLoading}
          disabled={isLoading || !inputMessage.trim()}
          className="px-6"
        >
          <SendIcon size={20} />
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={clearChat}
          disabled={isLoading || messages.length === 0}
          className="px-6"
        >
          <Trash2Icon size={20} />
        </Button>
      </form>
    </div>
  );
}