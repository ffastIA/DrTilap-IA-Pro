import os
import logging
from typing import List, Tuple, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import supabase

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGService")


class RAGService:
    def __init__(self):
        """
        Inicializa os componentes de IA e conexão com Supabase (sem SupabaseVectorStore).
        """
        try:
            # Embeddings: Transforma texto em vetores numéricos
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

            # LLM: O cérebro que gera as respostas (GPT-4o)
            self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

            # Supabase client (direto, sem SupabaseVectorStore)
            self.supabase = supabase

            logger.info("✅ RAGService inicializado com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar RAGService: {str(e)}")
            raise

    async def ingest_pdf(self, file_path: str, filename: str) -> int:
        """
        Processa um PDF: Carrega -> Divide em Chunks -> Vetoriza -> Salva no Supabase.
        """
        try:
            logger.info(f"📄 Iniciando processamento do PDF: {filename}")

            # 1. Carregamento
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            logger.info(f"   ✓ Carregadas {len(documents)} páginas")

            # 2. Divisão em pedaços (Chunking)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " ", ""],
                length_function=len,
            )
            chunks = text_splitter.split_documents(documents)
            logger.info(f"   ✓ Dividido em {len(chunks)} chunks")

            # 3. Gerar embeddings e persistir no Supabase
            saved_count = 0
            for i, chunk in enumerate(chunks):
                try:
                    # Gerar embedding para este chunk
                    embedding_response = await self.embeddings.aembed_query(chunk.page_content)

                    # Preparar dados para inserção
                    document_data = {
                        "content": chunk.page_content,
                        "metadata": {
                            "source": filename,
                            "chunk_index": i,
                            "page": chunk.metadata.get("page", 0),
                        },
                        "embedding": embedding_response,  # pgvector vai armazenar automaticamente
                    }

                    # Inserir no Supabase
                    response = self.supabase.table("documents").insert(document_data).execute()

                    if response.data:
                        saved_count += 1
                        if (i + 1) % 10 == 0:
                            logger.info(f"   ✓ {i + 1}/{len(chunks)} chunks salvos")

                except Exception as chunk_error:
                    logger.warning(f"   ⚠️ Erro ao salvar chunk {i}: {str(chunk_error)}")
                    continue

            logger.info(f"✅ Sucesso: {saved_count}/{len(chunks)} chunks salvos para {filename}")
            return saved_count

        except Exception as e:
            logger.error(f"❌ Falha na ingestão do arquivo {filename}: {str(e)}")
            raise

    async def get_answer(
            self, question: str, chat_history: List[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Realiza busca semântica e gera resposta.
        Solução alternativa: busca SQL com match_documents RPC no Supabase.
        """
        try:
            if chat_history is None:
                chat_history = []

            logger.info(f"🔍 Processando pergunta: {question}")

            # 1. Gerar embedding da pergunta
            logger.info("   Gerando embedding da pergunta...")
            question_embedding = await self.embeddings.aembed_query(question)
            logger.info("   ✓ Embedding gerado")

            # 2. Buscar documentos relevantes usando match_documents RPC
            logger.info("   Buscando documentos relevantes via RPC...")
            try:
                # Chamar a função RPC match_documents no Supabase
                result = self.supabase.rpc(
                    "match_documents",
                    {
                        "query_embedding": question_embedding,
                        "match_count": 5,
                        "similarity_threshold": 0.5,
                    }
                ).execute()

                relevant_docs = result.data if result.data else []
                logger.info(f"   ✓ Encontrados {len(relevant_docs)} documentos relevantes")

            except Exception as rpc_error:
                logger.warning(f"   ⚠️ Erro ao chamar RPC: {str(rpc_error)}")
                # Fallback: busca SQL simples (sem similaridade)
                logger.info("   Fazendo fallback para busca SQL simples...")
                relevant_docs = self.supabase.table("documents").select(
                    "content, metadata"
                ).limit(5).execute().data
                logger.info(f"   ✓ {len(relevant_docs)} documentos recuperados (modo fallback)")

            if not relevant_docs:
                logger.warning("   Nenhum documento relevante encontrado")
                return {
                    "answer": "Desculpe, não encontrei documentos relevantes para sua pergunta na base de conhecimento. Tente fazer upload de mais documentos ou reformule sua pergunta.",
                    "sources": [],
                }

            # 3. Formatar contexto
            context = "\n\n".join([
                f"---\nFonte: {doc.get('metadata', {}).get('source', 'Desconhecido')}\n{doc.get('content', '')}"
                for doc in relevant_docs
            ])

            # 4. Construir histórico
            history_text = ""
            if chat_history:
                history_text = "Histórico da conversa:\n"
                for user_msg, ai_msg in chat_history[-3:]:
                    history_text += f"Usuário: {user_msg}\nAssistente: {ai_msg}\n\n"

            # 5. Construir prompt
            prompt_text = f"""Você é um especialista em piscicultura tecnológica e aquacultura.

{history_text}

Contexto de documentos técnicos:
{context}

Pergunta do usuário: {question}

Instruções:
- Responda APENAS com base nos documentos fornecidos
- Seja conciso, prático e objetivo
- Se a pergunta não estiver nos documentos, diga: "Não encontrei informação específica sobre isso nos manuais disponíveis"
- Cite a fonte quando relevante

Resposta:"""

            logger.info("   Gerando resposta com LLM...")

            # 6. Invocar LLM
            response = await self.llm.ainvoke(prompt_text)
            answer = response.content if hasattr(response, 'content') else str(response)

            # 7. Extrair fontes
            sources = list(set([
                doc.get("metadata", {}).get("source", "Fonte desconhecida")
                for doc in relevant_docs
            ]))

            logger.info(f"✅ Resposta gerada. Fontes: {sources}")

            return {
                "answer": answer,
                "sources": sources,
            }

        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR no RAG: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            return {
                "answer": f"Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.",
                "sources": [],
            }


# Instância Singleton
rag_service = RAGService()