from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from app.database import supabase

SECRET_KEY = os.environ.get("JWT_SECRET")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")


class AuthService:
    @staticmethod
    async def login(email: str, password: str):
        try:
            # Autenticação nativa do Supabase
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user:
                return {
                    "access_token": response.session.access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "role": response.user.user_metadata.get("role", "user")
                    }
                }
        except Exception as e:
            return None


auth_service = AuthService()