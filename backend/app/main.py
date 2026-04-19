# CAMINHO: backend/app/main.py

from pathlib import Path
import logging
import shutil
from typing import Any, Dict, List, Tuple
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from app.auth.auth_service import auth_service
from app.database import supabase_auth, supabase_admin
from app.services.rag_service import rag_service
from app.services.vector_admin_service import vector_admin_service
from app.vector_admin_schemas import (
    VectorFileSummary,
    VectorFileDetail,
    DeleteFileRequest,
    DeleteFileResponse,
    CleanupVectorBaseRequest,
    CleanupVectorBaseResponse,
    ReindexFileRequest,
    ReindexFileResponse,
    VectorChunksResponse,
    RecoverFileContentResponse,
    RecoveryDiagnosisResponse,
)

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização da aplicação FastAPI
app = FastAPI(title="Dr. Tilápia API", version="2.2.0")

# Diretório para uploads temporários
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Segurança para autenticação Bearer
security = HTTPBearer()


class LoginRequest(BaseModel):
    """
    Modelo para requisição de login.
    """
    email: str
    password: str


class ChatRequest(BaseModel):
    """
    Modelo para requisição de chat.
    """
    message: str
    history: List[List[str]]


def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependência para obter o usuário admin atual a partir do token Bearer.

    Args:
        credentials: Credenciais de autorização HTTP.

    Returns:
        Dict[str, Any]: Dados do usuário admin (id, email, role).

    Raises:
        HTTPException: Se o token for inválido ou o usuário não for admin.
    """
    token = credentials.credentials
    try:
        user = supabase_auth.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = user.user.id
        result = supabase_admin.table("users").select("id, email, role").eq("id", user_id).execute()
        if not result.data or result.data[0]["role"] != "admin":
            raise HTTPException(status_code=403, detail="Acesso negado: usuário não é admin")
        return result.data[0]
    except Exception as e:
        logger.error(f"Erro ao validar usuário admin: {e}")
        raise HTTPException(status_code=401, detail="Erro na autenticação")


@app.get("/health")
def health_check():
    """
    Endpoint para verificação de saúde da API.

    Returns:
        Dict[str, str]: Status da API.
    """
    return {"status": "ok"}


@app.post("/auth/login")
async def login(request: LoginRequest):
    """
    Endpoint para login de usuário.

    Args:
        request: Dados de login (email e senha).

    Returns:
        Dict: Resultado do login.

    Raises:
        HTTPException: Se as credenciais forem inválidas.
    """
    result = await auth_service.login(request.email, request.password)
    if not result:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return result


@app.post("/consultoria/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint para upload de arquivos PDF para ingestão no RAG.

    Args:
        file: Arquivo PDF a ser enviado.

    Returns:
        Dict[str, str]: Mensagem de sucesso.

    Raises:
        HTTPException: Se o arquivo não for PDF.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
    temp_file = UPLOAD_DIR / file.filename
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        await rag_service.ingest_pdf(str(temp_file), file.filename)
        logger.info(f"Arquivo {file.filename} processado com sucesso")
    finally:
        if temp_file.exists():
            temp_file.unlink()
    return {"message": "Arquivo processado com sucesso"}


@app.post("/consultoria/chat")
async def chat(request: ChatRequest):
    """
    Endpoint para interação de chat com o RAG.

    Args:
        request: Mensagem e histórico do chat.

    Returns:
        Dict[str, str]: Resposta do RAG.
    """
    formatted_history: List[Tuple[str, str]] = [tuple(item) for item in request.history]
    answer = await rag_service.get_answer(request.message, formatted_history)
    return {"answer": answer}


@app.get("/admin/vector-base/files", response_model=List[VectorFileSummary], dependencies=[Depends(get_current_admin_user)])
def list_files():
    """
    Endpoint para listar arquivos na base vetorial (apenas admin).

    Returns:
        List[VectorFileSummary]: Lista de resumos dos arquivos.
    """
    return vector_admin_service.list_files()


@app.get("/admin/vector-base/files/{original_file_id}", response_model=VectorFileDetail, dependencies=[Depends(get_current_admin_user)])
def get_file(original_file_id: str):
    """
    Endpoint para obter detalhes de um arquivo na base vetorial (apenas admin).

    Args:
        original_file_id: ID do arquivo original.

    Returns:
        VectorFileDetail: Detalhes do arquivo.
    """
    return vector_admin_service.get_file(original_file_id)


@app.post("/admin/vector-base/files/{original_file_id}/delete", response_model=DeleteFileResponse, dependencies=[Depends(get_current_admin_user)])
def delete_file(original_file_id: str, request: DeleteFileRequest):
    """
    Endpoint para deletar um arquivo da base vetorial (apenas admin).

    Args:
        original_file_id: ID do arquivo original.
        request: Dados da requisição de deleção.

    Returns:
        DeleteFileResponse: Resposta da deleção.
    """
    return vector_admin_service.delete_file(original_file_id, request.confirmation_phrase, request.reason, request.hard_delete)


@app.post("/admin/vector-base/cleanup", response_model=CleanupVectorBaseResponse, dependencies=[Depends(get_current_admin_user)])
def cleanup_vector_base(request: CleanupVectorBaseRequest):
    """
    Endpoint para limpeza da base vetorial (apenas admin).

    Args:
        request: Dados da requisição de limpeza.

    Returns:
        CleanupVectorBaseResponse: Resposta da limpeza.
    """
    return vector_admin_service.cleanup_vector_base(request.confirmation_phrase)


@app.post("/admin/vector-base/reindex", response_model=ReindexFileResponse, dependencies=[Depends(get_current_admin_user)])
async def reindex_files(request: ReindexFileRequest):
    """
    Endpoint para reindexar arquivos na base vetorial (apenas admin).

    Args:
        request: Dados da requisição de reindexação.

    Returns:
        ReindexFileResponse: Resposta da reindexação.
    """
    return await vector_admin_service.reindex_files(request.confirmation_phrase, request.original_file_ids)


@app.get("/admin/vector-base/files/{original_file_id}/chunks", response_model=VectorChunksResponse, dependencies=[Depends(get_current_admin_user)])
def get_file_chunks(original_file_id: str):
    """
    Endpoint para obter chunks de um arquivo na base vetorial (apenas admin).

    Args:
        original_file_id: ID do arquivo original.

    Returns:
        VectorChunksResponse: Chunks do arquivo.
    """
    return vector_admin_service.get_file_chunks(original_file_id)


@app.get("/admin/vector-base/files/{original_file_id}/content", response_model=RecoverFileContentResponse, dependencies=[Depends(get_current_admin_user)])
def recover_file_content(original_file_id: str):
    """
    Endpoint para recuperar conteúdo de um arquivo na base vetorial (apenas admin).

    Args:
        original_file_id: ID do arquivo original.

    Returns:
        RecoverFileContentResponse: Conteúdo recuperado.
    """
    return vector_admin_service.recover_file_content(original_file_id)


@app.get("/admin/vector-base/files/{original_file_id}/diagnosis", response_model=RecoveryDiagnosisResponse, dependencies=[Depends(get_current_admin_user)])
def diagnose_file_recovery(original_file_id: str):
    """
    Endpoint para diagnóstico de recuperação de um arquivo na base vetorial (apenas admin).

    Args:
        original_file_id: ID do arquivo original.

    Returns:
        RecoveryDiagnosisResponse: Diagnóstico de recuperação.
    """
    return vector_admin_service.diagnose_file_recovery(original_file_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
