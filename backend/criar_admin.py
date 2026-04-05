import os
import sys

# 1. Localiza a pasta 'backend' de forma absoluta
# Isso evita problemas com o OneDrive e caminhos relativos no Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Injeta o caminho no sys.path para o Python "enxergar" a pasta app
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    # Importação direta (agora o Python sabe que 'app' está na raiz do sys.path)
    from app.database import supabase
    from app.auth.auth_service import get_password_hash


    def main():
        print("\n" + "=" * 50)
        print("   DR. TILÁPIA - CONFIGURAÇÃO DE ACESSO ADMIN")
        print("=" * 50)

        email = input("📧 E-mail do Administrador: ").strip()
        senha = input("🔑 Senha do Administrador: ").strip()

        if not email or not senha:
            print("❌ Erro: Campos obrigatórios vazios.")
            return

        print("\n⏳ Gerando Hash e conectando ao Supabase...")

        try:
            # Gerando o hash usando sua função do auth_service
            senha_hash = get_password_hash(senha)

            # Inserindo na tabela 'users'
            # IMPORTANTE: Verifique se as colunas no Supabase são exatamente estas
            dados = {
                "email": email,
                "hashed_password": senha_hash,
                "role": "admin"
            }

            response = supabase.table("users").insert(dados).execute()

            if response.data:
                print(f"\n✅ SUCESSO! Usuário '{email}' criado.")
                print("🚀 Agora você pode logar no Frontend (Porta 3000).")
            else:
                print("\n❌ Erro: O banco não retornou confirmação.")

        except Exception as e:
            print(f"\n❌ Erro na operação: {e}")


    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"\n❌ ERRO DE IMPORTAÇÃO: {e}")
    print(f"DEBUG: Verifique se existe o arquivo: {os.path.join(BASE_DIR, 'app', 'database.py')}")
    print(f"DEBUG: Verifique se existe o arquivo: {os.path.join(BASE_DIR, 'app', '__init__.py')}")