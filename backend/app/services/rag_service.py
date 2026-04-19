# CAMINHO: backend/app/services/rag_service.py

import uuid
import logging
from pathlib import Path
from tempfile import gettempdir
from typing import List, Tuple, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import supabase_admin


class RAGService:
    """
    Serviço para processamento de documentos PDF usando RAG (Retrieval-Augmented Generation).
    """

    def __init__(self):
        """
        Inicializa o serviço RAG com embeddings, LLM e conexão com Supabase.
        """
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.supabase = supabase_admin
        self.storage_bucket = "rag-documents"
        self.embedding_batch_size = 20
        self.insert_batch_size = 20

    async def ingest_pdf(self, file_path: str, filename: str, original_file_id: Optional[str] = None, cleanup_existing: bool = False) -> Dict[str, Any]:
        """
        Ingere um PDF, processa em chunks, gera embeddings e armazena no Supabase.

        Args:
            file_path: Caminho local do arquivo PDF.
            filename: Nome do arquivo.
            original_file_id: ID único do arquivo (gerado se não informado).
            cleanup_existing: Se True, remove chunks existentes para o original_file_id.

        Returns:
            Dicionário com informações do processamento.
        """
        if not original_file_id:
            original_file_id = str(uuid.uuid4())

        logging.info(f"Iniciando ingestão do PDF: {filename} com ID {original_file_id}")

        # Carregar o PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # Dividir em chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)

        # Upload do PDF original para o storage
        storage_path = f"uploads/{original_file_id}/{filename}"
        with open(file_path, "rb") as f:
            self.supabase.storage.from_(self.storage_bucket).upload(storage_path, f)

        # Limpar chunks existentes se solicitado
        if cleanup_existing:
            await self._delete_existing_document_chunks(original_file_id)

        # Montar payloads
        payloads = self._build_chunk_payloads(chunks, original_file_id, filename, self.storage_bucket, storage_path)

        # Gerar embeddings em lotes
        await self._generate_embeddings_in_payloads(payloads)

        # Inserir na tabela em lotes
        await self._insert_payload_batches(payloads)

        logging.info(f"Ingestão concluída para {filename}")
        return {
            "message": "PDF ingerido com sucesso",
            "original_file_id": original_file_id,
            "original_file_name": filename,
            "chunks_criados": len(chunks),
            "storage_bucket": self.storage_bucket,
            "storage_path": storage_path
        }

    async def get_answer(self, question: str, chat_history: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Gera uma resposta para a pergunta usando RAG.

        Args:
            question: Pergunta do usuário.
            chat_history: Histórico do chat.

        Returns:
            Dicionário com resposta e fontes.
        """
        logging.info(f"Gerando resposta para pergunta: {question}")

        # Gerar embedding da pergunta
        query_embedding = self.embeddings.embed_query(question)

        # Buscar documentos similares via RPC
        response = self.supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_count": 5,
            "similarity_threshold": 0.7
        }).execute()

        docs = response.data if response.data else []
        docs = [self._normalize_match_doc(doc) for doc in docs if doc]

        # Fallback se não houver conteúdo suficiente
        if not docs or not any(self._safe_content(doc) for doc in docs):
            logging.warning("RPC não retornou conteúdo suficiente, usando fallback")
            docs = await self._fetch_document_chunks_by_original_file_id(None)  # Ajustar se necessário

        # Montar contexto
        context = self._build_context_from_docs(docs)

        # Gerar resposta com LLM
        prompt = f"Histórico: {chat_history}\nContexto: {context}\nPergunta: {question}\nResponda baseado no contexto."
        answer = self.llm.invoke(prompt).content

        sources = [{
            "original_file_name": doc.get("original_file_name", ""),
            "page": self._safe_page_from_metadata(doc.get("metadata", {})),
            "content": self._safe_content(doc)
        } for doc in docs]

        return {
            "answer": answer,
            "sources": sources
        }

    async def reindex_file_from_storage(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reindexa um arquivo do storage.

        Args:
            file_info: Dicionário com storage_bucket, storage_path, original_file_name.

        Returns:
            Resultado da reingestão.
        """
        storage_bucket = file_info["storage_bucket"]
        storage_path = file_info["storage_path"]
        original_file_name = file_info["original_file_name"]
        original_file_id = file_info.get("original_file_id")

        logging.info(f"Reindexando arquivo: {original_file_name}")

        # Baixar para temporário
        temp_dir = gettempdir()
        temp_path = Path(temp_dir) / f"temp_{uuid.uuid4()}.pdf"
        with open(temp_path, "wb") as f:
            res = self.supabase.storage.from_(storage_bucket).download(storage_path)
            f.write(res)

        # Reingerir
        result = await self.ingest_pdf(str(temp_path), original_file_name, original_file_id, cleanup_existing=True)

        # Limpar temporário
        temp_path.unlink()

        return result

    def _build_chunk_payloads(self, chunks, original_file_id, original_file_name, storage_bucket, storage_path):
        """
        Monta payloads para os chunks.
        """
        payloads = []
        for chunk in chunks:
            payloads.append({
                "content": chunk.page_content,
                "metadata": chunk.metadata,
                "original_file_id": original_file_id,
                "original_file_name": original_file_name,
                "storage_bucket": storage_bucket,
                "storage_path": storage_path
            })
        return payloads

    def _chunk_list(self, lst, n):
        """
        Divide uma lista em chunks de tamanho n.
        """
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    async def _generate_embeddings_in_payloads(self, payloads):
        """
        Gera embeddings para os payloads em lotes.
        """
        for batch in self._chunk_list(payloads, self.embedding_batch_size):
            contents = [p["content"] for p in batch]
            embeddings = self.embeddings.embed_documents(contents)
            for p, emb in zip(batch, embeddings):
                p["embedding"] = emb

    async def _insert_payload_batches(self, payloads):
        """
        Insere payloads na tabela em lotes.
        """
        for batch in self._chunk_list(payloads, self.insert_batch_size):
            self.supabase.table("documents").insert(batch).execute()

    async def _fetch_document_chunks_by_original_file_id(self, original_file_id):
        """
        Busca chunks por original_file_id.
        """
        response = self.supabase.table("documents").select("*").eq("original_file_id", original_file_id).execute()
        return response.data

    def _normalize_match_doc(self, doc):
        """
        Normaliza documento retornado pela RPC.
        """
        return doc

    def _build_context_from_docs(self, docs):
        """
        Monta contexto a partir dos documentos.
        """
        context = ""
        for doc in docs:
            context += f"Arquivo: {doc.get('original_file_name', '')}, Página: {self._safe_page_from_metadata(doc.get('metadata', {}))}, Conteúdo: {self._safe_content(doc)}\n"
        return context

    async def _delete_existing_document_chunks(self, original_file_id):
        """
        Remove chunks existentes para o original_file_id.
        """
        self.supabase.table("documents").delete().eq("original_file_id", original_file_id).execute()

    def _safe_page_from_metadata(self, metadata):
        """
        Extrai página de forma segura.
        """
        return metadata.get("page", 0)

    def _safe_content(self, doc):
        """
        Extrai conteúdo de forma segura.
        """
        return doc.get("content", "")


# Exportar instância do serviço
rag_service = RAGService()