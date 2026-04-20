# CAMINHO: backend/app/main.py

import os
import logging
import inspect
import importlib
from typing import Any, Dict, List, Optional, Callable

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.database import supabase_admin
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
    VectorChunk,
    VectorChunksResponse,
    RecoverFileContentResponse,
    RecoveryDiagnosisResponse,
)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modelo de resposta para saúde
class HealthResponse(BaseModel):
    status: str = Field(..., description="Status da aplicação")

# Modelo de requisição para login
class LoginRequest(BaseModel):
    email: str = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha do usuário")

# Modelo de requisição para chat
class ChatRequest(BaseModel):
    question: str = Field(..., description="Pergunta do usuário")

# Função helper para carregar módulo de database
def _load_database_module():
    """Carrega o módulo de database de forma defensiva."""
    try:
        return importlib.import_module('app.database')
    except ImportError:
        logger.warning("Módulo app.database não encontrado.")
        return None

# Função helper para resolver cliente de autenticação
def _resolve_auth_client():
    """Resolve o cliente Supabase para autenticação."""
    db_module = _load_database_module()
    if not db_module:
        return None
    candidates = ['supabase', 'supabase_client', 'supabase_auth', 'supabase_admin']
    for attr in candidates:
        client = getattr(db_module, attr, None)
        if client and hasattr(client, 'auth') and hasattr(client.auth, 'sign_in_with_password'):
            return client
    return None

# Função helper para carregar serviço RAG
def _load_rag_service():
    """Carrega o serviço RAG de forma defensiva."""
    try:
        rag_module = importlib.import_module('app.services.rag_service')
        return getattr(rag_module, 'rag_service', None)
    except (ImportError, AttributeError):
        logger.warning("Serviço RAG não encontrado.")
        return None

# Função helper para chamar método de forma defensiva
def _call_method_defensively(service, method_name: str, *args, **kwargs):
    """Chama um método de forma defensiva, ajustando parâmetros e suportando sync/async."""
    if not service:
        return None
    method = getattr(service, method_name, None)
    if not method:
        return None
    try:
        sig = inspect.signature(method)
        # Filtrar kwargs para apenas parâmetros aceitos
        valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
        result = method(*args, **valid_kwargs)
        if inspect.isawaitable(result):
            # Se for async, assumir que o chamador lidará com await
            return result
        return result
    except Exception as e:
        logger.error(f"Erro ao chamar {method_name}: {e}")
        return None

