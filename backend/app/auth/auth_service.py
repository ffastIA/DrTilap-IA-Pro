import logging
from typing import Optional, Dict, Any
from app.database import supabase

logger = logging.getLogger("AuthService")


class AuthService:
    @staticmethod
    async def login(email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Login: Autentica via Supabase Auth + busca dados em users table
        """
        try:
            # 1. Autenticação via Supabase Auth
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                logger.warning(f"Login falhou para: {email}")
                return None

            user_id = auth_response.user.id

            # 2. Buscar role na tabela users (SEM o prefixo "public.")
            # O Supabase já assume o schema padrão
            users_response = supabase.table("users").select(
                "id, email, role"
            ).eq("id", user_id).execute()

            logger.info(f"Query executada: users_response = {users_response.data}")

            role = "user"  # Default
            if users_response.data and len(users_response.data) > 0:
                role = users_response.data[0].get("role", "user")
                logger.info(f"✅ Role encontrado: {role}")
            else:
                logger.warning(f"⚠️ Nenhum registro encontrado para user_id: {user_id}")

            logger.info(f"✅ Login bem-sucedido: {email} | role: {role}")

            # 3. Retornar dados de autenticação
            return {
                "access_token": auth_response.session.access_token,
                "token_type": "bearer",
                "user": {
                    "id": user_id,
                    "email": auth_response.user.email,
                    "role": role
                }
            }

        except Exception as e:
            logger.error(f"❌ Erro no login: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None


auth_service = AuthService()