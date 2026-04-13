# CAMINHO: backend/app/services/rag_service.py
# ARQUIVO: rag_service.py

import os
import logging
import tempfile
import uuid
from typing import List, Tuple, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RAGService')


class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
        self.llm = ChatOpenAI(model='gpt-4o', temperature=0)
        self.supabase = supabase
        self.storage_bucket = os.getenv('RAG_STORAGE_BUCKET', 'rag-documents')

    def _safe_filename(self, filename: str) -> str:
        # Remove caracteres especiais e limita o tamanho
        import re
        safe = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        return safe[:100]  # Limita a 100 caracteres

    def _build_storage_path(self, original_file_id: str, filename: str) -> str:
        # Monta o caminho no storage: original_file_id/safe_filename
        safe_name = self._safe_filename(filename)
        return f'{original_file_id}/{safe_name}'

    def _insert_ingestion_log(self, original_file_id: str, original_file_name: str, status: str,
                              requested_by: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        # Insere log na tabela rag_ingestion_logs
        payload = {
            'original_file_id': original_file_id,
            'original_file_name': original_file_name,
            'status': status,
            'requested_by': requested_by,
            'details': details or {}
        }
        self.supabase.table('rag_ingestion_logs').insert(payload).execute()

    def _update_ingestion_log(self, original_file_id: str, status: str,
                              details: Optional[Dict[str, Any]] = None) -> None:
        # Atualiza o log por original_file_id
        update_data = {'status': status}
        if details:
            update_data['details'] = details
        self.supabase.table('rag_ingestion_logs').update(update_data).eq('original_file_id', original_file_id).execute()

    def _upload_original_file(self, file_path: str, storage_path: str) -> None:
        # Lê os bytes do arquivo e faz upload para o storage
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        self.supabase.storage.from_(self.storage_bucket).upload(storage_path, file_bytes)

    def _download_original_file(self, storage_bucket: str, storage_path: str) -> bytes:
        # Baixa o arquivo do storage e retorna os bytes
        response = self.supabase.storage.from_(storage_bucket).download(storage_path)
        return response

    def _build_chunks(self, file_path: str):
        # Carrega o PDF e divide em chunks usando a estratégia atual
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=['\n\n', '\n', '.', ' ', ''],
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        return chunks

    async def _insert_document_chunk(self, chunk, chunk_index: int, filename: str, original_file_id: str,
                                     storage_bucket: str, storage_path: str) -> bool:
        # Gera embedding e insere o chunk na tabela documents
        try:
            embedding = await self.embeddings.aembed_query(chunk.page_content)
            payload = {
                'content': chunk.page_content,
                'metadata': {
                    'source': filename,
                    'chunk_index': chunk_index,
                    'page': chunk.metadata.get('page', 0),
                    'original_file_id': original_file_id,
                    'storage_bucket': storage_bucket,
                    'storage_path': storage_path
                },
                'embedding': embedding,
                'original_file_id': original_file_id,
                'original_file_name': filename,
                'storage_bucket': storage_bucket,
                'storage_path': storage_path,
                'deleted_at': None,
                'deleted_by': None,
                'deletion_reason': None
            }
            self.supabase.table('documents').insert(payload).execute()
            return True
        except Exception as e:
            logger.error(f'Erro ao inserir chunk {chunk_index}: {e}')
            return False

    async def _reingest_existing_file(self, file_path: str, filename: str, original_file_id: str, storage_bucket: str,
                                      storage_path: str, requested_by: Optional[str] = None) -> Dict[str, Any]:
        # Processa os chunks e insere na base
        chunks = self._build_chunks(file_path)
        chunks_criados = 0
        for i, chunk in enumerate(chunks):
            success = await self._insert_document_chunk(chunk, i, filename, original_file_id, storage_bucket,
                                                        storage_path)
            if success:
                chunks_criados += 1
        self._update_ingestion_log(original_file_id, 'completed', {'chunks_created': chunks_criados})
        return {
            'original_file_id': original_file_id,
            'filename': filename,
            'chunks_criados': chunks_criados,
            'storage_bucket': storage_bucket,
            'storage_path': storage_path
        }

    async def ingest_pdf(self, file_path: str, filename: str, uploaded_by: Optional[str] = None) -> Dict[str, Any]:
        # Gera ID único, faz upload e processa
        original_file_id = str(uuid.uuid4())
        storage_path = self._build_storage_path(original_file_id, filename)
        self._upload_original_file(file_path, storage_path)
        self._insert_ingestion_log(original_file_id, filename, 'started', uploaded_by)
        try:
            result = await self._reingest_existing_file(file_path, filename, original_file_id, self.storage_bucket,
                                                        storage_path, uploaded_by)
            return result
        except Exception as e:
            self._update_ingestion_log(original_file_id, 'failed', {'error': str(e)})
            raise e

    async def get_answer(self, question: str, chat_history: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        # Mantém o fluxo atual com melhorias no fallback
        try:
            question_embedding = await self.embeddings.aembed_query(question)
            # Tenta RPC
            try:
                rpc_result = self.supabase.rpc('match_documents', {
                    'query_embedding': question_embedding,
                    'match_count': 5,
                    'similarity_threshold': 0.5
                }).execute()
                docs = rpc_result.data or []
            except Exception:
                # Fallback: select com filtro
                response = self.supabase.table('documents').select('content, metadata, deleted_at').limit(20).execute()
                docs = [d for d in (response.data or []) if d.get('deleted_at') is None][:5]

            if not docs:
                return {'answer': 'Desculpe, não encontrei informações relevantes para responder à sua pergunta.',
                        'sources': []}

            # Monta contexto
            context = '\n'.join([doc['content'] for doc in docs])

            # Monta histórico (últimas 3 interações)
            history_text = ''
            if chat_history:
                recent_history = chat_history[-3:]
                history_text = '\n'.join([f'Usuário: {h[0]}\nAssistente: {h[1]}' for h in recent_history])

            # Prompt em português
            prompt_text = f"""
Você é um assistente especializado em consultoria para piscicultores. Responda de forma clara, objetiva e em português brasileiro.

Contexto dos documentos:
{context}

Histórico da conversa:
{history_text}

Pergunta: {question}

Resposta:"""

            response = await self.llm.ainvoke(prompt_text)
            answer = response.content if hasattr(response, 'content') else str(response)

            # Sources únicos sem duplicação
            sources = []
            seen = set()
            for doc in docs:
                source = doc['metadata'].get('source', '')
                if source and source not in seen:
                    sources.append(source)
                    seen.add(source)

            return {'answer': answer, 'sources': sources}
        except Exception as e:
            logger.error(f'Erro em get_answer: {e}')
            return {'answer': 'Ocorreu um erro interno. Tente novamente mais tarde.', 'sources': []}

    async def reindex_file_from_storage(self, original_file_id: str, original_file_name: str, storage_bucket: str,
                                        storage_path: str, requested_by: Optional[str] = None) -> Dict[str, Any]:
        # Baixa, apaga antigos e reindexa
        temp_file = None
        try:
            file_bytes = self._download_original_file(storage_bucket, storage_path)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(file_bytes)
            temp_file.close()

            # Apaga registros antigos
            self.supabase.table('documents').delete().eq('original_file_id', original_file_id).execute()
            self.supabase.table('rag_ingestion_logs').delete().eq('original_file_id', original_file_id).execute()

            # Reindexa
            result = await self._reingest_existing_file(temp_file.name, original_file_name, original_file_id,
                                                        storage_bucket, storage_path, requested_by)
            return result
        except Exception as e:
            logger.error(f'Erro em reindex_file_from_storage: {e}')
            raise e
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)


rag_service = RAGService()
