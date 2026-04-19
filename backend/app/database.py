# CAMINHO: backend/app/database.py
"""Módulo de configuração dos clientes Supabase do backend."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL não encontrada no arquivo .env do backend.")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY não encontrada no arquivo .env do backend.")

auth_key = SUPABASE_KEY
admin_key = (
    SUPABASE_SERVICE_ROLE_KEY
    if SUPABASE_SERVICE_ROLE_KEY and SUPABASE_SERVICE_ROLE_KEY.strip()
    else SUPABASE_KEY
)

supabase_auth_key_type = "default_key"
supabase_admin_key_type = (
    "service_role"
    if SUPABASE_SERVICE_ROLE_KEY and SUPABASE_SERVICE_ROLE_KEY.strip()
    else "default_key"
)

supabase_auth: Client = create_client(SUPABASE_URL, auth_key)
supabase_admin: Client = create_client(SUPABASE_URL, admin_key)

# Compatibilidade retroativa com código legado
supabase: Client = supabase_admin

supabase_env_path = str(env_path)

logger.info("Arquivo .env carregado de: %s", supabase_env_path)
logger.info("Tipo da chave auth: %s", supabase_auth_key_type)
logger.info("Tipo da chave admin: %s", supabase_admin_key_type)