# CAMINHO: backend/app/auth/auth_service.py
"""Módulo de autenticação do DrTilápia."""

import logging
from typing import Optional, Dict, Any
from app.database import supabase_auth, supabase_admin

logger = logging.getLogger("AuthService")


class AuthService:
    @staticmethod
    async def login(email: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            auth_response = supabase_auth.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )

            if not auth_response.user:
                logger.warning("Login falhou para: %s", email)
                return None

            user_id = auth_response.user.id
            users_response = (
                supabase_admin.table("users")
                .select("id, email, role")
                .eq("id", user_id)
                .execute()
            )

            role = "user"
            user_email = auth_response.user.email or email

            if users_response.data and len(users_response.data) > 0:
                role = users_response.data[0].get("role", "user")
                user_email = users_response.data[0].get("email", user_email)

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
            logger.error("Erro durante login para %s: %s", email, str(e))
            return None


auth_service = AuthService()