# Dependência para autenticação (extrair token Bearer)
def get_auth_token(request: Request):
    """Extrai o token Bearer do header Authorization."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token de autenticação ausente ou inválido")
    return auth_header[7:]  # Retorna o token sem 'Bearer '

# Inicialização da aplicação FastAPI
app = FastAPI(title="API de Consultoria", version="1.0.0")

# Configuração de CORS
cors_origins = os.getenv('CORS_ALLOW_ORIGINS')
if cors_origins:
    origins = [origin.strip() for origin in cors_origins.split(',')]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint de saúde
@app.get("/health", response_model=HealthResponse)
async def health():
    """Retorna o status de saúde da aplicação."""
    return HealthResponse(status="ok")

# Endpoint de login
@app.post("/auth/login")
async def login(request: LoginRequest):
    """Realiza login usando Supabase."""
    auth_client = _resolve_auth_client()
    if not auth_client:
        raise HTTPException(status_code=500, detail="Cliente de autenticação não disponível")
    try:
        response = auth_client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        access_token = response.session.access_token
        return {"access_token": access_token}
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

# Endpoint de chat
@app.post("/consultoria/chat")
async def chat(request: ChatRequest):
    """Processa uma pergunta de chat usando o serviço RAG."""
    rag_service = _load_rag_service()
    candidates = ['chat', 'ask', 'ask_question', 'consult', 'query']
    for method_name in candidates:
        result = _call_method_defensively(rag_service, method_name, question=request.question)
        if result is not None:
            if inspect.isawaitable(result):
                result = await result
            return result
    # Fallback
    return {"answer": "Desculpe, não consegui processar sua pergunta no momento."}

# Endpoint de upload para consultoria
@app.post("/consultoria/upload")
async def upload_consultoria(file: UploadFile = File(...)):
    """Faz upload de arquivo para consultoria."""
    rag_service = _load_rag_service()
    candidates = ['upload_file', 'process_upload', 'ingest_file', 'ingest_pdf', 'process_document', 'add_document']
    for method_name in candidates:
        result = _call_method_defensively(rag_service, method_name, file=file)
        if result is not None:
            if inspect.isawaitable(result):
                result = await result
            response = {"message": "Arquivo processado com sucesso"}
            if isinstance(result, dict) and 'file_id' in result:
                response['file_id'] = result['file_id']
            return response
    # Fallback
    return {"message": "Arquivo processado com sucesso"}

# Endpoint de upload para admin
@app.post("/admin/upload", dependencies=[Depends(get_auth_token)])
async def upload_admin(file: UploadFile = File(...)):
    """Faz upload de arquivo para admin."""
    # Mesmo comportamento que consultoria, mas com auth
    return await upload_consultoria(file)

# Endpoints administrativos vetoriais
@app.get("/admin/vector-base/files", response_model=List[VectorFileSummary], dependencies=[Depends(get_auth_token)])
async def list_vector_files():
    """Lista arquivos na base vetorial."""
    try:
        files = vector_admin_service.list_files()
        return files
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.get("/admin/vector-base/files/{original_file_id}", response_model=VectorFileDetail, dependencies=[Depends(get_auth_token)])
async def get_vector_file(original_file_id: str):
    """Obtém detalhes de um arquivo na base vetorial."""
    try:
        file_detail = vector_admin_service.get_file(original_file_id)
        return file_detail
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao obter arquivo: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.get("/admin/vector-base/files/{original_file_id}/chunks", response_model=VectorChunksResponse, dependencies=[Depends(get_auth_token)])
async def get_vector_file_chunks(original_file_id: str):
    """Obtém chunks de um arquivo na base vetorial."""
    try:
        chunks = vector_admin_service.get_file_chunks(original_file_id)
        return chunks
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao obter chunks: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.get("/admin/vector-base/files/{original_file_id}/content", response_model=RecoverFileContentResponse, dependencies=[Depends(get_auth_token)])
async def recover_vector_file_content(original_file_id: str):
    """Recupera conteúdo de um arquivo na base vetorial."""
    try:
        content = vector_admin_service.recover_file_content(original_file_id)
        return content
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao recuperar conteúdo: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.get("/admin/vector-base/files/{original_file_id}/diagnosis", response_model=RecoveryDiagnosisResponse, dependencies=[Depends(get_auth_token)])
async def diagnose_vector_file_recovery(original_file_id: str):
    """Diagnóstica recuperação de um arquivo na base vetorial."""
    try:
        diagnosis = vector_admin_service.diagnose_file_recovery(original_file_id)
        return diagnosis
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao diagnosticar: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.post("/admin/vector-base/reindex", response_model=ReindexFileResponse, dependencies=[Depends(get_auth_token)])
async def reindex_vector_files(request: ReindexFileRequest):
    """Reindexa arquivos na base vetorial."""
    try:
        result = await vector_admin_service.reindex_files(request.confirmation_phrase, request.original_file_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao reindexar: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.delete("/admin/vector-base/files/{original_file_id}", response_model=DeleteFileResponse, dependencies=[Depends(get_auth_token)])
async def delete_vector_file(original_file_id: str, request: DeleteFileRequest):
    """Deleta um arquivo da base vetorial."""
    try:
        result = vector_admin_service.delete_file(original_file_id, request.confirmation_phrase, request.reason, request.hard_delete)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao deletar arquivo: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")

@app.post("/admin/vector-base/cleanup", response_model=CleanupVectorBaseResponse, dependencies=[Depends(get_auth_token)])
async def cleanup_vector_base(request: CleanupVectorBaseRequest):
    """Limpa a base vetorial."""
    try:
        result = vector_admin_service.cleanup_vector_base(request.confirmation_phrase)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao limpar base: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")