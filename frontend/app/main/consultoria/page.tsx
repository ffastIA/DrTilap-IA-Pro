// CAMINHO: frontend/app/main/consultoria/page.tsx

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useChat } from '@/hooks/useChat';
import ChatMessage from '@/components/ChatMessage';
import LoadingSpinner from '@/components/LoadingSpinner';
import Button from '@/components/Button';
import { SendIcon, Trash2Icon, ArrowLeftIcon, MessageSquareTextIcon } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  sender: string;
}

export default function Consultoria() {
  const router = useRouter();

  const { messages, isLoading, error, sendMessage, clearChat } = useChat() as {
    messages: Message[];
    isLoading: boolean;
    error: string | null;
    sendMessage: (message: string) => void;
    clearChat: () => void;
  };

  const [input, setInput] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/main/hub');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      sendMessage(input);
      setInput('');
    }
  };

  const handleClear = () => {
    clearChat();
    setInput('');
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="p-4 border-b border-border bg-card shadow-sm">
        <div className="flex items-center gap-4 max-w-4xl mx-auto">
          <Button
            variant="secondary"
            onClick={handleBack}
            className="flex items-center gap-2 p-2 h-auto"
            size="sm"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Voltar
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Consultoria de IA</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Faça perguntas sobre piscicultura e tilápias
            </p>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col overflow-hidden max-w-4xl mx-auto w-full">
        <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-20">
          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg text-destructive text-sm">
              Erro: {error}
            </div>
          )}

          {messages.length === 0 && !isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <MessageSquareTextIcon className="w-20 h-20 text-muted-foreground mb-6 opacity-60" />
              <h2 className="text-2xl font-semibold text-foreground mb-3">
                Bem-vindo à Consultoria de IA
              </h2>
              <p className="text-muted-foreground max-w-md leading-relaxed">
                Digite sua pergunta sobre criação de tilápias, manejo de tanques, alimentação ou qualquer dúvida em piscicultura.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg.text}
                isUser={msg.sender === 'user'}
              />
            ))
          )}

          {isLoading && (
            <div className="flex justify-end p-4">
              <LoadingSpinner />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="p-6 border-t border-border bg-card shrink-0">
          <div className="flex gap-3 max-w-4xl mx-auto w-full">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Digite sua pergunta sobre tilápias..."
              className="flex-1 px-4 py-3 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all bg-background text-foreground placeholder:text-muted-foreground"
              disabled={isLoading}
            />
            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              disabled={!input.trim() || isLoading}
              className="min-w-[44px] p-3"
            >
              <SendIcon className="w-5 h-5" />
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleClear}
              disabled={isLoading || messages.length === 0}
              className="min-w-[44px] p-3"
            >
              <Trash2Icon className="w-5 h-5" />
            </Button>
          </div>
        </form>
      </main>
    </div>
  );
}
