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
from app.services.fish_image_service import fish_image_service
from app.services.image_processing_service import image_processing_service
from app.fish_schemas import (
    FishImageUploadResponse, FishImageListResponse, FishImageDeleteResponse,
    FishAnalysisListResponse, FishAnalysisDeleteResponse,
    ProcessRequest, ProcessResponse,
)

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

# Origens permitidas — definir ALLOWED_ORIGINS no .env em produção
# Exemplo: ALLOWED_ORIGINS=https://app.drtilapia.com,https://www.drtilapia.com
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
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
async def chat(data: ChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        response = rag_service.get_answer(data.message, data.history)
        return {"answer": response, "sources": []}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro no chat")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ========== ROTAS ADMIN (requer role=admin) ==========

@app.post("/admin/upload")
async def upload_admin(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin_user),
):
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
async def get_vector_files(current_user: dict = Depends(get_current_admin_user)):
    try:
        logger.info(f"[get_vector_files] Listando arquivos")
        return vector_admin_service.get_files()
    except Exception as e:
        logger.exception(f"[get_vector_files] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}", response_model=VectorFileDetail)
async def get_vector_file(original_file_id: str, current_user: dict = Depends(get_current_admin_user)):
    try:
        logger.info(f"[get_vector_file] Obtendo arquivo {original_file_id}")
        return vector_admin_service.get_file(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao obter arquivo: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/chunks", response_model=VectorChunksResponse)
async def get_vector_file_chunks(original_file_id: str, current_user: dict = Depends(get_current_admin_user)):
    try:
        logger.info(f"[get_vector_file_chunks] Obtendo chunks de {original_file_id}")
        return vector_admin_service.get_file_chunks(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file_chunks] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao obter chunks: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/content", response_model=RecoverFileContentResponse)
async def get_vector_file_content(original_file_id: str, current_user: dict = Depends(get_current_admin_user)):
    try:
        logger.info(f"[get_vector_file_content] Recuperando conteúdo de {original_file_id}")
        return vector_admin_service.get_file_content(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file_content] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar conteúdo: {str(e)}")

@app.get("/admin/vector-base/files/{original_file_id}/diagnosis", response_model=RecoveryDiagnosisResponse)
async def get_vector_file_diagnosis(original_file_id: str, current_user: dict = Depends(get_current_admin_user)):
    try:
        logger.info(f"[get_vector_file_diagnosis] Diagnosticando {original_file_id}")
        return vector_admin_service.get_file_diagnosis(original_file_id)
    except Exception as e:
        logger.exception(f"[get_vector_file_diagnosis] Erro")
        raise HTTPException(status_code=500, detail=f"Erro ao obter diagnóstico: {str(e)}")

@app.post("/admin/vector-base/files/{original_file_id}/delete", response_model=DeleteFileResponse)
async def delete_vector_file(original_file_id: str, request: DeleteFileRequest, current_user: dict = Depends(get_current_admin_user)):
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
async def cleanup_vector_base(request: CleanupVectorBaseRequest, current_user: dict = Depends(get_current_admin_user)):
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
async def reindex_vector_base(request: ReindexFileRequest, current_user: dict = Depends(get_current_admin_user)):
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


# ========== ROTAS ANÁLISE DE IMAGENS ==========

@app.post("/fish/images/upload", response_model=FishImageUploadResponse)
async def upload_fish_image(
    file: UploadFile = File(...),
    tag: str = Form(...),                              # 'lateral' | 'superior'
    fator_conversao: Optional[float] = Form(None),    # px/cm manual (opcional)
    current_user: dict = Depends(get_current_user),
):
    """Faz upload de uma imagem (lateral ou superior) para análise biométrica."""
    temp_path = None
    try:
        suffix = "." + (file.filename or "img.jpg").rsplit(".", 1)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        return fish_image_service.upload_image(
            file_path=temp_path,
            filename=file.filename or "imagem.jpg",
            tag=tag,
            user_id=current_user["id"],
            fator_conversao=fator_conversao,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("[upload_fish_image] erro")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.get("/fish/images", response_model=FishImageListResponse)
async def list_fish_images(
    tag: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Lista imagens do usuário autenticado com filtros opcionais."""
    try:
        return fish_image_service.list_images(
            user_id=current_user["id"],
            tag=tag,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        logger.exception("[list_fish_images] erro")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/fish/images/{image_id}", response_model=FishImageDeleteResponse)
async def delete_fish_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove uma imagem individual (Storage + banco)."""
    try:
        return fish_image_service.delete_image(image_id, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception("[delete_fish_image] erro")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fish/analyses/process", response_model=ProcessResponse)
async def process_fish_analysis(
    data: ProcessRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Processa o par de imagens (lateral + superior) e cria a análise.

    Etapas:
      1. Baixa cada imagem do Supabase Storage
      2. Detecta escala via ArUco (ou usa fator manual)
      3. Remove fundo com rembg
      4. Calcula bounding box e área da máscara
      5. Cria registro em fish_analyses com as métricas consolidadas
      6. Calcula Kvol se peso_g for informado
    """
    try:
        user_id = current_user["id"]
        warnings: list = []

        # ── 1. Processar imagem lateral ───────────────────────────────────────
        lat_result = fish_image_service.supabase.table("fish_images").select("*").eq("id", data.lateral_id).execute()
        if not lat_result.data:
            raise HTTPException(status_code=404, detail="Imagem lateral não encontrada")
        lat_row = lat_result.data[0]
        if lat_row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Sem permissão para esta imagem lateral")

        sup_result = fish_image_service.supabase.table("fish_images").select("*").eq("id", data.superior_id).execute()
        if not sup_result.data:
            raise HTTPException(status_code=404, detail="Imagem superior não encontrada")
        sup_row = sup_result.data[0]
        if sup_row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Sem permissão para esta imagem superior")

        # Atualiza status → processing
        for img_id in [data.lateral_id, data.superior_id]:
            fish_image_service.supabase.table("fish_images").update(
                {"processing_status": "processing"}
            ).eq("id", img_id).execute()

        # ── 2. Download + processamento ───────────────────────────────────────
        lat_bytes = fish_image_service.download_image_bytes(lat_row["storage_path"])
        lat_metrics = image_processing_service.process_image(lat_bytes, data.fator_lateral)
        warnings.extend(lat_metrics.pop("warnings", []))
        lat_viz_b64 = lat_metrics.pop("viz_b64", None)

        sup_bytes = fish_image_service.download_image_bytes(sup_row["storage_path"])
        sup_metrics = image_processing_service.process_image(sup_bytes, data.fator_superior)
        warnings.extend(sup_metrics.pop("warnings", []))
        sup_viz_b64 = sup_metrics.pop("viz_b64", None)

        # ── 3. Atualizar métricas em fish_images ──────────────────────────────
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        fish_image_service.supabase.table("fish_images").update({
            **{k: v for k, v in lat_metrics.items() if k != "fator_conversao"},
            "fator_conversao": lat_metrics.get("fator_conversao") or data.fator_lateral,
            "processing_status": "done",
            "processed_at": now,
        }).eq("id", data.lateral_id).execute()

        fish_image_service.supabase.table("fish_images").update({
            **{k: v for k, v in sup_metrics.items() if k != "fator_conversao"},
            "fator_conversao": sup_metrics.get("fator_conversao") or data.fator_superior,
            "processing_status": "done",
            "processed_at": now,
        }).eq("id", data.superior_id).execute()

        # ── 4. Dimensões consolidadas ─────────────────────────────────────────
        # Lateral: bbox_width=comprimento, bbox_height=altura
        # Superior: bbox_height=largura (dimensão perpendicular ao comprimento)
        comprimento_cm = lat_metrics.get("bbox_width_cm")
        altura_cm = lat_metrics.get("bbox_height_cm")
        largura_cm = sup_metrics.get("bbox_height_cm")

        # ── 5. Calcular Kvol ──────────────────────────────────────────────────
        kvol = None
        if (data.peso_g and comprimento_cm and altura_cm and largura_cm
                and comprimento_cm > 0 and altura_cm > 0 and largura_cm > 0):
            kvol = round(data.peso_g / (comprimento_cm * altura_cm * largura_cm), 6)

        # ── 6. Criar análise ──────────────────────────────────────────────────
        analysis_row = {
            "user_id": user_id,
            "peso_g": data.peso_g,
            "kvol": kvol,
            "comprimento_cm": comprimento_cm,
            "altura_cm": altura_cm,
            "largura_cm": largura_cm,
        }
        analysis_result = fish_image_service.supabase.table("fish_analyses").insert(analysis_row).execute()
        if not analysis_result.data:
            raise RuntimeError("Falha ao criar análise no banco")

        analysis_id = analysis_result.data[0]["id"]

        # Vincular imagens à análise
        for img_id in [data.lateral_id, data.superior_id]:
            fish_image_service.supabase.table("fish_images").update(
                {"analysis_id": analysis_id}
            ).eq("id", img_id).execute()

        if data.peso_g:
            for img_id in [data.lateral_id, data.superior_id]:
                fish_image_service.supabase.table("fish_images").update(
                    {"peso_g": data.peso_g}
                ).eq("id", img_id).execute()

        logger.info("[process] análise criada id=%s kvol=%s", analysis_id, kvol)

        return ProcessResponse(
            analysis_id=analysis_id,
            status="success",
            message="Análise concluída com sucesso",
            comprimento_cm=comprimento_cm,
            altura_cm=altura_cm,
            largura_cm=largura_cm,
            kvol=kvol,
            lateral_metrics=lat_metrics,
            superior_metrics=sup_metrics,
            lateral_viz_b64=lat_viz_b64,
            superior_viz_b64=sup_viz_b64,
            warnings=warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[process_fish_analysis] erro")
        # Marcar imagens como erro
        try:
            for img_id in [data.lateral_id, data.superior_id]:
                fish_image_service.supabase.table("fish_images").update(
                    {"processing_status": "error", "processing_error": str(e)}
                ).eq("id", img_id).execute()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fish/analyses", response_model=FishAnalysisListResponse)
async def list_fish_analyses(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    kvol_min: Optional[float] = None,
    kvol_max: Optional[float] = None,
    current_user: dict = Depends(get_current_user),
):
    """Lista análises do usuário autenticado com filtros opcionais."""
    try:
        return fish_image_service.list_analyses(
            user_id=current_user["id"],
            date_from=date_from,
            date_to=date_to,
            kvol_min=kvol_min,
            kvol_max=kvol_max,
        )
    except Exception as e:
        logger.exception("[list_fish_analyses] erro")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/fish/analyses/{analysis_id}", response_model=FishAnalysisDeleteResponse)
async def delete_fish_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove análise + imagens associadas (Storage + banco)."""
    try:
        return fish_image_service.delete_analysis(analysis_id, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception("[delete_fish_analysis] erro")
        raise HTTPException(status_code=500, detail=str(e))


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