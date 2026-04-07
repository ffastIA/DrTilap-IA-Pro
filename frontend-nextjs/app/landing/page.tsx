'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useEffect } from 'react';
import { FishIcon, BrainIcon, BarChart3Icon, ShieldIcon, ArrowRightIcon, SparklesIcon } from 'lucide-react';
import Button from '@/components/Button';

const FeatureItem: React.FC<{
  icon: React.ElementType;
  title: string;
  description: string;
}> = ({ icon: Icon, title, description }) => (
  <div className="glass-effect p-8 rounded-xl text-center hover:scale-105 transition-transform duration-300">
    <Icon size={48} className="text-primary mx-auto mb-4" />
    <h3 className="text-xl font-bold text-white mb-3">{title}</h3>
    <p className="text-text-secondary text-sm leading-relaxed">{description}</p>
  </div>
);

export default function LandingPage() {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    // Se já está autenticado, vai direto para o hub
    if (isAuthenticated) {
      router.replace('/main/hub');
    }
  }, [isAuthenticated, router]);

  const handleEnter = () => {
    router.push('/auth/login');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-surface">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b border-gray-700/30">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <FishIcon size={32} className="text-primary" />
            <h1 className="text-2xl font-bold text-white">Dr. Tilápia</h1>
          </div>
          <Button onClick={handleEnter}>
            Entrar no Sistema
          </Button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-block mb-6">
            <div className="glass-effect px-6 py-2 rounded-full border border-primary/20">
              <p className="text-primary text-sm font-medium">🚀 Inteligência Artificial para Piscicultura</p>
            </div>
          </div>

          <h2 className="text-6xl font-bold text-white mb-6 leading-tight max-w-4xl mx-auto">
            Consultoria de IA para <span className="text-primary">Piscicultura</span> Inteligente
          </h2>

          <p className="text-xl text-text-secondary mb-12 max-w-2xl mx-auto leading-relaxed">
            Dr. Tilápia 2.0 combina inteligência artificial avançada com expertise em aquacultura para otimizar sua produção e maximizar resultados.
          </p>

          <div className="flex gap-6 justify-center mb-20">
            <Button onClick={handleEnter} className="px-10 py-4 text-lg">
              Começar Agora
              <ArrowRightIcon size={20} />
            </Button>
            <Button variant="secondary" className="px-10 py-4 text-lg">
              Saiba Mais
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-20">
            <div className="glass-effect p-8 rounded-xl">
              <p className="text-4xl font-bold text-primary mb-2">1250+</p>
              <p className="text-text-secondary">Consultas Realizadas</p>
            </div>
            <div className="glass-effect p-8 rounded-xl">
              <p className="text-4xl font-bold text-primary mb-2">45</p>
              <p className="text-text-secondary">Documentos na Base</p>
            </div>
            <div className="glass-effect p-8 rounded-xl">
              <p className="text-4xl font-bold text-primary mb-2">98%</p>
              <p className="text-text-secondary">Satisfação dos Usuários</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6 bg-gradient-to-b from-transparent to-surface/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h3 className="text-4xl font-bold text-white mb-4">Funcionalidades Principais</h3>
            <p className="text-text-secondary text-lg">Tudo que você precisa para gerenciar sua piscicultura com IA</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <FeatureItem
              icon={BrainIcon}
              title="Consultoria de IA"
              description="Respostas instantâneas e insights especializados sobre piscicultura baseados em manuais técnicos."
            />
            <FeatureItem
              icon={BarChart3Icon}
              title="Dashboard Analytics"
              description="Visualize métricas e KPIs em tempo real para otimizar sua produção."
            />
            <FeatureItem
              icon={ShieldIcon}
              title="Segurança"
              description="Autenticação segura e proteção de dados com encriptação de nível empresarial."
            />
            <FeatureItem
              icon={SparklesIcon}
              title="Base de Conhecimento"
              description="Banco de dados RAG constantemente atualizado com documentação técnica."
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h3 className="text-4xl font-bold text-white mb-16 text-center">Como Funciona</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {/* Step 1 */}
            <div className="relative">
              <div className="glass-effect p-8 rounded-xl text-center h-full flex flex-col justify-center">
                <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mx-auto mb-6">
                  <span className="text-2xl font-bold text-primary">1</span>
                </div>
                <h4 className="text-xl font-bold text-white mb-3">Faça Login</h4>
                <p className="text-text-secondary">Acesse sua conta com credenciais seguras.</p>
              </div>
              <div className="hidden md:block absolute top-1/2 -right-6 transform -translate-y-1/2 text-primary text-4xl">
                →
              </div>
            </div>

            {/* Step 2 */}
            <div className="relative">
              <div className="glass-effect p-8 rounded-xl text-center h-full flex flex-col justify-center">
                <div className="w-16 h-16 bg-secondary/20 rounded-full flex items-center justify-center mx-auto mb-6">
                  <span className="text-2xl font-bold text-secondary">2</span>
                </div>
                <h4 className="text-xl font-bold text-white mb-3">Faça Perguntas</h4>
                <p className="text-text-secondary">Consulte o Dr. Tilápia sobre qualquer aspecto da piscicultura.</p>
              </div>
              <div className="hidden md:block absolute top-1/2 -right-6 transform -translate-y-1/2 text-secondary text-4xl">
                →
              </div>
            </div>

            {/* Step 3 */}
            <div>
              <div className="glass-effect p-8 rounded-xl text-center h-full flex flex-col justify-center">
                <div className="w-16 h-16 bg-accent/20 rounded-full flex items-center justify-center mx-auto mb-6">
                  <span className="text-2xl font-bold text-accent">3</span>
                </div>
                <h4 className="text-xl font-bold text-white mb-3">Otimize</h4>
                <p className="text-text-secondary">Aplique as recomendações para melhorar sua produção.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6 bg-gradient-to-b from-surface/50 to-surface">
        <div className="max-w-4xl mx-auto glass-effect p-16 rounded-2xl text-center border border-primary/20">
          <h3 className="text-4xl font-bold text-white mb-6">Pronto para Transformar sua Piscicultura?</h3>
          <p className="text-xl text-text-secondary mb-10">
            Junte-se a centenas de aquacultores que já usam Dr. Tilápia para aumentar produtividade e reduzir custos.
          </p>
          <Button onClick={handleEnter} className="px-12 py-4 text-lg">
            Começar Agora
            <ArrowRightIcon size={20} />
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-gray-700/30">
        <div className="max-w-7xl mx-auto text-center text-text-secondary">
          <p>&copy; 2026 Dr. Tilápia. Inteligência Artificial para Piscicultura. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
}