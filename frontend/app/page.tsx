// CAMINHO: frontend/app/page.tsx

'use client';

import Link from 'next/link';

const HomePage = () => {

  return (

    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* Header */}

      <header className="bg-white shadow-md py-6">

        <div className="container mx-auto px-4 text-center">

          <h1 className="text-4xl font-bold text-blue-600">Dr. Tilápia</h1>

          <p className="text-lg text-gray-600 mt-2">Consultoria Inteligente para Piscicultura</p>

        </div>

      </header>

      {/* Hero Section */}

      <section className="flex-grow flex items-center justify-center py-12">

        <div className="container mx-auto px-4 text-center">

          <h2 className="text-3xl font-semibold text-gray-800 mb-4">Bem-vindo ao Dr. Tilápia</h2>

          <p className="text-xl text-gray-600 mb-8">Soluções avançadas para monitoramento, gestão técnica e consultoria inteligente em piscicultura.</p>

          <div className="space-x-4">

            <Link href="/auth/login" className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition duration-300">

              Entrar no Sistema

            </Link>

            <button

              onClick={() => document.getElementById('beneficios')?.scrollIntoView({ behavior: 'smooth' })}

              className="bg-gray-200 text-gray-800 px-6 py-3 rounded-lg hover:bg-gray-300 transition duration-300"

            >

              Saiba Mais

            </button>

          </div>

        </div>

      </section>

      {/* Benefícios Section */}

      <section id="beneficios" className="py-12 bg-white">

        <div className="container mx-auto px-4">

          <h3 className="text-2xl font-bold text-center text-gray-800 mb-8">Nossos Benefícios</h3>

          <div className="grid md:grid-cols-3 gap-8">

            <div className="text-center">

              <h4 className="text-xl font-semibold text-blue-600 mb-4">Consultoria Técnica com IA</h4>

              <p className="text-gray-600">Receba orientações personalizadas e inteligentes para otimizar suas operações de piscicultura com o apoio de inteligência artificial.</p>

            </div>

            <div className="text-center">

              <h4 className="text-xl font-semibold text-blue-600 mb-4">Base de Conhecimento e Documentos</h4>

              <p className="text-gray-600">Acesse uma vasta biblioteca de documentos e conhecimentos especializados para consultas rápidas e precisas.</p>

            </div>

            <div className="text-center">

              <h4 className="text-xl font-semibold text-blue-600 mb-4">Gestão e Acompanhamento Operacional</h4>

              <p className="text-gray-600">Monitore e gerencie suas atividades diárias com ferramentas integradas para maior eficiência e controle.</p>

            </div>

          </div>

        </div>

      </section>

      {/* Footer */}

      <footer className="bg-gray-800 text-white py-6">

        <div className="container mx-auto px-4 text-center">

          <p>&copy; 2023 Dr. Tilápia. Todos os direitos reservados.</p>

        </div>

      </footer>

    </div>

  );

};

export default HomePage;