import logging
import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database import supabase_admin
from app.services.vector_admin_service import vector_admin_service
from app.services.rag_service import rag_service
from app.vector_admin_schemas import (
    VectorFileSummary,
    VectorFileDetail,
    VectorChunksResponse,
    RecoverFileContentResponse,
    RecoveryDiagnosisResponse,
    DeleteFileRequest,
    DeleteFileResponse,
    CleanupVectorBaseRequest,
    CleanupVectorBaseResponse,
    ReindexFileRequest,
    ReindexFileResponse,
)

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginUserResponse(BaseModel):
    id: str
    email: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: LoginUserResponse

class ChatRequest(BaseModel):
    message: str
    history: List[List[str]] = []

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

@app.post("/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    try:
        auth_response = supabase_admin.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        if not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        session = auth_response.session
        access_token = session.access_token
        auth_user = auth_response.user
        user_id = auth_user.id
        email = auth_user.email
        role = None
        public_user = _load_public_user_profile(user_id=user_id, email=None)
        if public_user:
            role = public_user.get('role')
        if not role:
            public_user = _load_public_user_profile(user_id=None, email=email)
            if public_user:
                role = public_user.get('role')
        if not role:
            role = _extract_role_from_auth_user(auth_user)
        if not role:
            role = 'user'
        role = _normalize_role(role)
        user_response = LoginUserResponse(id=user_id, email=email, role=role)
        return LoginResponse(access_token=access_token, token_type="bearer", user=user_response)
    except Exception as e:
        logger.exception("Erro no login")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/consultoria/chat")
async def chat(data: ChatRequest):
    try:
        formatted_history = [tuple(h) for h in data.history]
        response = await rag_service.get_answer(data.message, formatted_history)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro no chat")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/admin/upload")
async def upload_admin(file: UploadFile = File(...)):
    temp_path = None
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Arquivo inválido")
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        result = await rag_service.ingest_pdf(temp_path, file.filename)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro no upload administrativo")
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@app.get("/admin/vector-base/files", response_model=List[VectorFileSummary])
async def get_vector_files():
    try:
        return vector_admin_service.get_files()
    except Exception as e:
        logger.exception("Erro ao listar arquivos vetoriais")
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}", response_model=VectorFileDetail)
async def get_vector_file(original_file_id: str):
    try:
        return vector_admin_service.get_file(original_file_id)
    except Exception as e:
        logger.exception("Erro ao obter arquivo vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao obter arquivo: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/chunks", response_model=VectorChunksResponse)
async def get_vector_file_chunks(original_file_id: str):
    try:
        return vector_admin_service.get_file_chunks(original_file_id)
    except Exception as e:
        logger.exception("Erro ao obter chunks do arquivo vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao obter chunks: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/content", response_model=RecoverFileContentResponse)
async def get_vector_file_content(original_file_id: str):
    try:
        return vector_admin_service.get_file_content(original_file_id)
    except Exception as e:
        logger.exception("Erro ao recuperar conteúdo do arquivo vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar conteúdo: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/diagnosis", response_model=RecoveryDiagnosisResponse)
async def get_vector_file_diagnosis(original_file_id: str):
    try:
        return vector_admin_service.get_file_diagnosis(original_file_id)
    except Exception as e:
        logger.exception("Erro ao obter diagnóstico do arquivo vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao obter diagnóstico: {str(e)}")

@app.post("/admin/vector-base/files/{original_file_id}/delete", response_model=DeleteFileResponse)
async def delete_vector_file(original_file_id: str, request: DeleteFileRequest):
    try:
        delete_chunks = request.delete_chunks if request.delete_chunks is not None else request.hard_delete
        result = vector_admin_service.delete_file(original_file_id, delete_chunks)
        normalized = _normalize_delete_response(original_file_id, result)
        return DeleteFileResponse(**normalized)
    except Exception as e:
        logger.exception("Erro ao deletar arquivo vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar arquivo: {str(e)}")

