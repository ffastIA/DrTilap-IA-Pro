import logging
import time
import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database import supabase_admin
from app.services.vector_admin_service import vector_admin_service
from app.services.rag_service import rag_service
from app.auth.auth_service import auth_service
from app.dependencies import get_current_user, get_current_admin_user
from app.services.video_service import video_service
from app.video_schemas import VideoUploadResponse, VideoListResponse, VideoDeleteResponse

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)
logging.getLogger("AuthService").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

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
    start_time = time.perf_counter()
    logger.info("[main.login] início da requisição para email=%s", data.email)
    try:
        logger.info("[main.login] chamando auth_service.login para email=%s", data.email)
        result = await auth_service.login(data.email, data.password)
        logger.info("[main.login] auth_service.login retornou para email=%s", data.email)
        if result is None:
            logger.warning("[main.login] auth_service retornou None para email=%s", data.email)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = result['access_token']
        token_type = result['token_type']
        user = result['user']
        logger.info("[main.login] montando resposta para user_id=%s role=%s", user['id'], user['role'])
        user_response = LoginUserResponse(id=user['id'], email=user['email'], role=user['role'])
        elapsed_seconds = time.perf_counter() - start_time
        logger.info("[main.login] login concluído para email=%s em %.3fs", data.email, elapsed_seconds)
        return LoginResponse(access_token=access_token, token_type=token_type, user=user_response)
    except HTTPException:
        logger.exception("[main.login] HTTPException durante login para email=%s", data.email)
        raise
    except Exception:
        logger.exception("[main.login] exceção inesperada para email=%s", data.email)
        logger.exception("Erro no login")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/consultoria/chat")
async def chat(data: ChatRequest):
    try:
        response = rag_service.get_answer(data.message, data.history)
        return {"answer": response, "sources": []}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro no chat")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ========== ROTAS ADMIN (SEM AUTENTICAÇÃO) ==========

@app.post("/admin/upload")
async def upload_admin(file: UploadFile = File(...)):
    temp_path = None
    try:
        logger.info(f"[upload_admin] Iniciando upload para filename={file.filename}")
        if not file.filename:
            raise HTTPException(status_code=400, detail="Arquivo inválido")
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        result = await rag_service.ingest_pdf(temp_path, file.filename)
        logger.info(f"[upload_admin] Upload concluído: {result.get('status')}")
        if result.get('status') == 'already_exists':
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=409, content=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[upload_admin] Erro no upload")
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@app.get("/admin/vector-base/files", response_model=List[VectorFileSummary])
async def get_vector_files():
    try:
        logger.info(f"[get_vector_files] Listando arquivos")
        return vector_admin_service.get_files()
    except Exception as e:
        logger.exception(f"[get_vector_files] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}", response_model=VectorFileDetail)
