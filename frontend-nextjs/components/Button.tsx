// components/Button.tsx
import React from 'react';
import LoadingSpinner from './LoadingSpinner'; // Importa o spinner de carregamento

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'glass'; // Variações de estilo do botão<br/>
  isLoading?: boolean; // Indica se o botão está em estado de carregamento<br/>
  children: React.ReactNode; // Conteúdo do botão
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  isLoading = false,
  children,
  className,
  disabled,
  ...props
}) => {
  const baseClasses = 'font-semibold py-2 px-4 rounded-lg transition-all duration-300 ease-in-out flex items-center justify-center';
  let variantClasses = '';

  switch (variant) {
    case 'primary':<br/>
      variantClasses = 'bg-primary text-white hover:bg-accent';
      break;
    case 'secondary':<br/>
      variantClasses = 'bg-secondary text-white hover:bg-primary';
      break;
    case 'glass':<br/>
      variantClasses = 'glass-effect text-white hover:bg-glass-light'; // Estilo glassmorphism para botões
      break;
    default:<br/>
      variantClasses = 'bg-primary text-white hover:bg-accent';
  }

  // Desabilita o botão se estiver carregando ou explicitamente desabilitado
  const isDisabled = isLoading || disabled;

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${className || ''} ${
        isDisabled ? 'opacity-50 cursor-not-allowed' : ''
      }`}
      disabled={isDisabled}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner size="small" color="text-white" /> // Exibe spinner se estiver carregando
      ) : (
        children // Exibe o conteúdo normal
      )}
    </button>
  );
};

export default Button;