@app.post("/admin/vector-base/cleanup", response_model=CleanupVectorBaseResponse)
async def cleanup_vector_base(request: CleanupVectorBaseRequest):
    try:
        dry_run = request.dry_run if request.dry_run is not None else (request.confirmation_phrase == "SIMULACAO")
        result = vector_admin_service.cleanup(dry_run)
        normalized = _normalize_cleanup_response(result)
        return CleanupVectorBaseResponse(**normalized)
    except Exception as e:
        logger.exception("Erro ao executar cleanup vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao executar cleanup: {str(e)}")

@app.post("/admin/vector-base/reindex", response_model=ReindexFileResponse)
async def reindex_vector_base(request: ReindexFileRequest):
    try:
        file_ids = request.original_file_ids or []
        result = await vector_admin_service.reindex_files(file_ids)
        normalized = _normalize_reindex_response(request, result)
        return ReindexFileResponse(**normalized)
    except Exception as e:
        logger.exception("Erro ao reindexar base vetorial")
        raise HTTPException(status_code=500, detail=f"Erro ao reindexar base: {str(e)}")

def _normalize_role(value: Any) -> str:
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ['admin', 'administrator']:
            return 'admin'
        elif lower_value == 'user':
            return 'user'
    return 'user'

def _extract_role_from_auth_user(auth_user: Any) -> Optional[str]:
    if hasattr(auth_user, 'user_metadata') and auth_user.user_metadata:
        return auth_user.user_metadata.get('role')
    elif isinstance(auth_user, dict) and 'user_metadata' in auth_user:
        return auth_user['user_metadata'].get('role')
    return None

def _load_public_user_profile(user_id: Optional[str], email: Optional[str]) -> Optional[Dict[str, Any]]:
    if user_id:
        response = supabase_admin.table('users').select('*').eq('id', user_id).execute()
        if response.data:
            return response.data[0]
    if email:
        response = supabase_admin.table('users').select('*').eq('email', email).execute()
        if response.data:
            return response.data[0]
    return None

def _normalize_delete_response(original_file_id: str, result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return {
            'original_file_id': result.get('original_file_id', original_file_id),
            'original_file_name': result.get('original_file_name', original_file_id),
            'documents_deleted': result.get('documents_deleted', 0),
            'ingestion_logs_deleted': result.get('ingestion_logs_deleted', 0),
            'storage_deleted': result.get('storage_deleted', False),
            'storage_bucket': result.get('storage_bucket', None),
            'storage_path': result.get('storage_path', None),
            'status': result.get('status', 'success'),
            'message': result.get('message', 'Arquivo deletado'),
        }
    else:
        return {
            'original_file_id': original_file_id,
            'original_file_name': original_file_id,
            'documents_deleted': 0,
            'ingestion_logs_deleted': 0,
            'storage_deleted': False,
            'storage_bucket': None,
            'storage_path': None,
            'status': 'success',
            'message': 'Arquivo deletado',
        }

def _normalize_cleanup_response(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return {
            'total_files_processed': result.get('total_files_processed', 0),
            'total_documents_deleted': result.get('total_documents_deleted', 0),
            'total_ingestion_logs_deleted': result.get('total_ingestion_logs_deleted', 0),
            'total_storage_deleted': result.get('total_storage_deleted', 0),
            'status': result.get('status', 'success'),
            'message': result.get('message', 'Limpeza executada'),
        }
    else:
        return {
            'total_files_processed': 0,
            'total_documents_deleted': 0,
            'total_ingestion_logs_deleted': 0,
            'total_storage_deleted': 0,
            'status': 'success',
            'message': 'Limpeza executada',
        }

def _normalize_reindex_response(request: ReindexFileRequest, result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return {
            'processed_files': result.get('processed_files', len(request.original_file_ids or [])),
            'failed_files': result.get('failed_files', 0),
            'total_chunks_created': result.get('total_chunks_created', 0),
            'status': result.get('status', 'success'),
            'message': result.get('message', 'Reindexação iniciada'),
        }
    else:
        return {
            'processed_files': len(request.original_file_ids or []),
            'failed_files': 0,
            'total_chunks_created': 0,
            'status': 'success',
            'message': 'Reindexação iniciada',
        }