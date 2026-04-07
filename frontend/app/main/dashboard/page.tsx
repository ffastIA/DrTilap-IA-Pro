'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link href="/main/hub" className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
            ← Voltar ao Hub
          </Link>
          <h1 className="text-4xl font-bold text-white mt-4 mb-2">
            📊 Dashboard
          </h1>
          <p className="text-slate-400">
            Métricas e estatísticas do sistema Dr. Tilápia
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Card 1 */}
          <div className="glass p-6 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm mb-1">Usuário Logado</p>
                <p className="text-2xl font-bold text-white">
                  {user?.email || 'N/A'}
                </p>
              </div>
              <div className="text-4xl">👤</div>
            </div>
          </div>

          {/* Card 2 */}
          <div className="glass p-6 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm mb-1">Status</p>
                <p className="text-2xl font-bold text-green-400">Online</p>
              </div>
              <div className="text-4xl">✅</div>
            </div>
          </div>

          {/* Card 3 */}
          <div className="glass p-6 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm mb-1">Permissão</p>
                <p className="text-2xl font-bold text-white">
                  {user?.role === 'admin' ? 'Admin' : 'Usuário'}
                </p>
              </div>
              <div className="text-4xl">{user?.role === 'admin' ? '👑' : '📋'}</div>
            </div>
          </div>
        </div>

        {/* Coming Soon */}
        <div className="glass p-8 rounded-xl text-center">
          <div className="text-6xl mb-4">🚀</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Em Desenvolvimento
          </h2>
          <p className="text-slate-400 mb-6">
            Mais métricas, gráficos e estatísticas em breve!
          </p>
          <div className="inline-block text-sm text-slate-500 bg-slate-700/30 px-4 py-2 rounded-lg">
            Próximas atualizações: Histórico de consultas, Taxa de acurácia, Tempo de resposta
          </div>
        </div>
      </div>
    </div>
  );
}