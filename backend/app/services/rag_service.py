import os
import logging
from typing import List, Tuple, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.chains import ConversationalRetrievalChain
from app.database import supabase

# Configuração de Logging para monitoramento no Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGService")


class RAGService:
    def __init__(self):
        """
        Inicializa os componentes de IA e a conexão com o banco vetorial.
        """
        # Embeddings: Transforma texto em vetores numéricos
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # LLM: O cérebro que gera as respostas (GPT-4o)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Vector Store: Conexão com a tabela 'documents' no Supabase
        self.vector_store = SupabaseVectorStore(
            client=supabase,
            embedding=self.embeddings,
            table_name="documents",
            query_name="match_documents",
        )

    async def ingest_pdf(self, file_path: str, filename: str) -> int:
        """
        Processa um PDF: Carrega -> Divide em Chunks -> Vetoriza -> Salva.
        """
        try:
            logger.info(f"Iniciando processamento do PDF: {filename}")

            # 1. Carregamento
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            # 2. Divisão em pedaços (Chunking)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)

            # 3. Adição de Metadados para rastreabilidade
            for chunk in chunks:
                chunk.metadata = {
                    "source": filename,
                    "type": "documentacao_tecnica"
                }

            # 4. Persistência no pgvector
            self.vector_store.add_documents(chunks)

            logger.info(f"Sucesso: {len(chunks)} chunks salvos para {filename}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Falha na ingestão do arquivo {filename}: {str(e)}")
            raise e

    async def get_answer(self, question: str, chat_history: List[Tuple[str, str]] = []) -> Dict[str, Any]:
        """
        Realiza a busca semântica e gera a resposta baseada no contexto.
        """
        try:
            logger.info(f"Processando pergunta: {question}")

            # Configura a Chain de Recuperação
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}),
                return_source_documents=True
            )

            # Executa a busca e geração
            result = chain.invoke({
                "question": question,
                "chat_history": chat_history
            })

            # Extrai as fontes únicas encontradas
            sources = list(set([
                doc.metadata.get("source", "Fonte desconhecida")
                for doc in result["source_documents"]
            ]))

            return {
                "answer": result["answer"],
                "sources": sources
            }

        except Exception as e:
            # ALTERAÇÃO PARA DEBUG: Retornando o erro real no corpo da resposta
            logger.error(f"CRITICAL ERROR no RAG: {str(e)}")
            return {
                "answer": f"Erro Técnico Detectado: {str(e)}",
                "sources": [],
                "debug_info": "Verifique a API Key da OpenAI ou a função match_documents no Supabase."
            }


# Instância Singleton
rag_service = RAGService()