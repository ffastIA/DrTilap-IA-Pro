'use client';

import React from 'react';
import Link from 'next/link';
import { MessageSquareTextIcon, UploadCloudIcon, BarChart2Icon, UserIcon } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

const FeatureCard: React.FC<{
  icon: React.ElementType;
  title: string;
  description: string;
  href: string;
  disabled?: boolean;
}> = ({ icon: Icon, title, description, href, disabled }) => (
  <Link href={href} className={`block ${disabled ? 'pointer-events-none opacity-50' : ''}`}>
    <div className="glass-effect p-6 rounded-lg flex flex-col items-center text-center h-full transition-all duration-300 hover:scale-105 hover:shadow-xl">
      <Icon size={48} className="text-primary mb-4" />
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-text-secondary text-sm">{description}</p>
    </div>
  </Link>
);

export default function HubPage() {
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-white mb-4">Bem-vindo, {user?.email}!</h1>
      <p className="text-text-secondary text-lg mb-8">
        Explore as funcionalidades do Dr. Tilápia, seu assistente de IA para piscicultura.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FeatureCard
          icon={MessageSquareTextIcon}
          title="Consultoria de IA"
          description="Obtenha respostas instantâneas e insights especializados sobre piscicultura."
          href="/main/consultoria"
        />
        <FeatureCard
          icon={BarChart2Icon}
          title="Dashboard de Métricas"
          description="Visualize dados e métricas importantes para otimizar sua produção."
          href="/main/dashboard"
        />
        {isAdmin ? (
          <FeatureCard
            icon={UploadCloudIcon}
            title="Administração RAG"
            description="Gerencie e faça upload de documentos para a base de conhecimento da IA."
            href="/main/admin"
          />
        ) : (
          <FeatureCard
            icon={UploadCloudIcon}
            title="Administração RAG"
            description="Funcionalidade exclusiva para administradores."
            href="#"
            disabled
          />
        )}
        <FeatureCard
          icon={UserIcon}
          title="Meu Perfil"
          description="Visualize e edite suas informações de usuário e preferências."
          href="/main/profile"
        />
      </div>

      <div className="mt-12">
        <h2 className="text-3xl font-bold text-white mb-6">Atividades Recentes</h2>
        <div className="glass-effect p-6 rounded-lg">
          <p className="text-text-secondary">Nenhuma atividade recente para exibir.</p>
        </div>
      </div>
    </div>
  );
}