'use client';
// CAMINHO: frontend/app/page.tsx

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import LoadingSpinner from '@/components/LoadingSpinner';

const HomePage = () => {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.replace('/main/hub');
    } else {
      router.replace('/auth/login');
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <LoadingSpinner size="w-12 h-12" color="text-primary" />
        <p>Carregando Dr. Tilápia...</p>
      </div>
    </div>
  );
};

export default HomePage;
