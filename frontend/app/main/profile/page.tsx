// CAMINHO: frontend/app/main/profile/page.tsx

'use client';

import useAuth from '@/hooks/useAuth';
import PageHeader from '@/components/ui/PageHeader';
import BackButton from '@/components/ui/BackButton';
import Card from '@/components/ui/Card';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function ProfilePage() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="flex items-center justify-center py-24">
        <LoadingSpinner size="w-16 h-16" />
      </div>
    );
  }

  const roleDisplay = user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase();

  return (
    <div>
      <PageHeader
        kicker="Conta"
        title="Meu Perfil"
        description="Informações do usuário e preferências da conta."
        actions={<BackButton />}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <Card>
          <h3 className="font-heading font-semibold uppercase mb-2">Email</h3>
          <p className="text-foreground break-all">{user.email}</p>
        </Card>
        <Card>
          <h3 className="font-heading font-semibold uppercase mb-2">Permissão</h3>
          <p className="text-foreground">{roleDisplay}</p>
        </Card>
        <Card>
          <h3 className="font-heading font-semibold uppercase mb-2">Status da Área</h3>
          <p className="text-primary font-semibold">Em Construção</p>
        </Card>
      </div>

      <Card corners className="text-center py-12 max-w-2xl mx-auto">
        <h2 className="font-heading font-semibold text-xl uppercase mb-4">Página em construção</h2>
        <p className="text-muted-foreground leading-relaxed max-w-lg mx-auto">
          As funcionalidades de perfil e preferências serão disponibilizadas em breve. Fique ligado
          nas atualizações!
        </p>
      </Card>
    </div>
  );
}
