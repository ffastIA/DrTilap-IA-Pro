import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Any
from fastapi import FastAPI, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Importações internas
from app.auth.auth_service import auth_service
from app.services.rag_service import rag_service

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DrTilapiaAPI")

# 1. Inicialização do App
app = FastAPI(
    title="Dr. Tilápia 2.0 API",
    version="2.0.1"
)

# 2. Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Modelos de Dados
class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    # Usamos List[List[str]] para compatibilidade total com JSON
    history: List[List[str]] = []


# 4. Configurações de Diretório
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    return {"status": "online", "version": app.version}


@app.post("/auth/login")
async def login(data: LoginRequest):
    result = await auth_service.login(data.email, data.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos"
        )
    return result


@app.post("/admin/upload")
async def upload_document(file: UploadFile = File(...)):
    temp_file = UPLOAD_DIR / file.filename
    try:
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        num_chunks = await rag_service.ingest_pdf(str(temp_file), file.filename)

        return {
            "message": f"Arquivo {file.filename} processado com sucesso!",
            "chunks_criados": num_chunks
        }
    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file.exists():
            temp_file.unlink()


@app.post("/consultoria/chat")
async def chat(data: ChatRequest):
    """Endpoint de consulta RAG."""
    try:
        logger.info(f"Nova consulta RAG: {data.message}")

        # Converte o histórico (lista de listas) para lista de tuplas para o LangChain
        formatted_history = [tuple(h) for h in data.history]

        response = await rag_service.get_answer(data.message, formatted_history)
        return response
    except Exception as e:
        logger.error(f"Erro no chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)