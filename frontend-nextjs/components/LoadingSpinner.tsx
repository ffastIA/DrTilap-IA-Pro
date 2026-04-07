// components/LoadingSpinner.tsx
import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large'; // Tamanho do spinner<br/>
  color?: string; // Cor do spinner (Tailwind class, e.g., 'text-primary')<br/>
  className?: string; // Classes CSS adicionais
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'medium', color = 'text-primary', className }) => {
  let spinnerSize = 'w-8 h-8'; // Tamanho padrão
  if (size === 'small') spinnerSize = 'w-5 h-5';
  if (size === 'large') spinnerSize = 'w-12 h-12';

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div
        className={`animate-spin rounded-full border-4 border-t-4 border-gray-200 ${color} ${spinnerSize}`}
        style={{ borderTopColor: 'var(--color-primary)' }} // Garante que a cor primária seja usada para a parte animada
      ></div>
    </div>
  );
};

export default LoadingSpinner;