import os
import logging
import re
from supabase import create_client, Client
from app.services.user_service import UserService
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdminCLI:
    """
    Interface de linha de comando para gerenciar usuários do Supabase Auth.
    Utiliza o UserService para operações administrativas.
    """

    def __init__(self):
        try:
            self.user_service = UserService()
            logger.info("AdminCLI inicializado com UserService.")
        except ValueError as e:
            logger.critical(f"Erro de inicialização do UserService: {e}")
            print(f"\n❌ ERRO CRÍTICO: {e}")
            print(
                "   Certifique-se de que SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY estão definidos no seu arquivo .env.")
            exit(1)

    def _validate_email(self, email: str) -> bool:
        """Valida o formato do email."""
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            print("❌ Formato de email inválido.")
            return False
        return True

    def _validate_password_strength(self, password: str) -> bool:
        """Valida a força da senha (mínimo 8 caracteres, maiúscula, minúscula, número, caractere especial)."""
        if len(password) < 8:
            print("❌ A senha deve ter no mínimo 8 caracteres.")
            return False
        if not re.search(r"[A-Z]", password):
            print("❌ A senha deve conter pelo menos uma letra maiúscula.")
            return False
        if not re.search(r"[a-z]", password):
            print("❌ A senha deve conter pelo menos uma letra minúscula.")
            return False
        if not re.search(r"\d", password):
            print("❌ A senha deve conter pelo menos um número.")
            return False
        if not re.search(r"[!@#$%^&*(),.?\"{}\|<>]", password):
            print("❌ A senha deve conter pelo menos um caractere especial.")
            return False
        return True

    def _get_user_input(self, prompt: str, sensitive: bool = False) -> str:
        """Obtém entrada do usuário, com opção para entrada sensível (senha)."""
        if sensitive:
            return input(prompt)
        return input(prompt)

    def display_menu(self):
        """Exibe o menu de opções para o usuário."""
        print("\n--- Gerenciamento de Usuários Supabase ---")
        print("1. Criar Novo Usuário")
        print("2. Listar Usuários Existentes")
        print("3. Deletar Usuário")
        print("4. Sair")
        print("")

    def handle_create_user(self):
        """Processa a criação de um novo usuário."""
        print("\n--- Criar Novo Usuário ---")
        while True:
            email = self._get_user_input("Email do novo usuário: ").strip()
            if self._validate_email(email):
                break

        existing_user = self.user_service.get_user_by_email(email)
        if existing_user:
            print(f"⚠️ Usuário com email '{email}' já existe. ID: {existing_user.get('id')}")
            return

        while True:
            password = self._get_user_input("Senha do novo usuário: ", sensitive=True).strip()
            if self._validate_password_strength(password):
                break

        name = self._get_user_input("Nome completo do usuário: ").strip()

        roles = ["admin", "user", "guest"]
        while True:
            role = self._get_user_input(f"Role do usuário ({', '.join(roles)}): ").strip().lower()
            if role in roles:
                break
            print(f"❌ Role inválida. Escolha entre: {', '.join(roles)}")

        try:
            new_user = self.user_service.create_user(email, password, name, role=role)
            print(f"\n🎉 Usuário '{email}' criado com sucesso!")
            print(f"   ID: {new_user.get('id')}")
            print(f"   Nome: {new_user.get('user_metadata', {}).get('name')}")
            print(f"   Email: {new_user.get('email')}")
            print(f"   Role: {new_user.get('user_metadata', {}).get('role')}")
        except Exception as e:
            logger.error(f"Erro ao criar usuário '{email}': {e}", exc_info=True)
            print(f"\n❌ ERRO ao criar usuário: {e}")

    def handle_list_users(self):
        """Processa a listagem de usuários existentes."""
        print("\n--- Listar Usuários ---")
        try:
            users = self.user_service.list_users()
            if not users:
                print("Nenhum usuário encontrado.")
                return

            print(f"Total de usuários: {len(users)}")
            for user in users:
                user_id = user.get('id', 'N/A')
                email = user.get('email', 'N/A')
                name = user.get('user_metadata', {}).get('name', 'N/A')
                role = user.get('user_metadata', {}).get('role', 'N/A')
                created_at = user.get('created_at', 'N/A')
                print(f"")
                print(f"ID: {user_id}")
                print(f"Email: {email}")
                print(f"Nome: {name}")
                print(f"Role: {role}")
                print(f"Criado em: {created_at}")
            print(f"")
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}", exc_info=True)
            print(f"\n❌ ERRO ao listar usuários: {e}")

    def handle_delete_user(self):
        """Processa a exclusão de um usuário."""
        print("\n--- Deletar Usuário ---")
        user_id = self._get_user_input("ID do usuário a ser deletado: ").strip()
        if not user_id:
            print("❌ ID do usuário não pode ser vazio.")
            return

        try:
            user_to_delete = self.user_service.get_user_by_id(user_id)
            if not user_to_delete:
                print(f"⚠️ Usuário com ID '{user_id}' não encontrado.")
                return

            confirm = self._get_user_input(
                f"Tem certeza que deseja deletar o usuário '{user_to_delete.get('email')}' (s/N)? ").strip().lower()
            if confirm == 's':
                self.user_service.delete_user(user_id)
                print(f"\n✅ Usuário '{user_id}' deletado com sucesso.")
            else:
                print("Operação de exclusão cancelada.")
        except Exception as e:
            logger.error(f"Erro ao deletar usuário '{user_id}': {e}", exc_info=True)
            print(f"\n❌ ERRO ao deletar usuário: {e}")

    def run(self):
        """Executa o loop principal da interface de linha de comando."""
        while True:
            self.display_menu()
            choice = self._get_user_input("Escolha uma opção: ").strip()

            if choice == '1':
                self.handle_create_user()
            elif choice == '2':
                self.handle_list_users()
            elif choice == '3':
                self.handle_delete_user()
            elif choice == '4':
                print("Saindo do gerenciador de usuários. Até mais!")
                break
            else:
                print("Opção inválida. Por favor, tente novamente.")


if __name__ == "__main__":
    cli = AdminCLI()
    cli.run()