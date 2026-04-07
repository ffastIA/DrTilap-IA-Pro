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

# ============ CONFIGURAÇÃO DE LOGGING ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DrTilapiaAPI")

# ============ INICIALIZAÇÃO DO APP ============
app = FastAPI(
    title="Dr. Tilápia 2.0 API",
    version="2.0.1"
)

# ============ CONFIGURAÇÃO DE CORS ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ MODELOS DE DADOS ============
class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    history: List[List[str]] = []


# ============ CONFIGURAÇÕES DE DIRETÓRIO ============
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ============ ENDPOINTS ============

@app.get("/health")
async def health_check():
    """Verifica se a API está online"""
    return {"status": "online", "version": app.version}


@app.post("/auth/login")
async def login(data: LoginRequest):
    """Realiza o login do usuário"""
    result = await auth_service.login(data.email, data.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos"
        )

    return result


@app.post("/admin/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint para upload de PDFs que serão processados e armazenados
    na base de conhecimento do RAG
    """
    try:
        # Verificar se é PDF
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Apenas arquivos PDF são permitidos."
            )

        # Salvar arquivo temporariamente
        temp_file = UPLOAD_DIR / file.filename
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Processar PDF com RAG Service
        try:
            num_chunks = await rag_service.ingest_pdf(
                str(temp_file),
                file.filename
            )

            logger.info(f"PDF '{file.filename}' processado. {num_chunks} chunks criados.")

            return {
                "message": f"Arquivo {file.filename} processado com sucesso!",
                "chunks_criados": num_chunks
            }

        finally:
            # Limpar arquivo temporário
            if temp_file.exists():
                temp_file.unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar upload: {str(e)}"
        )


@app.post("/consultoria/chat")
async def chat(data: ChatRequest):
    """Endpoint de consulta RAG"""
    try:
        logger.info(f"Nova consulta RAG: {data.message}")

        # Converte o histórico (lista de listas) para lista de tuplas para o LangChain
        formatted_history = [tuple(h) for h in data.history]

        response = await rag_service.get_answer(
            data.message,
            formatted_history
        )

        return response

    except Exception as e:
        logger.error(f"Erro no chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )


# ============ MAIN ============
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)