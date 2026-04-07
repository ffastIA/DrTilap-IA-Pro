'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/main/hub');
    }
  }, [isAuthenticated, router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden">
      <div
        className="fixed inset-0 -z-10"
        style={{
          backgroundImage: "url('/bg_hero.png')",
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'brightness(0.3) blur(8px)',
        }}
      />

      <div className="z-10 text-center max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-6xl font-bold text-white mb-4">
            🐟 Dr. Tilápia
          </h1>
          <h2 className="text-3xl text-slate-200 font-semibold">
            Consultoria IA para Piscicultura
          </h2>
        </div>

        <p className="text-lg text-slate-300 mb-8 leading-relaxed">
          Sistema inteligente de consultoria técnica baseado em IA, com análise de documentação
          especializada em piscicultura e tilápia. Respostas rápidas, precisas e confiáveis.
        </p>

        <Link
          href="/auth/login"
          className="inline-block px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-white font-bold rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
        >
          Entrar no Sistema →
        </Link>

        <div className="mt-12 pt-8 border-t border-slate-600 border-opacity-30">
          <p className="text-sm text-slate-400">
            Dr. Tilápia utiliza IA para análise de manuais técnicos.
            <br />
            Sempre valide com um técnico especializado antes de implementar recomendações.
          </p>
        </div>
      </div>
    </div>
  );
}