"""Módulo de autenticação do DrTilápia."""

import logging
from typing import Optional, Dict, Any
from app.database import supabase_auth, supabase_admin

logger = logging.getLogger("AuthService")


class AuthService:
    @staticmethod
    async def login(email: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            logger.info("[login] iniciando autenticação para: %s", email)
            auth_response = supabase_auth.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )

            logger.info("[login] auth_response recebido para: %s", email)

            if not auth_response.user:
                logger.warning("[login] auth_response.user vazio para: %s", email)
                logger.warning("Login falhou para: %s", email)
                return None

            user_id = auth_response.user.id
            logger.info("[login] buscando perfil em public.users para user_id: %s", user_id)
            users_response = (
                supabase_admin.table("users")
                .select("id, email, role")
                .eq("id", user_id)
                .execute()
            )

            logger.info("[login] users_response.data length: %s", len(users_response.data) if users_response.data else 0)

            role = "user"
            user_email = auth_response.user.email or email

            if users_response.data and len(users_response.data) > 0:
                logger.info("[login] perfil encontrado em public.users para user_id: %s", user_id)
                role = users_response.data[0].get("role", "user")
                user_email = users_response.data[0].get("email", user_email)
            else:
                logger.warning("[login] perfil não encontrado em public.users para user_id: %s", user_id)

            logger.info("[login] retornando role=%s para email=%s", role, user_email)
            return {
                "access_token": auth_response.session.access_token,
                "token_type": "bearer",
                "user": {
                    "id": user_id,
                    "email": user_email,
                    "role": role,
                },
            }
        except Exception as e:
            logger.exception("[login] exceção inesperada durante login para %s", email)
            logger.error("Erro durante login para %s: %s", email, str(e))
            return None


auth_service = AuthService()