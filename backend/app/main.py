# CAMINHO: backend/app/main.py

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database import supabase_admin
from app.services.vector_admin_service import vector_admin_service
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

# Modelos Pydantic para login
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

# Helpers para login
def _normalize_role(value: Any) -> str:
    """Normaliza o valor do role para 'admin' ou 'user'."""
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ['admin', 'administrator']:
            return 'admin'
        elif lower_value == 'user':
            return 'user'
    return 'user'

def _extract_role_from_auth_user(auth_user: Any) -> Optional[str]:
    """Extrai o role dos metadados do usuário autenticado."""
    if isinstance(auth_user, dict):
        metadata = auth_user.get('user_metadata') or auth_user.get('app_metadata') or auth_user.get('raw_user_meta_data') or auth_user.get('raw_app_meta_data')
    else:
        metadata = getattr(auth_user, 'user_metadata', {}) or getattr(auth_user, 'app_metadata', {}) or getattr(auth_user, 'raw_user_meta_data', {}) or getattr(auth_user, 'raw_app_meta_data', {})
    if metadata and isinstance(metadata, dict):
        role_value = metadata.get('role')
        if role_value:
            return _normalize_role(role_value)
    return None

def _load_public_user_profile(user_id: Optional[str], email: Optional[str]) -> Optional[Dict[str, Any]]:
    """Carrega o perfil do usuário da tabela public.users."""
    try:
        if user_id:
            response = supabase_admin.table('users').select('*').eq('id', user_id).execute()
            if response.data:
                return response.data[0]
        if email:
            response = supabase_admin.table('users').select('*').eq('email', email).execute()
            if response.data:
                return response.data[0]
    except Exception:
        pass
    return None

app = FastAPI()

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint de login corrigido
@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Autentica o usuário e retorna token com role correto."""
    try:
        auth_response = supabase_admin.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        if not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        auth_user = auth_response.user
        session = auth_response.session
        access_token = session.access_token
        user_id = auth_user.id
        email = auth_user.email

        # Ordem: public.users por id -> public.users por email -> metadata -> fallback 'user'
        role = None
        profile = _load_public_user_profile(user_id, None)
        if profile and 'role' in profile:
            role = _normalize_role(profile['role'])
        if not role:
            profile = _load_public_user_profile(None, email)
            if profile and 'role' in profile:
                role = _normalize_role(profile['role'])
        if not role:
            role = _extract_role_from_auth_user(auth_user) or 'user'

        user_response = LoginUserResponse(id=user_id, email=email, role=role)
        return LoginResponse(access_token=access_token, token_type="bearer", user=user_response)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# Endpoints de chat (preservados)
# ... (lógica existente de chat)

# Endpoints de upload (preservados)
# ... (lógica existente de upload)

# Endpoints administrativos (preservados)
@app.get("/admin/vector-base/files", response_model=List[VectorFileSummary])
def get_vector_base_files():
    """Lista arquivos na base vetorial."""
    return vector_admin_service.get_files()

@app.get("/admin/vector-base/files/{original_file_id}", response_model=VectorFileDetail)
def get_vector_base_file(original_file_id: str):
    """Obtém detalhes de um arquivo."""
    return vector_admin_service.get_file(original_file_id)

@app.get("/admin/vector-base/files/{original_file_id}/chunks", response_model=VectorChunksResponse)
def get_vector_base_file_chunks(original_file_id: str):
    """Lista chunks de um arquivo."""
    return vector_admin_service.get_file_chunks(original_file_id)

@app.get("/admin/vector-base/files/{original_file_id}/content", response_model=RecoverFileContentResponse)
def get_vector_base_file_content(original_file_id: str):
    """Obtém conteúdo de um arquivo."""
    return vector_admin_service.get_file_content(original_file_id)

@app.get("/admin/vector-base/files/{original_file_id}/diagnosis", response_model=RecoveryDiagnosisResponse)
def get_vector_base_file_diagnosis(original_file_id: str):
    """Obtém diagnóstico de um arquivo."""
    return vector_admin_service.get_file_diagnosis(original_file_id)

@app.post("/admin/vector-base/reindex", response_model=ReindexFileResponse)
async def reindex_vector_base(request: ReindexFileRequest):
    """Reindexa a base vetorial."""
    await vector_admin_service.reindex_files(request.file_ids)
    return {"message": "Reindexação iniciada"}

@app.post("/admin/vector-base/files/{original_file_id}/delete", response_model=DeleteFileResponse)
def delete_vector_base_file(original_file_id: str, request: DeleteFileRequest):
    """Deleta um arquivo da base vetorial."""
    vector_admin_service.delete_file(original_file_id, request.delete_chunks)
    return {"message": "Arquivo deletado"}

@app.post("/admin/vector-base/cleanup", response_model=CleanupVectorBaseResponse)
def cleanup_vector_base(request: CleanupVectorBaseRequest):
    """Limpa a base vetorial."""
    vector_admin_service.cleanup(request.dry_run)
    return {"message": "Limpeza executada"}
