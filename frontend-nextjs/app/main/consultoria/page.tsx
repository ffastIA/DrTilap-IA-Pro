'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { chatApi } from '@/lib/api';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

interface Message {
  user: string;
  ai: string;
}

export default function ConsultoriaPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll para última mensagem
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: (message: string) => {
      // Converter histórico para formato esperado pela API
      const history = messages.map((m) => [m.user, m.ai]);
      return chatApi.sendMessage(message, history);
    },
    onSuccess: (response) => {
      setMessages((prev) => [
        ...prev,
        { user: input, ai: response.answer },
      ]);
      setInput('');
      inputRef.current?.focus();
    },
    onError: (error: any) => {
      const errorMessage =
        error instanceof Error ? error.message : 'Erro ao processar mensagem. Tente novamente.';
      setMessages((prev) => [
        ...prev,
        { user: input, ai: `❌ ${errorMessage}` },
      ]);
      setInput('');
    },
  });

  const handleSend = () => {
    const trimmedInput = input.trim();
    if (!trimmedInput) return;

    // Adicionar mensagem do usuário imediatamente para feedback visual
    setMessages((prev) => [...prev, { user: trimmedInput, ai: '' }]);
    chatMutation.mutate(trimmedInput);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 backdrop-blur border-b border-slate-700 p-4 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">
              💬 Consultor Dr. Tilápia
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Faça perguntas sobre piscicultura e técnicas de tilápia
            </p>
          </div>
          <Link
            href="/main/hub"
            className="text-cyan-400 hover:text-cyan-300 font-medium transition duration-200"
          >
            ← Voltar ao Hub
          </Link>
        </div>
      </div>

      {/* Chat Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto max-w-4xl mx-auto w-full p-6 space-y-4"
      >
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="text-6xl mb-4">🐟</div>
              <h2 className="text-2xl font-bold text-slate-200 mb-2">
                Olá, {user?.email?.split('@')[0]}!
              </h2>
              <p className="text-slate-400 mb-6">
                Bem-vindo ao consultor IA. Faça uma pergunta sobre piscicultura, criação de tilápia,
                técnicas de cultivo ou qualquer dúvida técnica. Estou aqui para ajudar!
              </p>
              <div className="space-y-2 text-left bg-slate-700/30 p-4 rounded-lg">
                <p className="text-sm text-slate-300 font-semibold">💡 Exemplos de perguntas:</p>
                <ul className="text-sm text-slate-400 space-y-1">
                  <li>• "Qual é a temperatura ideal para criação de tilápia?"</li>
                  <li>• "Como identificar doenças em peixes?"</li>
                  <li>• "Qual a alimentação recomendada?"</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-2">
            {/* User Message */}
            <div className="flex justify-end">
              <div className="max-w-md bg-blue-600 text-white p-4 rounded-xl rounded-tr-none shadow-lg">
                <p className="text-sm leading-relaxed">{msg.user}</p>
              </div>
            </div>

            {/* AI Message */}
            <div className="flex justify-start">
              <div className="max-w-md bg-slate-700 text-white p-4 rounded-xl rounded-tl-none shadow-lg">
                {msg.ai ? (
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.ai}</p>
                ) : (
                  <div className="flex items-center gap-2">
                    <svg
                      className="animate-spin h-4 w-4"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    <span className="text-sm">Pensando...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="bg-slate-800/50 backdrop-blur border-t border-slate-700 p-4 sticky bottom-0">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Digite sua pergunta... (Enter para enviar)"
            className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500 transition duration-200"
            disabled={chatMutation.isPending}
          />
          <button
            onClick={handleSend}
            disabled={chatMutation.isPending || !input.trim()}
            className="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 text-white font-semibold rounded-lg transition-all duration-300 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {chatMutation.isPending ? (
              <>
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </>
            ) : (
              <>
                <span>Enviar</span>
                <span>→</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}