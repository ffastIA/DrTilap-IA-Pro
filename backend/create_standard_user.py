import bcrypt
from app.database import supabase


def create_user(email, password, name, role):
    # Gerando Hash seguro com Bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    data = {
        "email": email,
        "hashed_password": hashed,
        "full_name": name,
        "role": role  # 'admin' ou 'user'
    }

    try:
        # Insere na tabela public.users
        res = supabase.table("users").insert(data).execute()
        print(f"✅ Usuário {email} criado com sucesso como '{role}'!")
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")


if __name__ == "__main__":
    # Criando o usuário padrão solicitado
    create_user("usuario@gmail.com", "123456", "Usuário Comum", "user")