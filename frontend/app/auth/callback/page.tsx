// CAMINHO: frontend/app/auth/callback/page.tsx
//
// Landing única para os dois links que o Supabase envia por email:
//  - confirmação de cadastro: #access_token=...&type=signup
//  - redefinição de senha:    #access_token=...&refresh_token=...&type=recovery
//
// O Supabase já confirma/autentica no servidor antes de redirecionar aqui —
// esta página só lê o fragmento da URL (nunca chega ao servidor) e decide
// o que mostrar. Tokens de recovery ficam em estado local do componente,
// nunca em authStore/cookies (não é uma sessão logada real).

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useResetPasswordMutation } from '@/hooks/useResetPasswordMutation';

type CallbackState = 'loading' | 'confirmed' | 'recovery' | 'invalid';

export default function AuthCallbackPage() {
  const [state, setState] = useState<CallbackState>('loading');
  const [accessToken, setAccessToken] = useState('');
  const [refreshToken, setRefreshToken] = useState('');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const resetPasswordMutation = useResetPasswordMutation();

  useEffect(() => {
    const hash = window.location.hash.startsWith('#')
      ? window.location.hash.slice(1)
      : window.location.hash;
    const params = new URLSearchParams(hash);
    const type = params.get('type');
    const token = params.get('access_token');
    const refresh = params.get('refresh_token');

    if (type === 'signup' || type === 'email_change') {
      setState('confirmed');
    } else if (type === 'recovery' && token && refresh) {
      setAccessToken(token);
      setRefreshToken(refresh);
      setState('recovery');
    } else {
      setState('invalid');
    }
  }, []);

  const validateForm = (): boolean => {
    if (!newPassword || newPassword.length < 6) {
      setValidationError('A senha deve ter pelo menos 6 caracteres.');
      return false;
    }
    if (newPassword !== confirmPassword) {
      setValidationError('As senhas não coincidem.');
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

    resetPasswordMutation.mutate(
      { access_token: accessToken, refresh_token: refreshToken, new_password: newPassword },
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

          {state === 'loading' && (
            <p className="mt-2 text-center text-sm text-gray-600">Verificando link...</p>
          )}

          {state === 'confirmed' && (
            <>
              <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
                Email Confirmado!
              </h2>
              <p className="mt-2 text-center text-sm text-gray-600">
                Sua conta foi confirmada com sucesso. Já pode entrar no sistema.
              </p>
            </>
          )}

          {state === 'invalid' && (
            <>
              <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
                Link Inválido
              </h2>
              <p className="mt-2 text-center text-sm text-gray-600">
                Este link é inválido ou já expirou.
              </p>
            </>
          )}

          {state === 'recovery' && !successMessage && (
            <>
              <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
                Redefinir Senha
              </h2>
              <p className="mt-2 text-center text-sm text-gray-600">
                Digite sua nova senha
              </p>
            </>
          )}
        </div>

        {state === 'recovery' && !successMessage && (
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-2">
                  Nova senha
                </label>
                <input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  required
                  className="appearance-none rounded-xl relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition duration-200"
                  placeholder="Pelo menos 6 caracteres"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                  Confirmar nova senha
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  className="appearance-none rounded-xl relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition duration-200"
                  placeholder="Digite a senha novamente"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {validationError && (
              <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl text-sm">
                {validationError}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
              >
                {isSubmitting ? 'Redefinindo...' : 'Redefinir Senha'}
              </button>
            </div>
          </form>
        )}

        {successMessage && (
          <div className="mt-6 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-xl text-sm">
            {successMessage}
          </div>
        )}

        {(state === 'confirmed' || state === 'invalid' || successMessage) && (
          <div className="mt-8">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
            </div>
            <div className="mt-6 flex flex-col items-center gap-2">
              <Link href="/auth/login" className="font-medium text-blue-600 hover:text-blue-500 text-sm">
                Ir para o login
              </Link>
              {state === 'invalid' && (
                <>
                  <Link href="/auth/signup" className="font-medium text-blue-600 hover:text-blue-500 text-sm">
                    Criar uma conta
                  </Link>
                  <Link href="/auth/forgot-password" className="font-medium text-blue-600 hover:text-blue-500 text-sm">
                    Pedir novo link de redefinição
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
