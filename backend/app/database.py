# CAMINHO: backend/app/database.py

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client


logger = logging.getLogger(__name__)


# Carrega o arquivo .env do backend
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


# Lê as variáveis de ambiente obrigatórias
SUPABASE_URL = os.getenv('SUPABASE_URL')
if not SUPABASE_URL:
    raise ValueError('SUPABASE_URL é obrigatória. Configure-a no backend/.env')

SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_KEY:
    raise ValueError('SUPABASE_KEY é obrigatória para autenticação comum. Configure-a no backend/.env')

SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        'SUPABASE_SERVICE_ROLE_KEY é obrigatória para upload no Storage e operações administrativas. '
        'Sem ela, o cliente admin falhará silenciosamente em operações privilegiadas. '
        'Configure-a no backend/.env'
    )


# Variáveis expostas para depuração e compatibilidade
supabase_env_path = str(env_path)
supabase_auth_key_type = 'default_key'
supabase_admin_key_type = 'service_role'


# Logs informativos seguros (sem expor segredos)
logger.info(f'Arquivo .env carregado: {supabase_env_path}')
logger.info(f'Tipo de chave para supabase_auth: {supabase_auth_key_type}')
logger.info(f'Tipo de chave para supabase_admin: {supabase_admin_key_type}')


# Cria os clientes Supabase
supabase_auth: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Alias legado para compatibilidade com código existente
supabase: Client = supabase_admin
