# CAMINHO: backend/app/main.py
# ARQUIVO: main.py

import shutil
import logging
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.auth.auth_service import auth_service
from app.services.rag_service import rag_service
from app.dependencies import get_current_admin_user
from app.vector_admin_schemas import DeleteFileRequest, CleanupRequest, ReindexRequest
from app.services.vector_admin_service import vector_admin_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DrTilapiaAPI')
app = FastAPI(title='Dr. Tilápia 2.0 API', version='2.1.0')

# Configuração de CORS aberta
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    history: List[List[str]] = []

UPLOAD_DIR = Path('temp_uploads')
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get('/health')
async def health():
    return {'status': 'online', 'version': app.version}

@app.post('/auth/login')
async def login(data: LoginRequest):
    result = await auth_service.login(data.email, data.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='E-mail ou senha incorretos')
    return result

@app.post('/admin/upload')
async def upload_document(file: UploadFile = File(...), current_admin: dict = Depends(get_current_admin_user)):
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Apenas arquivos PDF são permitidos.')
    temp_file = UPLOAD_DIR / file.filename
    try:
        with open(temp_file, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        result = await rag_service.ingest_pdf(str(temp_file), file.filename, current_admin.get('id'))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro ao processar upload: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Erro ao processar upload: {str(e)}')
    finally:
        if temp_file.exists():
            temp_file.unlink()

@app.post('/consultoria/chat')
async def chat(data: ChatRequest):
    formatted_history = [tuple(h) for h in data.history]
    try:
        response = await rag_service.get_answer(data.message, formatted_history)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro interno: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Erro interno: {str(e)}')

@app.get('/admin/vector-base/files')
async def list_files(current_admin: dict = Depends(get_current_admin_user)):
    return vector_admin_service.list_files()

@app.get('/admin/vector-base/files/{original_file_id}')
async def get_file_detail(original_file_id: str, current_admin: dict = Depends(get_current_admin_user)):
    try:
        return vector_admin_service.get_file_detail(original_file_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Arquivo não encontrado')
    except Exception as e:
        logger.error(f'Erro interno do servidor: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno do servidor')

@app.post('/admin/vector-base/files/{original_file_id}/delete')
async def delete_file(original_file_id: str, body: DeleteFileRequest, current_admin: dict = Depends(get_current_admin_user)):
    if body.original_file_id != original_file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='O original_file_id do corpo deve ser igual ao da URL.')
    try:
        result = vector_admin_service.delete_by_file(
            original_file_id=original_file_id,
            deleted_by=current_admin.get('id'),
            hard_delete=body.hard_delete,
            reason=body.reason,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro interno do servidor: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno do servidor')

@app.post('/admin/vector-base/cleanup')
async def cleanup(body: CleanupRequest, current_admin: dict = Depends(get_current_admin_user)):
    try:
        result = vector_admin_service.cleanup_all(
            deleted_by=current_admin.get('id'),
            hard_delete=body.hard_delete,
            reason=body.reason,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro interno do servidor: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno do servidor')

@app.post('/admin/vector-base/reindex')
async def reindex(body: ReindexRequest, current_admin: dict = Depends(get_current_admin_user)):
    try:
        result = await vector_admin_service.reindex_files(
            original_file_ids=body.original_file_ids,
            requested_by=current_admin.get('id'),
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro interno do servidor: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno do servidor')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
