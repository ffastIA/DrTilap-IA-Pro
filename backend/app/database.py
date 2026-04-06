import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Carrega o .env da raiz do backend
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL ou SUPABASE_KEY não encontradas no .env")

# Cliente global do Supabase
supabase: Client = create_client(url, key)