// CAMINHO: frontend/app/auth/forgot-password/page.tsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForgotPasswordMutation } from '@/hooks/useForgotPasswordMutation';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const forgotPasswordMutation = useForgotPasswordMutation();

  const validateForm = (): boolean => {
    if (!email.trim()) {
      setValidationError('O email é obrigatório.');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setValidationError('Por favor, insira um email válido.');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    setValidationError('');
    setSuccessMessage('');

    forgotPasswordMutation.mutate(
      { email: email.trim() },
      {
        onSuccess: (data) => {
          setSuccessMessage(data.message);
        },
        onError: (error) => {
          setValidationError(error.message);
        },
        onSettled: () => {
          setIsSubmitting(false);
        },
      }
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-2xl shadow-xl border border-gray-200">
        <div>
          <div className="mx-auto h-16 w-16 bg-gradient-to-r from-green-400 to-blue-500 rounded-2xl flex items-center justify-center mb-6">
            <span className="text-2xl font-bold text-white">DT</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Esqueci Minha Senha
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Informe seu email para receber um link de redefinição
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="appearance-none rounded-xl relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition duration-200"
              placeholder="Digite seu email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          {validationError && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm">
              {validationError}
            </div>
          )}

          {successMessage && (
            <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-xl text-sm">
              {successMessage}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
            >
              {isSubmitting ? 'Enviando...' : 'Enviar link de redefinição'}
            </button>
          </div>
        </form>

        <div className="mt-8">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Lembrou sua senha?</span>
            </div>
          </div>
          <div className="mt-6">
            <Link
              href="/auth/login"
              className="font-medium text-blue-600 hover:text-blue-500 text-sm flex items-center justify-center gap-1"
            >
              Entrar
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
