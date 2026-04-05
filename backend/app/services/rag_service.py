import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from backend.app.database import supabase

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        # Carregar .env com caminho absoluto baseado na raiz do projeto (backend/)
        backend_root = Path(__file__).parent.parent.parent  # backend/app/services -> backend/
        env_path = backend_root / '.env'
        load_dotenv(dotenv_path=env_path)

        # Verificação robusta da API Key
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY não encontrada no arquivo .env. Verifique o caminho absoluto e a presença da variável.")

        try:
            # Configurar ChatOpenAI
            self.llm = ChatOpenAI(model="gpt-5-nano", temperature=0, openai_api_key=self.openai_api_key)

            # Configurar SupabaseVectorStore
            self.vectorstore = SupabaseVectorStore(
                client=supabase,
                table_name="documents",
                embedding=None,  # Assumindo que embeddings são gerenciados externamente ou via pgvector
                query_name="match_documents"
            )

            # Configurar ConversationalRetrievalChain
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(),
                return_source_documents=True
            )

            logger.info("RAGService inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar RAGService: {str(e)}")
            raise

    def query(self, question: str, user_id: str, chat_history: list = None):
        """
        Realiza uma consulta com contexto filtrado por user_id.
        """
        if chat_history is None:
            chat_history = []

        try:
            # Filtrar documentos por user_id nos metadados
            retriever = self.vectorstore.as_retriever(
                search_kwargs={"filter": {"metadata->>user_id": user_id}}
            )

            # Atualizar a chain com o retriever filtrado
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                return_source_documents=True
            )

            result = qa_chain({"question": question, "chat_history": chat_history})
            logger.info(f"Consulta realizada com sucesso para user_id: {user_id}")
            return result
        except Exception as e:
            logger.error(f"Erro na consulta para user_id {user_id}: {str(e)}")
            raise