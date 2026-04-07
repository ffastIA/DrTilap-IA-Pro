// components/GlassContainer.tsx
import React from 'react';

interface GlassContainerProps {
  children: React.ReactNode; // Conteúdo a ser renderizado dentro do contêiner<br/>
  className?: string; // Classes CSS adicionais para personalização
}

const GlassContainer: React.FC<GlassContainerProps> = ({ children, className }) => {
  return (
    // Aplica o efeito glassmorphism e classes Tailwind para padding e arredondamento
    // As classes adicionais são mescladas com as classes padrão
    <div className={`glass-effect p-6 rounded-xl ${className || ''}`}>
      {children} {/* Renderiza o conteúdo passado como children */}
    </div>
  );
};

export default GlassContainer;