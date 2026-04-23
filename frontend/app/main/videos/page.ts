'use client';

import { useRouter } from 'next/navigation';
import useAuth from '@/hooks/useAuth';

export default function VideosPage() {
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
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={handleBack}
            className="p-3 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-full border border-white/20 transition-all duration-300 flex items-center gap-2 text-lg font-medium group hover:scale-105 shadow-lg"
          >
            <span className="text-xl">←</span>
            Voltar
          </button>
          <h1 className="text-4xl md:text-5xl font-bold text-center flex-1 mx-4 drop-shadow-lg">
            Vídeos
          </h1>
          <div className="w-12" />
        </div>

        <p className="text-xl md:text-2xl mb-12 text-center max-w-2xl mx-auto leading-relaxed drop-shadow-md">
          Acompanhe em breve a biblioteca de vídeos do DrTilápia com conteúdos técnicos, tutoriais e materiais de apoio para piscicultura.
        </p>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 mb-16">
          <div className="bg-white/10 backdrop-blur-lg p-8 rounded-2xl border border-white/20 shadow-2xl hover:shadow-3xl transition-all duration-300 hover:-translate-y-2">
            <h3 className="text-2xl font-bold mb-4 flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-500/30 rounded-xl flex items-center justify-center backdrop-blur-sm border border-blue-400/30">
                👤
              </div>
              Usuário Logado
            </h3>
            <p className="text-lg opacity-90 font-medium">
              {user?.email || 'Nenhum usuário logado'}
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-lg p-8 rounded-2xl border border-white/20 shadow-2xl hover:shadow-3xl transition-all duration-300 hover:-translate-y-2">
            <h3 className="text-2xl font-bold mb-4 flex items-center gap-3">
              <div className="w-12 h-12 bg-yellow-500/30 rounded-xl flex items-center justify-center backdrop-blur-sm border border-yellow-400/30">
                ⚙️
              </div>
              Status
            </h3>
            <p className="text-lg opacity-90 font-medium text-yellow-300">
              Em preparação
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-lg p-8 rounded-2xl border border-white/20 shadow-2xl hover:shadow-3xl transition-all duration-300 hover:-translate-y-2">
            <h3 className="text-2xl font-bold mb-4 flex items-center gap-3">
              <div className="w-12 h-12 bg-green-500/30 rounded-xl flex items-center justify-center backdrop-blur-sm border border-green-400/30">
                🔐
              </div>
              Permissão
            </h3>
            <p className="text-lg opacity-90 font-medium">
              {user?.role || 'N/A'}
            </p>
          </div>
        </div>

        {/* Bloco Em Desenvolvimento */}
        <div className="bg-white/5 backdrop-blur-xl p-12 rounded-3xl border border-white/10 shadow-2xl text-center max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold mb-8 bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent drop-shadow-lg">
            Em Desenvolvimento
          </h2>
          <p className="text-lg md:text-xl leading-relaxed opacity-90 max-w-3xl mx-auto">
            Esta biblioteca de vídeos está em fase de desenvolvimento ativo. Em breve, novos recursos como catálogo organizado, filtros por categoria, reprodução integrada e conteúdos técnicos exclusivos serão adicionados para ampliar sua experiência na plataforma.
          </p>
        </div>
      </div>
    </div>
  );
}