async def get_vector_file(original_file_id: str):
    try:
        logger.info(f"[get_vector_file] Obtendo arquivo {original_file_id}")
        return vector_admin_service.get_file(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao obter arquivo: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/chunks", response_model=VectorChunksResponse)
async def get_vector_file_chunks(original_file_id: str):
    try:
        logger.info(f"[get_vector_file_chunks] Obtendo chunks de {original_file_id}")
        return vector_admin_service.get_file_chunks(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file_chunks] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao obter chunks: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/content", response_model=RecoverFileContentResponse)
async def get_vector_file_content(original_file_id: str):
    try:
        logger.info(f"[get_vector_file_content] Recuperando conteúdo de {original_file_id}")
        return vector_admin_service.get_file_content(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file_content] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar conteúdo: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/diagnosis", response_model=RecoveryDiagnosisResponse)
async def get_vector_file_diagnosis(original_file_id: str):
    try:
        logger.info(f"[get_vector_file_diagnosis] Diagnosticando {original_file_id}")
        return vector_admin_service.get_file_diagnosis(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file_diagnosis] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao obter diagnóstico: {str(e)}")

@app.post("/admin/vector-base/files/{original_file_id}/delete", response_model=DeleteFileResponse)
async def delete_vector_file(original_file_id: str, request: DeleteFileRequest):
    try:
        logger.info(f"[delete_vector_file] Deletando arquivo {original_file_id}")
        hard_delete = request.hard_delete if request.hard_delete is not None else True
        result = vector_admin_service.delete_file(
            original_file_id,
            request.confirmation_phrase,
            request.reason,
            hard_delete,
        )
        normalized = _normalize_delete_response(original_file_id, result)
        return DeleteFileResponse(**normalized)
    except Exception as e:
        logger.exception(f"[delete_vector_file] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar arquivo: {str(e)}")

@app.post("/admin/vector-base/cleanup", response_model=CleanupVectorBaseResponse)
async def cleanup_vector_base(request: CleanupVectorBaseRequest):
    try:
        logger.info(f"[cleanup_vector_base] Executando cleanup")
        if request.dry_run is True and request.confirmation_phrase == "SIMULACAO":
            result = vector_admin_service.cleanup(True)
        else:
            result = vector_admin_service.cleanup(request.confirmation_phrase)
        normalized = _normalize_cleanup_response(result)
        return CleanupVectorBaseResponse(**normalized)
    except Exception as e:
        logger.exception(f"[cleanup_vector_base] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao executar cleanup: {str(e)}")

@app.post("/admin/vector-base/reindex", response_model=ReindexFileResponse)
async def reindex_vector_base(request: ReindexFileRequest):
    try:
        logger.info(f"[reindex_vector_base] Iniciando reindexação")
        file_ids = request.original_file_ids or []
        result = await vector_admin_service.reindex_files(file_ids)
        normalized = _normalize_reindex_response(request, result)
        return ReindexFileResponse(**normalized)
    except Exception as e:
        logger.exception(f"[reindex_vector_base] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao reindexar base: {str(e)}")

# ========== ROTAS VÍDEOS ==========

@app.post("/videos/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("geral"),
    current_user: dict = Depends(get_current_admin_user),  # 🔒 somente admin
):
    """
    Faz upload de um vídeo para a biblioteca.
    Requer autenticação com role=admin.
    Formatos aceitos: .mp4, .webm, .mov
    """
    temp_path = None
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Arquivo inválido")

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ("mp4", "webm", "mov"):
            raise HTTPException(
                status_code=400,
                detail="Formato não suportado. Use: .mp4, .webm ou .mov",
            )

        logger.info(
            "[upload_video] admin=%s filename=%s title='%s'",
            current_user["email"], file.filename, title,
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            temp_path = tmp.name
            content = await file.read()
            tmp.write(content)

        result = video_service.upload_video(
            file_path=temp_path,
            filename=file.filename,
            title=title,
            description=description,
            category=category,
            uploader_id=current_user["id"],
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("[upload_video] erro inesperado")
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.get("/videos", response_model=VideoListResponse)
async def list_videos(
    current_user: dict = Depends(get_current_user),  # 🔑 qualquer usuário autenticado
):
    """
    Retorna a lista de vídeos com signed URLs válidas por 24 h.
    Requer autenticação (qualquer role).
    """
    try:
        logger.info("[list_videos] user=%s", current_user["email"])
        return video_service.list_videos()
    except Exception as e:
        logger.exception("[list_videos] erro")
        raise HTTPException(status_code=500, detail=f"Erro ao listar vídeos: {str(e)}")


@app.delete("/videos/{video_id}", response_model=VideoDeleteResponse)
async def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 somente admin
):
    """
    Remove um vídeo da biblioteca (Storage + metadados).
    Requer autenticação com role=admin.
    """
    try:
        logger.info("[delete_video] admin=%s video_id=%s", current_user["email"], video_id)
        return video_service.delete_video(video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("[delete_video] erro")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar vídeo: {str(e)}")


# ========== FUNÇÕES AUXILIARES ==========

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