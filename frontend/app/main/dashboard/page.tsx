// CAMINHO: frontend/app/main/dashboard/page.tsx

'use client';

import { useRouter } from 'next/navigation';
import useAuth from '@/hooks/useAuth';

export default function Dashboard() {
  const router = useRouter();
  const { user } = useAuth();

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/main/hub');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/30 to-black text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header com botão Voltar e Título */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={handleBack}
            className="bg-white/10 backdrop-blur-md border border-white/20 px-6 py-3 rounded-xl hover:bg-white/20 transition-all duration-300 flex items-center gap-2 shadow-xl hover:shadow-2xl"
          >
            ← Voltar
          </button>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent drop-shadow-2xl">
            Dashboard
          </h1>
          <div className="w-12" /> {/* Spacer para balancear */}
        </div>

        {/* Subtítulo de métricas e estatísticas */}
        <p className="text-2xl text-gray-300 mb-16 max-w-3xl leading-relaxed">
          Acompanhe métricas e estatísticas em tempo real do seu painel de controle DrTilápia.
        </p>

        {/* Três Cards: Usuário, Status, Permissão */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-16">
          {/* Card Usuário Logado */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/20 rounded-3xl p-10 hover:bg-white/10 transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-3xl">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-green-400 to-blue-500 rounded-2xl flex items-center justify-center shadow-lg">
                <span className="text-2xl font-bold">👤</span>
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-gray-200 mb-2">Usuário Logado</h2>
                <p className="text-3xl font-bold text-green-400 break-all">{user?.email || 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Card Status Online */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/20 rounded-3xl p-10 hover:bg-white/10 transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-3xl">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-emerald-400 to-green-500 rounded-2xl flex items-center justify-center shadow-lg relative">
                <span className="text-2xl font-bold">●</span>
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-400 rounded-full animate-ping"></div>
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-gray-200 mb-2">Status</h2>
                <p className="text-3xl font-bold text-emerald-400">Online</p>
              </div>
            </div>
          </div>

          {/* Card Permissão */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/20 rounded-3xl p-10 hover:bg-white/10 transition-all duration-300 hover:scale-105 shadow-2xl hover:shadow-3xl">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-400 to-purple-500 rounded-2xl flex items-center justify-center shadow-lg">
                <span className="text-2xl font-bold">🔑</span>
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-gray-200 mb-2">Permissão</h2>
                <p className="text-3xl font-bold text-blue-400 capitalize">{user?.role || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Bloco Em Desenvolvimento */}
        <div className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 backdrop-blur-xl border border-yellow-400/30 rounded-3xl p-16 text-center shadow-2xl">
          <h2 className="text-4xl font-bold mb-8 bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 bg-clip-text text-transparent drop-shadow-2xl">
            Em Desenvolvimento
          </h2>
          <p className="text-xl text-gray-300 max-w-4xl mx-auto leading-relaxed">
            Esta dashboard está em fase de desenvolvimento ativo. Novas funcionalidades, gráficos interativos,
            relatórios avançados e integrações serão adicionadas em breve para elevar sua experiência!
          </p>
        </div>
      </div>
    </div>
  );
}
