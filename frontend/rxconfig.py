import reflex as rx

config = rx.Config(
    # Nome do pacote onde reside a lógica da UI (pasta 'ui')
    app_name="ui",

    # URL pública da sua API FastAPI (Motor de IA)
    # O Frontend usará este endereço para chamadas httpx
    api_url="http://localhost:8000",

    # Porta interna que o Reflex usa para gerenciar o estado (Eventos)
    # Definimos 8001 para evitar conflito com o FastAPI na 8000
    backend_port=8001,

    # Banco de dados interno do Reflex (para persistência de estado da UI)
    db_url="sqlite:///reflex.db",

    # Configuração de CORS para permitir conexões do navegador
    cors_allowed_origins=["*"]
)