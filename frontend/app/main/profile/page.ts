// CAMINHO: frontend/app/main/profile/page.ts

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import useAuth from '@/hooks/useAuth';

const ProfilePage = () => {
  const router = useRouter();
  const { user } = useAuth();

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/main/hub');
    }
  };

  if (!user) {
    return React.createElement(
      'div',
      {
        className:
          'min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8'
      },
      React.createElement('div', {
        className:
          'animate-spin rounded-full h-16 w-16 border-b-4 border-white border-t-transparent'
      })
    );
  }

  const roleDisplay =
    user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase();

  const glassCardClass =
    'backdrop-blur-md bg-black/30 border border-white/20 shadow-2xl rounded-2xl p-8 hover:shadow-3xl transition-all duration-300 hover:-translate-y-2';

  const headerClass =
    'backdrop-blur-md bg-black/20 border-b border-white/10 px-6 py-4 flex items-center gap-4 sticky top-0 z-10';

  const contentClass =
    'flex-1 container mx-auto px-6 py-12 lg:px-12 lg:py-20 space-y-16 max-w-7xl';

  const subtitleClass =
    'text-xl md:text-2xl text-gray-200/80 text-center max-w-2xl mx-auto leading-relaxed';

  const gridClass = 'grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 max-w-4xl mx-auto';

  const centralClass =
    'backdrop-blur-xl bg-gradient-to-b from-black/40 to-black/60 border border-white/30 shadow-3xl rounded-3xl p-12 lg:p-16 text-center max-w-2xl mx-auto';

  return React.createElement(
    'div',
    {
      className:
        'min-h-screen bg-gradient-to-br from-slate-900 via-slate-800/50 to-slate-900 flex flex-col'
    },
    // Header
    React.createElement(
      'header',
      { className: headerClass },
      React.createElement(
        'button',
        {
          onClick: handleBack,
          className:
            'text-2xl font-bold text-white hover:text-purple-300 transition-colors p-2 rounded-lg hover:bg-white/10 flex items-center gap-1'
        },
        '← Voltar'
      ),
      React.createElement(
        'h1',
        {
          className:
            'text-3xl md:text-4xl font-bold bg-gradient-to-r from-white via-purple-100 to-purple-200 bg-clip-text text-transparent drop-shadow-lg'
        },
        'Meu Perfil'
      )
    ),
    // Main content
    React.createElement(
      'main',
      { className: contentClass },
      // Subtitle
      React.createElement(
        'p',
        { className: subtitleClass },
        'Informações do usuário e preferências da conta.'
      ),
      // Cards grid
      React.createElement(
        'div',
        { className: gridClass },
        // Email card
        React.createElement(
          'div',
          { className: glassCardClass },
          React.createElement(
            'h3',
            { className: 'text-xl font-bold text-white mb-4' },
            'Email'
          ),
          React.createElement(
            'p',
            { className: 'text-gray-300 text-lg break-all font-medium' },
            user.email
          )
        ),
        // Role card
        React.createElement(
          'div',
          { className: glassCardClass },
          React.createElement(
            'h3',
            { className: 'text-xl font-bold text-white mb-4' },
            'Permissão'
          ),
          React.createElement(
            'p',
            { className: 'text-gray-300 text-lg font-medium' },
            roleDisplay
          )
        ),
        // Status card
        React.createElement(
          'div',
          { className: glassCardClass },
          React.createElement(
            'h3',
            { className: 'text-xl font-bold text-white mb-4' },
            'Status da Área'
          ),
          React.createElement(
            'p',
            { className: 'text-yellow-400 text-lg font-semibold' },
            'Em Construção'
          )
        )
      ),
      // Central construction message
      React.createElement(
        'section',
        { className: centralClass },
        React.createElement(
          'h2',
          {
            className:
              'text-3xl lg:text-4xl font-bold text-white mb-6 bg-gradient-to-r from-yellow-400 via-orange-400 to-yellow-500 bg-clip-text text-transparent drop-shadow-lg'
          },
          'Página em construção'
        ),
        React.createElement(
          'p',
          {
            className:
              'text-lg lg:text-xl text-gray-300 leading-relaxed max-w-lg mx-auto'
          },
          'As funcionalidades de perfil e preferências serão disponibilizadas em breve. Fique ligado nas atualizações!'
        )
      )
    )
  );
};

export default ProfilePage;
