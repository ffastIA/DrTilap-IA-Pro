// app/page.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    // Se não está carregando e o estado de autenticação foi verificado
    if (!isLoading) {
      if (isAuthenticated) {
        // Se está autenticado, vai para o hub
        router.replace('/main/hub');
      } else {
        // Se não está autenticado, vai para a landing page
        router.replace('/landing');
      }
    }
  }, [isAuthenticated, isLoading, router]);

  // Exibe spinner enquanto verifica autenticação
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <LoadingSpinner size="w-12 h-12" color="text-primary" />
        <p className="text-text-secondary mt-4">Carregando Dr. Tilápia...</p>
      </div>
    </div>
  );
}