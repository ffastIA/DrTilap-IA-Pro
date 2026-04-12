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

# Configuração simples de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        return safe[:255]  # Limita a 255 caracteres

    def _build_storage_path(self, original_file_id: str, filename: str) -> str:
        # Constrói o caminho no storage
        safe_filename = self._safe_filename(filename)
        return f"{original_file_id}/{safe_filename}"

    def _insert_ingestion_log(self, original_file_id: str, original_file_name: str, status: str, requested_by: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        # Insere log de ingestão
        payload = {
            'original_file_id': original_file_id,
            'original_file_name': original_file_name,
            'status': status,
            'requested_by': requested_by,
            'details': details or {}
        }
        try:
            self.supabase.table('rag_ingestion_logs').insert(payload).execute()
        except Exception as e:
            logger.error(f"Erro ao inserir log de ingestão: {e}")

    def _update_ingestion_log(self, original_file_id: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        # Atualiza log de ingestão
        update_data = {'status': status}
        if details:
            update_data['details'] = details
        try:
            self.supabase.table('rag_ingestion_logs').update(update_data).eq('original_file_id', original_file_id).execute()
        except Exception as e:
            logger.error(f"Erro ao atualizar log de ingestão: {e}")

    def _upload_original_file(self, file_path: str, storage_path: str) -> None:
        # Faz upload do arquivo para o storage
        with open(file_path, 'rb') as f:
            file_data = f.read()
        try:
            self.supabase.storage.from_(self.storage_bucket).upload(storage_path, file_data)
        except Exception as e:
            logger.error(f"Erro ao fazer upload do arquivo: {e}")
            raise

    def _download_original_file(self, storage_bucket: str, storage_path: str) -> bytes:
        # Baixa o arquivo do storage
        try:
            response = self.supabase.storage.from_(storage_bucket).download(storage_path)
            return response
        except Exception as e:
            logger.error(f"Erro ao baixar arquivo do storage: {e}")
            raise

    def _build_chunks(self, file_path: str):
        # Carrega e divide o PDF em chunks
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        return chunks

    async def _insert_document_chunk(self, chunk, chunk_index: int, filename: str, original_file_id: str, storage_bucket: str, storage_path: str) -> bool:
        # Insere um chunk na tabela documents
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
            logger.error(f"Erro ao inserir chunk {chunk_index}: {e}")
            return False

    async def _reingest_existing_file(self, file_path: str, filename: str, original_file_id: str, storage_bucket: str, storage_path: str, requested_by: Optional[str] = None) -> Dict[str, Any]:
        # Reingesta um arquivo existente
        chunks = self._build_chunks(file_path)
        chunks_criados = 0
        for i, chunk in enumerate(chunks):
            success = await self._insert_document_chunk(chunk, i, filename, original_file_id, storage_bucket, storage_path)
            if success:
                chunks_criados += 1
        self._update_ingestion_log(original_file_id, 'completed', {'chunks_criados': chunks_criados})
        return {
            'original_file_id': original_file_id,
            'filename': filename,
            'chunks_criados': chunks_criados,
            'storage_bucket': storage_bucket,
            'storage_path': storage_path
        }

    async def ingest_pdf(self, file_path: str, filename: str, uploaded_by: Optional[str] = None) -> Dict[str, Any]:
        # Ingestão completa de um PDF
        original_file_id = str(uuid.uuid4())
        storage_path = self._build_storage_path(original_file_id, filename)
        try:
            self._upload_original_file(file_path, storage_path)
            self._insert_ingestion_log(original_file_id, filename, 'started', uploaded_by)
            result = await self._reingest_existing_file(file_path, filename, original_file_id, self.storage_bucket, storage_path, uploaded_by)
            return result
        except Exception as e:
            self._update_ingestion_log(original_file_id, 'failed', {'error': str(e)})
            raise

    async def get_answer(self, question: str, chat_history: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        # Gera resposta baseada na pergunta
        try:
            query_embedding = await self.embeddings.aembed_query(question)
            # Tenta RPC match_documents
            try:
                response = self.supabase.rpc('match_documents', {
                    'query_embedding': query_embedding,
                    'match_count': 5,
                    'similarity_threshold': 0.5
                }).execute()
                docs = response.data
            except Exception:
                # Fallback
                response = self.supabase.table('documents').select('content, metadata, deleted_at').limit(20).execute()
                docs = [d for d in response.data if d['deleted_at'] is None][:5]
            if not docs:
                return {
                    'answer': 'Desculpe, não encontrei informações relevantes para responder à sua pergunta.',
                    'sources': []
                }
            # Monta contexto
            context = "\n".join([f"Fonte: {doc['metadata']['source']} (Página {doc['metadata']['page']})\n{doc['content']}" for doc in docs])
            # Histórico
            history_text = ""
            if chat_history:
                history_text = "\n".join([f"Usuário: {q}\nAssistente: {a}" for q, a in chat_history])
            # Prompt
            prompt = f"""Você é um assistente especializado em consultoria para o projeto DrTilápia. Responda de forma clara, objetiva e baseada apenas nas informações fornecidas no contexto.

Histórico da conversa:
{history_text}

Contexto relevante:
{context}

Pergunta: {question}

Resposta:"""
            answer = await self.llm.ainvoke(prompt)
            sources = [{
                'source': doc['metadata']['source'],
                'page': doc['metadata']['page'],
                'chunk_index': doc['metadata']['chunk_index']
            } for doc in docs]
            return {
                'answer': answer.content,
                'sources': sources
            }
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            return {
                'answer': 'Ocorreu um erro interno. Tente novamente mais tarde.',
                'sources': []
            }

    async def reindex_file_from_storage(self, original_file_id: str, original_file_name: str, storage_bucket: str, storage_path: str, requested_by: Optional[str] = None) -> Dict[str, Any]:
        # Reindexa arquivo a partir do storage
        try:
            file_bytes = self._download_original_file(storage_bucket, storage_path)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name
            # Apaga registros atuais
            self.supabase.table('documents').delete().eq('original_file_id', original_file_id).execute()
            self.supabase.table('rag_ingestion_logs').delete().eq('original_file_id', original_file_id).execute()
            # Reingesta
            result = await self._reingest_existing_file(temp_file_path, original_file_name, original_file_id, storage_bucket, storage_path, requested_by)
            # Remove arquivo temporário
            os.unlink(temp_file_path)
            return result
        except Exception as e:
            logger.error(f"Erro na reindexação: {e}")
            raise

# Instância singleton
rag_service = RAGService()
