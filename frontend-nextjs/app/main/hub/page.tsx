'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useState } from 'react';

export default function HubPage() {
  const { user } = useAuth();
  const { clearAuth } = useAuthStore();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    authApi.logout();
    clearAuth();

    // Aguardar um pouco antes de redirecionar
    setTimeout(() => {
      router.push('/');
    }, 300);
  };

  const userEmail = user?.email || 'Usuário';
  const userName = userEmail.split('@')[0].charAt(0).toUpperCase() + userEmail.split('@')[0].slice(1);
  const isAdmin = user?.role === 'admin';

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Background Image com Overlay */}
      <div
        className="fixed inset-0 -z-10"
        style={{
          backgroundImage: "url('/hub01.jpeg')",
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'brightness(0.4) blur(4px)',
        }}
      />

      {/* Header com Logout */}
      <div className="absolute top-0 left-0 right-0 z-50 flex justify-between items-center p-6 bg-gradient-to-b from-black/50 to-transparent">
        <div>
          <h1 className="text-3xl font-bold text-white">
            🐟 Dr. Tilápia
          </h1>
        </div>
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="px-6 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-white font-semibold rounded-lg transition-all duration-300 disabled:cursor-not-allowed"
        >
          {isLoggingOut ? 'Saindo...' : 'Sair'}
        </button>
      </div>

      {/* Welcome Section */}
      <div className="absolute top-32 left-12 z-40">
        <h2 className="text-5xl font-bold text-white mb-2">
          Olá, {userName}! 👋
        </h2>
        <p className="text-slate-300 text-lg">
          Bem-vindo ao Hub de Ferramentas Dr. Tilápia
        </p>
        {isAdmin && (
          <span className="inline-block mt-3 px-3 py-1 bg-yellow-500/20 border border-yellow-500/50 text-yellow-200 text-xs font-semibold rounded-full">
            👑 Administrador
          </span>
        )}
      </div>

      {/* Cards Container */}
      <div className="relative w-full h-screen flex items-center justify-center px-4">
        <div className="flex flex-wrap gap-8 justify-center max-w-5xl">
          {/* Card: Consultoria */}
          <Link href="/main/consultoria">
            <div className="group cursor-pointer w-72 h-48 glass p-8 flex flex-col justify-center items-center text-center hover:scale-110 hover:shadow-2xl transition-all duration-300 hover:bg-opacity-20 rounded-2xl">
              <div className="text-6xl mb-4 group-hover:scale-125 transition-transform duration-300">
                💬
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">
                Consultoria IA
              </h3>
              <p className="text-slate-300 text-sm">
                Chat interativo com análise de manuais técnicos via RAG
              </p>
            </div>
          </Link>

          {/* Card: Dashboard */}
          <Link href="/main/dashboard">
            <div className="group cursor-pointer w-72 h-48 glass p-8 flex flex-col justify-center items-center text-center hover:scale-110 hover:shadow-2xl transition-all duration-300 hover:bg-opacity-20 rounded-2xl">
              <div className="text-6xl mb-4 group-hover:scale-125 transition-transform duration-300">
                📊
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">
                Dashboard
              </h3>
              <p className="text-slate-300 text-sm">
                Métricas e estatísticas em tempo real do sistema
              </p>
            </div>
          </Link>

          {/* Card: Admin (Condicional) */}
          {isAdmin && (
            <Link href="/main/admin">
              <div className="group cursor-pointer w-72 h-48 glass p-8 flex flex-col justify-center items-center text-center hover:scale-110 hover:shadow-2xl transition-all duration-300 hover:bg-opacity-20 rounded-2xl">
                <div className="text-6xl mb-4 group-hover:scale-125 transition-transform duration-300">
                  ⚙️
                </div>
                <h3 className="text-2xl font-bold text-white mb-2">
                  Administração
                </h3>
                <p className="text-slate-300 text-sm">
                  Upload de documentos e gestão da base de conhecimento
                </p>
              </div>
            </Link>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="absolute bottom-6 left-0 right-0 text-center text-xs text-slate-500">
        <p>Dr. Tilápia 2.0 | Powered by Next.js + FastAPI + Supabase</p>
      </div>
    </div>
  );
}