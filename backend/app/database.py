import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Configuração de caminhos para evitar problemas com OneDrive/Windows
basedir = Path(__file__).resolve().parent.parent
env_path = basedir / '.env'
load_dotenv(dotenv_path=env_path)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    # Fallback para diretório atual
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

# Objeto global do Supabase utilizado por todo o sistema
supabase: Client = create_client(url, key)