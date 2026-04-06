# Usamos Python 3.11 para estabilidade total com Reflex
FROM python:3.11-slim

WORKDIR /app

# Instala dependências de sistema essenciais
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 1. Copia o arquivo de requisitos
COPY frontend/requirements.txt .

# 2. Instala as dependências bases
RUN pip install --no-cache-dir \
    sqlalchemy==2.0.29 \
    sqlmodel==0.0.16

# 3. Aguarda um segundo para garantir que o pip finalizou
RUN sleep 1

# 4. Agora instala o resto com o ambiente blindado
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia o código do frontend
COPY frontend/ .

# 6. NÃO rodamos reflex init aqui. Ele será executado no container em runtime.
# Isso evita o conflito de metaclasses que ocorre durante o build.

# Portas: 3000 (UI) e 8001 (Eventos do Reflex)
EXPOSE 3000 8001

# Comando de execução: O reflex run já cuida de chamar reflex init se necessário
CMD ["reflex", "run", "--env", "prod", "--backend-port", "8001"]