import os
import re
import time
import json
import hashlib
import logging
import httpx
from typing import TypedDict, Dict, Any, List, Literal, Optional, Tuple

logger = logging.getLogger(__name__)
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.document_loaders import PyPDFLoader
try:
    import pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False

try:
    import fitz as _fitz  # PyMuPDF — renderização de páginas para Vision OCR / Tesseract
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

try:
    import pytesseract as _pytesseract
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False

# Locais comuns do Tesseract no Windows
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\usuario\AppData\Local\Tesseract-OCR\tesseract.exe",
]
from langgraph.graph import StateGraph, END
from app.database import supabase_admin, _resolve_ssl_verify
from app.utils.pdf_cleaning import clean_loaded_pages, is_editorial_or_low_value, contains_scientific_signal
from app.utils.extraction_quality import assess_extraction, ExtractionQuality


# Limites do OCR por página (custo ~US$ 0,002-0,01/página no Vision).
# Sem teto, um PDF de centenas de páginas gera centenas de chamadas pagas.
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "40"))
OCR_PAGE_TIMEOUT_SECONDS = float(os.getenv("OCR_PAGE_TIMEOUT_SECONDS", "60"))


class ExtractionCostLimitExceeded(Exception):
    """OCR por página excederia o teto configurado.

    Levantada em vez de truncar: entregar um documento parcial rotulado como
    completo é o problema que a detecção de extração se propõe a evitar.
    """


class State(TypedDict):
    question: str
    context: str
    answer: str
    evaluation: str
    retry_count: int
    language: str
    history: List[List[str]]   # pares [pergunta_humano, resposta_ai]
    question_type: str         # quantitative | conceptual | comparative | methodological


class RAGService:
    def __init__(
            self,
            openai_api_key: str,
            supabase_url: str,
            supabase_key: str,
    ):
        # Verificação TLS por padrão; use SSL_CERT_FILE/REQUESTS_CA_BUNDLE para
        # apontar o CA bundle de um proxy corporativo de inspeção TLS, se necessário.
        _ssl_verify = _resolve_ssl_verify()
        _http_client = httpx.Client(verify=_ssl_verify)
        _http_async_client = httpx.AsyncClient(verify=_ssl_verify)

        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            http_client=_http_client,
            http_async_client=_http_async_client,
        )
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=openai_api_key,
            http_client=_http_client,
            http_async_client=_http_async_client,
        )
        # REFATORAÇÃO: Usar supabase_admin centralizado em vez de criar novo cliente
        self.supabase_admin = supabase_admin
        self.vectorstore = SupabaseVectorStore(
            client=self.supabase_admin,
            embedding=self.embeddings,
            table_name="documents"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=500,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.similarity_threshold = float(
            os.getenv("PRIMARY_RPC_SIMILARITY_THRESHOLD", "0.5")
        )
        logger.info("[RAGService] similarity_threshold=%.2f", self.similarity_threshold)
        self.graph = self._build_graph()

    # MÉTODO MODIFICADO: ingest_pdf com duplicação + validação (Etapa 1)
    async def ingest_pdf(self, file_path: str, original_filename: str) -> dict:
        """Ingestão de PDF com detecção de duplicação e validação de qualidade."""
        try:
            # Gerar original_file_id como MD5 do NOME do arquivo (não do caminho temp)
            original_file_id = hashlib.md5(original_filename.encode()).hexdigest()

            # Verificar se arquivo já foi ingestado
            if self._check_file_exists(original_file_id):
                return {
                    "status": "already_exists",
                    "message": "Arquivo já foi ingestado",
                    "original_file_id": original_file_id,
                    "original_file_name": original_filename,
                }

            # Carregar PDF percorrendo a cascata de extração até obter qualidade adequada
            try:
                raw_docs, extraction_method, quality = self._load_pdf_with_fallback(
                    file_path, original_filename
                )
            except ExtractionCostLimitExceeded as exc:
                return {
                    "status": "extraction_cost_limit",
                    "message": str(exc),
                    "original_file_id": original_file_id,
                    "original_file_name": original_filename,
                }

            # Extração inadequada é erro, não sucesso silencioso: nada é gravado.
            if not quality.adequate:
                logger.error(
                    "[ingest] '%s' rejeitado por qualidade de extração — %s",
                    original_filename, quality.reason,
                )
                return {
                    "status": "extraction_failed",
                    "message": (
                        f"A extração de texto deste PDF ficou incompleta e o documento "
                        f"não foi ingerido. Detalhe: {quality.reason}."
                    ),
                    "extraction_method": extraction_method,
                    "extraction_quality": quality.as_metadata(),
                    "original_file_id": original_file_id,
                    "original_file_name": original_filename,
                }

            # Validar qualidade do PDF antes de qualquer processamento
            if not self._validate_pdf_quality(raw_docs):
                return {
                    "status": "invalid_pdf",
                    "message": "PDF vazio ou corrompido",
                    "original_file_id": original_file_id,
                    "original_file_name": original_filename,
                }

            # Limpar páginas (remove ruído: números de página, copyright, linhas vazias)
            cleaned_docs = clean_loaded_pages(raw_docs)

            original_file_name = original_filename

            # Split em chunks com parâmetros otimizados para documentos científicos
            splits = self.text_splitter.split_documents(cleaned_docs)
            chunks_before_filter = len(splits)

            # Filtrar chunks de baixo valor
            splits = self._filter_chunks(splits)

            # Adicionar metadados normalizados ANTES de salvar.
            # `extraction_method` é gravado para TODOS os caminhos (inclusive o
            # pypdf primário), junto das métricas que justificaram o aceite —
            # sem isso é impossível distinguir depois, olhando só a base, um
            # documento bem extraído de um mal extraído.
            quality_metadata = quality.as_metadata()
            for split in splits:
                split.metadata['original_file_id'] = original_file_id
                split.metadata['original_file_name'] = original_file_name
                split.metadata['extraction_method'] = extraction_method
                split.metadata['extraction_quality'] = quality_metadata

            # Adicionar ao vectorstore
            self.vectorstore.add_documents(splits)

            return {
                "status": "success",
                "message": "PDF ingerido com sucesso",
                "chunks": len(splits),
                "chunks_before_filter": chunks_before_filter,
                "chunks_filtered_out": chunks_before_filter - len(splits),
                "pages_loaded": len(raw_docs),
                "extraction_method": extraction_method,
                "extraction_quality": quality_metadata,
                "file_path": file_path,
                "original_file_id": original_file_id,
                "original_file_name": original_file_name,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "file_path": file_path,
            }

    # NOVO MÉTODO: Verificação de duplicação
    def _check_file_exists(self, original_file_id: str) -> bool:
        """Verifica se original_file_id já existe em public.documents.

        Usa filtro JSONB (metadata->>original_file_id) porque a coluna
        original_file_id não é populada pelo SupabaseVectorStore do LangChain.
        O operador ->> extrai o valor como texto e faz comparação simples (eq),
        mais confiável que .contains() para JSONB no supabase-py.
        """
        try:
            response = (
                self.supabase_admin.table("documents")
                .select("id")
                .filter("metadata->>original_file_id", "eq", original_file_id)
                .limit(1)
                .execute()
            )
            found = len(response.data) > 0
            logger.info(
                "[_check_file_exists] original_file_id=%s → found=%s",
                original_file_id, found,
            )
            return found
        except Exception as e:
            logger.error(
                "[_check_file_exists] ERRO ao verificar duplicata: %s",
                e, exc_info=True,
            )
            return False

    def _accept_extraction(self, docs: List[Document], method: str) -> Optional[ExtractionQuality]:
        """Decide se a extração de um estágio é aceitável.

        Combina os dois critérios: encoding quebrado (`_is_text_garbled`, que
        cobre mojibake) e extração incompleta (`assess_extraction`, que cobre
        estrutura sem conteúdo). Retorna a qualidade se aceitável, senão None.
        """
        if not docs:
            return None
        combined = " ".join(d.page_content for d in docs)
        if self._is_text_garbled(combined):
            logger.warning("[ingest] %s: texto com encoding quebrado", method)
            return None
        quality = assess_extraction([d.page_content for d in docs])
        if not quality.adequate:
            logger.warning("[ingest] %s: extração incompleta — %s", method, quality.reason)
            return None
        return quality

    def _load_pdf_with_fallback(
        self, file_path: str, original_filename: str
    ) -> Tuple[List[Document], str, ExtractionQuality]:
        """Carrega PDF com cadeia de fallbacks progressivos:
        1. PyPDFLoader  (rápido, sem custo)
        2. pdfplumber   (melhor para alguns encodings e layouts)
        3. Tesseract OCR
        4. Vision OCR   (GPT-4o-mini + PyMuPDF — último recurso, com custo por página)

        Cada estágio é aceito apenas se a extração for adequada — não basta ter
        texto, é preciso ter conteúdo. Retorna (documentos, método, qualidade).
        Quando nenhum estágio produz qualidade adequada, devolve a melhor
        tentativa com `quality.adequate == False`, para o chamador falhar
        explicitamente em vez de gravar conteúdo inútil.
        """
        # ── 1. PyPDFLoader ────────────────────────────────────────────────────
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        for doc in raw_docs:
            doc.metadata['source'] = original_filename

        quality = self._accept_extraction(raw_docs, "pypdf")
        if quality:
            logger.info("[ingest] pypdf OK — %.0f palavras/página", quality.mean_words_per_page)
            return raw_docs, "pypdf", quality

        # ── 2. pdfplumber ─────────────────────────────────────────────────────
        if _PDFPLUMBER_AVAILABLE:
            try:
                import pdfplumber
                plumber_docs: List[Document] = []
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        plumber_docs.append(Document(
                            page_content=text,
                            metadata={"source": original_filename, "page": page_num},
                        ))
                quality = self._accept_extraction(plumber_docs, "pdfplumber")
                if quality:
                    logger.info("[ingest] pdfplumber OK — %.0f palavras/página",
                                quality.mean_words_per_page)
                    return plumber_docs, "pdfplumber", quality
            except Exception as exc:
                logger.warning("[ingest] pdfplumber falhou (%s)", exc)

        # ── 3. Tesseract OCR via PyMuPDF + pytesseract ───────────────────────
        if _PYMUPDF_AVAILABLE and _PYTESSERACT_AVAILABLE:
            try:
                tesseract_docs = self._extract_text_via_tesseract(file_path, original_filename)
                quality = self._accept_extraction(tesseract_docs, "tesseract_ocr")
                if quality:
                    logger.info("[ingest] Tesseract OCR OK — %.0f palavras/página",
                                quality.mean_words_per_page)
                    return tesseract_docs, "tesseract_ocr", quality
            except Exception as exc:
                logger.warning("[ingest] Tesseract OCR falhou (%s)", exc)
        else:
            # Sem Tesseract a cascata pula direto para o Vision, que custa por
            # página — vale deixar registrado por que o custo subiu.
            logger.warning(
                "[ingest] Tesseract indisponível (pymupdf=%s, pytesseract=%s) — "
                "cascata seguirá para Vision OCR, que tem custo por página",
                _PYMUPDF_AVAILABLE, _PYTESSERACT_AVAILABLE,
            )

        # ── 4. Vision OCR via GPT-4o-mini + PyMuPDF (último recurso) ─────────
        if _PYMUPDF_AVAILABLE:
            try:
                vision_docs = self._extract_text_via_vision(file_path, original_filename)
                quality = self._accept_extraction(vision_docs, "vision_ocr")
                if quality:
                    logger.info("[ingest] Vision OCR OK — %.0f palavras/página",
                                quality.mean_words_per_page)
                    return vision_docs, "vision_ocr", quality
            except ExtractionCostLimitExceeded:
                raise
            except Exception as exc:
                logger.error("[ingest] Vision OCR falhou (%s)", exc)

        # Nenhum estágio produziu qualidade adequada. Devolve a primeira
        # tentativa com o veredito negativo — o chamador deve falhar, não gravar.
        final_quality = assess_extraction([d.page_content for d in raw_docs])
        logger.error("[ingest] cascata esgotada sem qualidade adequada — %s", final_quality.reason)
        return raw_docs, "pypdf", final_quality

    def _extract_text_via_tesseract(self, file_path: str, original_filename: str) -> List[Document]:
        """Extrai texto via Tesseract OCR (PyMuPDF renderiza → PIL → pytesseract).

        Requer Tesseract instalado no sistema.
        Usa idiomas 'por+eng' (português + inglês) para cobrir artigos bilíngues.
        """
        import io
        import fitz as pymupdf
        import pytesseract
        from PIL import Image

        # Configurar path do Tesseract se não estiver no PATH
        if not pytesseract.pytesseract.tesseract_cmd or pytesseract.pytesseract.tesseract_cmd == "tesseract":
            for path in _TESSERACT_PATHS:
                import os
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info("[tesseract] Encontrado em: %s", path)
                    break

        docs: List[Document] = []
        pdf = pymupdf.open(file_path)
        total = len(pdf)
        logger.info("[tesseract] iniciando OCR de %d páginas: %s", total, original_filename)

        for page_num, page in enumerate(pdf):
            mat = pymupdf.Matrix(2.5, 2.5)  # ~180 DPI — bom para OCR
            pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                text = pytesseract.image_to_string(img, lang="por+eng")
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "source": original_filename,
                            "page": page_num,
                            "extraction_method": "tesseract_ocr",
                        },
                    ))
                    logger.info("[tesseract] página %d/%d: %d chars", page_num + 1, total, len(text))
            except Exception as exc:
                logger.warning("[tesseract] página %d falhou: %s", page_num, exc)

        pdf.close()
        return docs

    def _extract_text_via_vision(self, file_path: str, original_filename: str) -> List[Document]:
        """Extrai texto de PDF via GPT Vision (PyMuPDF renderiza páginas → base64 → OpenAI).

        Funciona mesmo em PDFs com fontes customizadas onde todo extrator de texto falha.
        Custo: ~$0.002–0.01 por página (gpt-4o-mini com detail=high).
        """
        import base64
        import fitz as pymupdf

        prompt_text = (
            "You are a scientific document transcription tool. "
            "Extract ALL text from this page EXACTLY as it appears. "
            "Include: all numbers, table values, column headers, row labels, "
            "statistical notation (±, p-values, %, n=, confidence intervals), "
            "and all body paragraphs. "
            "For tables: preserve structure using | to separate columns, one row per line. "
            "Example table row: 'T1 (100%) | 45.2 ± 3.1 | 312.5 | 1.82 | 98.3'. "
            "Do NOT summarize, skip values, or add commentary. "
            "Transcribe every character you see."
        )

        docs: List[Document] = []
        pdf = pymupdf.open(file_path)
        total_pages = len(pdf)

        # Teto de custo: cada página é uma chamada de API paga. Ultrapassar o
        # limite falha explicitamente — processar só as N primeiras entregaria
        # um documento parcial rotulado como completo.
        if total_pages > OCR_MAX_PAGES:
            pdf.close()
            raise ExtractionCostLimitExceeded(
                f"O documento tem {total_pages} páginas e exigiria OCR por página, "
                f"acima do limite configurado de {OCR_MAX_PAGES} (OCR_MAX_PAGES). "
                f"Nenhuma página foi processada."
            )

        logger.info("[vision_ocr] iniciando OCR de %d páginas: %s", total_pages, original_filename)

        for page_num, page in enumerate(pdf):
            # Renderizar em ~150 DPI (fator 2.08) — equilibra qualidade e tamanho
            mat = pymupdf.Matrix(2.08, 2.08)
            pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()

            try:
                message = HumanMessage(content=[
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ])
                # Timeout por página: sem ele, uma chamada travada bloqueia a
                # ingestão inteira indefinidamente.
                resp = self.llm.invoke([message], timeout=OCR_PAGE_TIMEOUT_SECONDS)
                extracted = resp.content.strip()
                if extracted:
                    docs.append(Document(
                        page_content=extracted,
                        metadata={
                            "source": original_filename,
                            "page": page_num,
                            "extraction_method": "vision_ocr",
                        },
                    ))
                logger.info("[vision_ocr] página %d/%d: %d chars", page_num + 1, total_pages, len(extracted))
            except Exception as exc:
                logger.warning("[vision_ocr] página %d falhou: %s", page_num, exc)

        pdf.close()
        return docs

    def _validate_pdf_quality(self, docs: List[Document]) -> bool:
        """Valida se o PDF extraído tem conteúdo utilizável.

        O critério de densidade fica em `assess_extraction`, aplicado durante a
        cascata em `_load_pdf_with_fallback` — aqui resta apenas a checagem
        estrutural de que existe documento e texto. Manter as duas separadas
        evita avaliar a mesma coisa duas vezes com limiares divergentes.
        """
        if not docs:
            return False
        total_chars = sum(len(doc.page_content) for doc in docs)
        return total_chars > 50

    def _filter_chunks(self, docs: List[Document]) -> List[Document]:
        """Remove chunks muito curtos ou sem valor científico."""
        filtered = []
        for doc in docs:
            content = doc.page_content.strip()
            if not content or len(content) < 120:
                continue
            if is_editorial_or_low_value(content) and not contains_scientific_signal(content):
                continue
            filtered.append(doc)
        return filtered

    def get_answer(self, question: str, history: Optional[List[List[str]]] = None) -> str:
        """Ponto de entrada: invoca grafo com pergunta, histórico e tipo detectado."""
        lang = self._detect_question_language(question)
        question_type = self._detect_question_type(question)
        logger.info("[get_answer] lang=%s question_type=%s pergunta='%s...'",
                    lang, question_type, question[:60])
        input_state = {
            "question": question,
            "context": "",
            "answer": "",
            "evaluation": "",
            "retry_count": 0,
            "language": lang,
            "history": history or [],
            "question_type": question_type,
        }
        t0 = time.perf_counter()
        result = self.graph.invoke(input_state)
        elapsed = time.perf_counter() - t0

        logger.info(
            "[metrics] type=%-14s lang=%-5s retries=%d answer_len=%4d eval=%-12s time=%.2fs",
            question_type,
            lang,
            result.get("retry_count", 0),
            len(result.get("answer", "")),
            result.get("evaluation", "?"),
            elapsed,
        )
        return result["answer"]

    def _build_graph(self) -> Any:
        """Grafo com retrieve -> generate -> evaluate -> (conditional retry ou END)."""
        workflow = StateGraph(State)

        def retrieve(state: State) -> Dict[str, Any]:
            """Nó: recupera docs e monta context.

            Para perguntas conceptuais, adiciona data companions (chunks mais
            ricos em dados do mesmo arquivo) para garantir que tabelas e métricas
            específicas estejam presentes no contexto mesmo sem alta similaridade semântica.
            """
            docs = self._retrieve_docs_via_rpc(state["question"], k=20)
            question_type = state.get("question_type", "conceptual")
            if question_type in ("conceptual", "quantitative"):
                docs = self._add_data_companion_chunks(docs, max_companions=5)
            context = "\n\n".join(doc.page_content for doc in docs)
            return {"context": context}

        def generate(state: State) -> Dict[str, str]:
            """Nó: gera resposta com prompt adaptado ao tipo de pergunta."""
            lang = state["language"]
            history = state.get("history", [])
            question_type = state.get("question_type", "conceptual")

            # Se o tipo é quantitativo mas o contexto é pobre/garbled,
            # usa template conceptual para evitar resposta toda vazia
            effective_type = question_type
            if question_type == "quantitative" and self._is_context_poor(state.get("context", "")):
                effective_type = "conceptual"
                logger.info("[generate] contexto pobre — degradando quantitative→conceptual")

            lang_instruction = (
                "Responda COMPLETAMENTE em português (pt-BR)."
                if lang == "pt-BR"
                else "Respond COMPLETELY in English."
            )

            system_content = self._build_system_prompt(effective_type, lang_instruction)

            # Montar lista de mensagens: system + histórico + pergunta atual com contexto
            messages = [SystemMessage(content=system_content)]

            for pair in history:
                if len(pair) >= 1 and pair[0]:
                    messages.append(HumanMessage(content=pair[0]))
                if len(pair) >= 2 and pair[1]:
                    messages.append(AIMessage(content=pair[1]))

            current_message = (
                f"**CONTEXT:**\n{state['context']}\n\n"
                f"**QUESTION:** {state['question']}"
            )
            messages.append(HumanMessage(content=current_message))

            response = self.llm.invoke(messages)
            return {"answer": response.content}

        def evaluate(state: State) -> Dict[str, str]:
            """Nó: avalia qualidade da resposta por tipo de pergunta + verificações de conteúdo."""
            answer = state["answer"]
            question = state["question"]
            question_type = state.get("question_type", "conceptual")

            # ── Verificações universais ────────────────────────────────────────
            has_content = len(answer.strip()) > 150
            is_relevant = self._is_answer_relevant(question, answer)
            too_many_empty = self._count_empty_sections(answer) >= 3

            # Falha imediata se resposta é irrelevante ou quase vazia
            if too_many_empty or not is_relevant or not has_content:
                reason = (
                    "muitas seções vazias" if too_many_empty
                    else "sem relevância" if not is_relevant
                    else "conteúdo insuficiente"
                )
                logger.info(
                    "[evaluate] LOW_QUALITY (%s) type=%s len=%d",
                    reason, question_type, len(answer),
                )
                return {"evaluation": "LOW_QUALITY"}

            # ── Verificações por tipo ──────────────────────────────────────────
            if question_type == "conceptual":
                quality = "HIGH_QUALITY"

            elif question_type == "comparative":
                has_comparison = "COMPARISON:" in answer
                has_differences = "KEY DIFFERENCES:" in answer or "DIFFERENCES:" in answer
                quality = "HIGH_QUALITY" if (has_comparison and has_differences) else "LOW_QUALITY"

            elif question_type == "methodological":
                has_design = "EXPERIMENTAL DESIGN:" in answer or "DESIGN:" in answer
                has_procedures = "PROCEDURES:" in answer or "PROCEDURE:" in answer
                quality = "HIGH_QUALITY" if (has_design and has_procedures) else "LOW_QUALITY"

            else:  # quantitative
                has_real_data = self._data_section_has_numbers(answer)
                sections_ok = sum(
                    1 for s in ["DATA:", "METHODOLOGY:", "INTERPRETATION:"]
                    if s in answer and "Empty section" not in answer.split(s)[1].split("\n")[0]
                )
                quality = "HIGH_QUALITY" if (has_real_data and sections_ok >= 2) else "LOW_QUALITY"

            logger.info(
                "[evaluate] question_type=%s quality=%s len=%d",
                question_type, quality, len(answer),
            )
            return {"evaluation": quality}

        def should_retry(state: State) -> Literal["generate", "end"]:
            """Condicional: retry ou END."""
            if state["evaluation"] == "LOW_QUALITY" and state["retry_count"] < 2:
                return "retrieve_retry"
            else:
                return "end"

        def retrieve_retry(state: State) -> Dict[str, Any]:
            """Nó: retry com estratégia diferente por tentativa.

            Retry 1: remove threshold de similaridade → abre o funil, k=30.
            Retry 2: expande a query com termos bilíngues + sem threshold, k=30.
            """
            retry_count = state["retry_count"]
            question = state["question"]

            if retry_count == 0:
                # Retry 1: remove threshold, mantém LLM expansion (já fez no retrieve inicial,
                # mas aqui é nova chamada sem cache — roda LLM de novo intencionalmente)
                logger.info("[retrieve_retry] tentativa=1 — removendo threshold, k=30")
                docs = self._retrieve_docs_via_rpc(
                    question, k=30, skip_threshold=True, use_llm_expansion=True
                )
            else:
                # Retry 2: expansão por regras bilíngues + sem threshold (diferente da LLM)
                expanded = self._expand_query_for_retry(question)
                logger.info("[retrieve_retry] tentativa=2 — expansão por regras, k=30")
                docs = self._retrieve_docs_via_rpc(
                    expanded, k=30, skip_threshold=True, use_llm_expansion=False
                )

            context = "\n\n".join(doc.page_content for doc in docs)
            return {"context": context, "retry_count": retry_count + 1}

        workflow.add_node("retrieve", retrieve)
        workflow.add_node("generate", generate)
        workflow.add_node("evaluate", evaluate)
        workflow.add_node("retrieve_retry", retrieve_retry)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            should_retry,
            {
                "retrieve_retry": "retrieve_retry",
                "end": END,
            },
        )
        workflow.add_edge("retrieve_retry", "generate")
        return workflow.compile()

    def _embed_query(self, text: str) -> List[float]:
        """Gera embedding da query."""
        return self.embeddings.embed_query(text)

    def _search_rpc(self, query_vector: List[float], limit: int = 20) -> List[Dict[str, Any]]:
        """Busca via RPC no Supabase."""
        response = self.supabase_admin.rpc(
            "rpc_vector_search",
            {"query_vector": query_vector, "limit_count": limit},
        ).execute()
        return response.data or []

    def _normalize_match_doc(self, match: Dict[str, Any]) -> Document:
        """Normaliza resultado RPC em Document."""
        metadata_raw = match.get("metadata")
        if isinstance(metadata_raw, dict):
            metadata = dict(metadata_raw)
        elif isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw) if metadata_raw else {}
        elif metadata_raw is None:
            metadata = {}
        else:
            metadata = {}
        metadata["db_id"] = match["id"]
        metadata["similarity"] = match["similarity"]
        return Document(
            page_content=match["content"],
            metadata=metadata,
        )

    def _make_retrieval_dedup_key(self, doc: Document) -> str:
        """Gera chave para deduplicação."""
        db_id = doc.metadata.get("db_id")
        if db_id is not None:
            return f"db_id:{db_id}"
        source = doc.metadata.get("source", "")
        page = doc.metadata.get("page", "")
        strong_key = f"{source}:{page}".strip()
        if strong_key:
            return f"meta:{hashlib.sha256(strong_key.encode('utf-8')).hexdigest()[:12]}"
        content_hash = hashlib.sha256(doc.page_content.encode('utf-8')).hexdigest()[:20]
        return f"content:{content_hash}"

    def _detect_question_language(self, question: str) -> str:
        """Detecção de idioma: pt-BR ou en."""
        q_lower = question.lower()
        pt_words = {'como', 'qual', 'quais', 'não', 'tilápia', 'restrição', 'alimentar', 'viveiro', 'crescimento',
                    'alevinos', 'qual', 'o que', 'por que'}
        en_words = {'what', 'how', 'which', 'feed', 'restriction', 'restricted', 'diet', 'under', 'growth',
                    'fingerlings', 'why', 'describe'}
        pt_accents = any(c in 'áéíóúãõçÁÉÍÓÚÃÕÇ' for c in question)
        pt_score = sum(1 for w in pt_words if w in q_lower) + (2 if pt_accents else 0)
        en_score = sum(1 for w in en_words if w in q_lower)
        return 'pt-BR' if pt_score >= en_score else 'en'

    def _detect_question_type(self, question: str) -> str:
        """Detecta o tipo da pergunta para selecionar o prompt adequado.

        Retorna: 'quantitative' | 'conceptual' | 'comparative' | 'methodological'

        Quantitativo exige indicadores numéricos EXPLÍCITOS — nunca é o default.
        Default seguro = conceptual.
        """
        q_lower = question.lower()

        # Indicadores positivos de pergunta quantitativa: pede valor/medida específica
        quantitative = {
            'quanto pesa', 'quanto pesam', 'quanto foi', 'quanto cresceu', 'quanto mede',
            'qual o valor', 'qual foi o valor', 'qual a taxa', 'qual foi a taxa',
            'qual o percentual', 'qual a porcentagem', 'qual o índice',
            'qual o ganho de peso', 'qual foi o ganho', 'qual a média', 'qual o fcr',
            'qual a conversão alimentar', 'qual a sobrevivência', 'qual foi a sobrevivência',
            'qual a biomassa', 'qual o peso final', 'qual o comprimento',
            'quantos gramas', 'quantos cm', 'quantos dias', 'quantas semanas',
            'how much', 'how many', 'what is the rate', 'what is the value',
            'what percentage', 'what was the growth', 'what were the values',
            'survival rate', 'feed conversion ratio', 'specific growth rate',
        }

        conceptual = {
            'o que é', 'o que são', 'como funciona', 'como funcionam', 'explique',
            'defina', 'definição', 'por que', 'porque', 'o que significa',
            'descreva', 'qual a importância', 'qual é a importância',
            # consequências / efeitos / impactos → sempre conceptual
            'consequencia', 'consequências', 'consequência', 'consequencias',
            'efeito', 'efeitos', 'impacto', 'impactos',
            'benefício', 'benefícios', 'vantagem', 'vantagens',
            'desvantagem', 'desvantagens',
            # verbos de causa-efeito (ex: "O que acarreta a restrição alimentar?")
            'acarreta', 'acarretam', 'provoca', 'provocam', 'causa ', 'causam',
            'implica', 'implicam', 'resulta', 'resultam', 'ocorre', 'acontece',
            'leva a', 'levam a', 'afeta', 'afetam', 'influencia', 'influenciam',
            'prejudica', 'prejudicam', 'interfere', 'interferecem',
            # padrão inglês
            'what is a ', 'what is an ', 'what are', 'how does', 'how do', 'explain',
            'define', 'definition', 'why', 'what does', 'describe',
            'consequences', 'effects', 'impacts', 'benefits', 'advantages',
        }
        comparative = {
            'compare', 'comparação', 'diferença', 'diferenças', 'melhor que',
            'pior que', 'versus', ' vs ', 'entre os', 'entre as', 'comparar',
            'qual é melhor', 'comparison', 'difference', 'differences',
            'better than', 'worse than', 'between', 'which is better',
        }
        methodological = {
            'metodologia', 'método', 'métodos', 'delineamento', 'procedimento',
            'protocolo', 'como foi conduzido', 'como foi realizado', 'como foi feito',
            'materiais e métodos', 'methodology', 'method', 'methods', 'procedure',
            'experimental design', 'protocol', 'how was conducted', 'how was performed',
            'materials and methods',
        }

        quantitative_score = sum(1 for t in quantitative if t in q_lower)
        conceptual_score = sum(1 for t in conceptual if t in q_lower)
        comparative_score = sum(1 for t in comparative if t in q_lower)
        methodological_score = sum(1 for t in methodological if t in q_lower)

        # "o que" no início = pedido de explicação/definição → bônus conceptual
        if q_lower.startswith('o que ') or q_lower.startswith('quais '):
            conceptual_score += 1

        # Tipos de domínio específicos primeiro
        if comparative_score > 0 and comparative_score >= methodological_score:
            return 'comparative'
        if methodological_score > 0:
            return 'methodological'

        # Quantitativo só vence se tiver indicador EXPLÍCITO e nenhum conceptual
        if quantitative_score > 0 and quantitative_score > conceptual_score:
            return 'quantitative'

        # Qualquer sinal conceptual → conceptual (inclui "o que acarreta", "o que provoca", etc.)
        if conceptual_score > 0:
            return 'conceptual'

        # Default seguro: conceptual — o template é flexível e não exige seções rígidas
        return 'conceptual'

    def _build_system_prompt(self, question_type: str, lang_instruction: str) -> str:
        """Retorna o system prompt adequado ao tipo de pergunta."""

        if question_type == 'conceptual':
            return (
                f"You are an expert in tilapia aquaculture and fisheries science. {lang_instruction}\n\n"
                f"Your task: Answer the question using ONLY the scientific context provided, "
                f"with maximum fidelity to the original data.\n\n"
                f"MANDATORY RESPONSE STRUCTURE:\n\n"
                f"**Dados do Estudo:**\n"
                f"List ALL numeric values found in the context relevant to the question. "
                f"Format as a bullet table: '• [Variable] ([Population/Treatment]): [Value] ([unit/stat])'. "
                f"Examples:\n"
                f"  • Coeficiente de endogamia FIS (SAW): 0.44 — mais alto do estudo\n"
                f"  • Coeficiente de endogamia FIS (ILH): 0.05 — mais baixo do estudo\n"
                f"  • Distância genética DEST: 0.00–0.818 (variação entre pares)\n"
                f"  • Área de filé por ultrassom (ILH/GIFT): 7.05 vs SAL: 3.04\n"
                f"If no numeric data is found in the context: write 'Dados numéricos não disponíveis no contexto.'\n\n"
                f"**Interpretação:**\n"
                f"Explain what the data means, using the populations/treatments by name. "
                f"Connect each numeric finding to its biological or practical significance as stated "
                f"in the study. Do not extrapolate beyond what the authors conclude.\n\n"
                f"**Implicações / Recomendações:**\n"
                f"List only conclusions and recommendations explicitly stated in the context.\n\n"
                f"GROUNDING RULES (mandatory):\n"
                f"  • Every claim in Interpretação must link to a value in Dados do Estudo\n"
                f"  • Name populations/stocks individually — never write 'algumas populações'\n"
                f"  • Do NOT add general aquaculture knowledge not in the context\n"
                f"  • Prefer 'O estudo encontrou X=Y' over 'X é geralmente importante para Y'\n"
                f"  • If context is insufficient for a section, say so explicitly"
            )

        if question_type == 'comparative':
            return (
                f"You are an expert in tilapia aquaculture research. {lang_instruction}\n\n"
                f"Your task: Compare and contrast based on the context provided.\n\n"
                f"Use these exact section headers:\n\n"
                f"COMPARISON:\n"
                f"- Side-by-side comparison with numeric values where available\n"
                f"- Organize by treatment groups, methods, or conditions\n\n"
                f"KEY DIFFERENCES:\n"
                f"- Main differences with supporting data (values, %, p-values)\n\n"
                f"CONCLUSION:\n"
                f"- Which performs better and under what conditions\n"
                f"- Practical recommendation if applicable\n\n"
                f"Include all available numeric values. Be objective and data-driven."
            )

        if question_type == 'methodological':
            return (
                f"You are an expert in tilapia aquaculture research. {lang_instruction}\n\n"
                f"Your task: Describe the experimental methodology based on the context.\n\n"
                f"Use these exact section headers:\n\n"
                f"EXPERIMENTAL DESIGN:\n"
                f"- Design type, treatments, groups, replication (n=)\n\n"
                f"PROCEDURES:\n"
                f"- Step-by-step methods, feeding protocols, duration\n\n"
                f"MEASUREMENTS:\n"
                f"- Variables measured, frequency, instruments\n\n"
                f"STATISTICAL ANALYSIS:\n"
                f"- Statistical tests, significance level, software used\n\n"
                f"Include specific values wherever available. Write 'Not described.' if a section has no information."
            )

        # default: quantitative
        return (
            f"You are an expert in tilapia aquaculture research, specialized in extracting "
            f"quantitative data from scientific documents. {lang_instruction}\n\n"
            f"Your task: Extract ALL numeric data from the context and answer with precise values.\n\n"
            f"Use these exact section headers:\n\n"
            f"DATA:\n"
            f"- All relevant numeric values paired with their meaning\n"
            f"- Reconstruct tables (pair headers with values)\n"
            f"- Include: n=, ±, %, p-values, confidence intervals\n"
            f"- Example: 'Weight gain: 45.2 ± 3.1 g (n=50, p<0.05)'\n"
            f"- If no data found: 'Empty section.'\n\n"
            f"METHODOLOGY:\n"
            f"- Experimental design, sample size, duration, treatment groups, statistical methods\n"
            f"- If not found: 'Empty section.'\n\n"
            f"INTERPRETATION:\n"
            f"- What the results mean; link numbers to biological/practical significance\n"
            f"- If not found: 'Empty section.'\n\n"
            f"LIMITATIONS:\n"
            f"- Study limitations mentioned in the text\n"
            f"- If not found: 'Empty section.'\n\n"
            f"RULES: Never write section headers without content. "
            f"Pair all numbers with their labels. Scan every line for digits. "
            f"CRITICAL: when a section has no data in the context, write EXACTLY 'Empty section.' "
            f"(do not translate or rephrase — this exact string is required for quality control)."
        )

    def _rewrite_query(self, question: str, lang: str) -> str:
        """Reescrita bilíngue da query."""
        q_lower = question.lower()
        rewritten = question
        if lang == 'pt-BR' and 'tilápia' in q_lower and 'nilo' in q_lower:
            rewritten += ' Oreochromis niloticus'
        elif lang == 'en' and ('oreochromis' in q_lower or 'niloticus' in q_lower):
            rewritten += ' tilápia do nilo'
        restriction_terms = [
            'restrição alimentar',
            'dieta restrita',
            'restrição dieta',
            'feed restriction',
            'restricted diet',
        ]
        if any(term in q_lower for term in restriction_terms):
            if lang == 'pt-BR':
                rewritten += ' feed restriction'
            elif lang == 'en':
                rewritten += ' restrição alimentar'
        if lang == 'pt-BR' and 'metabolismo' in q_lower:
            rewritten += ' metabolism'
        elif lang == 'en' and 'metabolism' in q_lower:
            rewritten += ' metabolismo'
        return rewritten.strip()

    def _expand_query_with_llm(self, question: str, lang: str) -> str:
        """Usa o LLM para expandir a query com sinônimos e termos bilíngues científicos.

        Faz uma chamada barata ao GPT-4o-mini. Em caso de falha, faz fallback para
        a reescrita por regras (_rewrite_query).
        """
        try:
            prompt = (
                f"You are a search query optimizer for scientific literature on tilapia aquaculture.\n\n"
                f"Original question: {question}\n"
                f"Language: {lang}\n\n"
                f"Return ONLY the original question followed by 4-6 relevant scientific synonyms "
                f"and bilingual equivalents (Portuguese and English) that improve document retrieval. "
                f"Do not add explanations or punctuation between terms. "
                f"Keep the original question first.\n\n"
                f"Example:\n"
                f"Input: 'Qual o ganho de peso de tilápias com restrição alimentar?'\n"
                f"Output: 'Qual o ganho de peso de tilápias com restrição alimentar? "
                f"weight gain feed restriction Oreochromis niloticus compensatory growth "
                f"crescimento compensatório desempenho zootécnico'"
            )
            response = self.llm.invoke([HumanMessage(content=prompt)])
            expanded = response.content.strip()
            # Validação mínima: resposta maior que a pergunta e contém termos da pergunta
            q_start = question[:20].lower()
            if len(expanded) > len(question) and q_start in expanded.lower():
                logger.info("[expand_query] '%s...' → '%s...'", question[:40], expanded[len(question):60])
                return expanded
            logger.warning("[expand_query] resposta LLM inválida — usando reescrita local")
        except Exception as exc:
            logger.warning("[expand_query] falha LLM (%s) — usando reescrita local", exc)
        return self._rewrite_query(question, lang)

    # ── Auxiliares de avaliação de qualidade ──────────────────────────────────

    def _is_answer_relevant(self, question: str, answer: str) -> bool:
        """Verifica se ao menos um termo significativo da pergunta aparece na resposta.

        Normaliza acentos antes de comparar para evitar falsos negativos em pt-BR:
        ex.: "indice" (pergunta sem acento) deve bater em "índice" (resposta com acento).
        """
        import unicodedata

        def _norm(s: str) -> str:
            """Remove diacríticos e converte para ASCII minúsculo."""
            return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').lower()

        stopwords = {
            'o', 'a', 'os', 'as', 'um', 'uma', 'de', 'da', 'do', 'em', 'para',
            'com', 'por', 'que', 'foi', 'the', 'an', 'of', 'in', 'for', 'is',
            'are', 'was', 'what', 'how', 'which', 'qual', 'como', 'quais',
        }
        words = [
            w.lower().strip('?.,!():')
            for w in question.split()
            if len(w) > 4 and w.lower().strip('?.,!():') not in stopwords
        ]
        if not words:
            return True
        answer_normalized = _norm(answer)
        return any(_norm(w) in answer_normalized for w in words)

    def _data_section_has_numbers(self, answer: str) -> bool:
        """Verifica se a seção DATA contém números reais (não só o cabeçalho)."""
        if "DATA:" not in answer:
            return False
        data_start = answer.index("DATA:") + len("DATA:")
        data_end = len(answer)
        for section in ["METHODOLOGY:", "INTERPRETATION:", "LIMITATIONS:"]:
            idx = answer.find(section, data_start)
            if idx != -1 and idx < data_end:
                data_end = idx
        data_content = answer[data_start:data_end]
        return (
            bool(re.search(r'\d', data_content))
            and "Empty section" not in data_content
        )

    def _count_empty_sections(self, answer: str) -> int:
        """Conta ocorrências de 'Empty section' — penaliza respostas ocas."""
        return answer.count("Empty section")

    # ── Auxiliar de retry ──────────────────────────────────────────────────────

    def _expand_query_for_retry(self, question: str) -> str:
        """Expande a query para o 2º retry: aplica reescrita bilíngue e adiciona
        termos gerais de aquicultura de tilápia caso ainda não estejam presentes."""
        lang = self._detect_question_language(question)
        expanded = self._rewrite_query(question, lang)
        q_lower = expanded.lower()
        if 'tilápia' not in q_lower and 'tilapia' not in q_lower:
            expanded += ' tilapia tilápia'
        if 'oreochromis' not in q_lower:
            expanded += ' Oreochromis niloticus'
        logger.info("[retry] query expandida: %s", expanded)
        return expanded.strip()

    def _get_rerank_terms(self, question: str, rewritten_question: str) -> List[str]:
        """Extrai termos para reranking."""
        q_lower = question.lower()
        rw_lower = rewritten_question.lower()
        terms = set()
        tilapia_terms = {'tilápia', 'nilo', 'oreochromis', 'niloticus'}
        if any(t in q_lower or t in rw_lower for t in tilapia_terms):
            terms.update(tilapia_terms)
        restriction_terms = {'restrição', 'alimentar', 'dieta', 'restrita', 'feed', 'restriction'}
        if any(t in q_lower or t in rw_lower for t in restriction_terms):
            terms.update(restriction_terms)
        metab_terms = {'metabolismo', 'metabolism'}
        if any(t in q_lower or t in rw_lower for t in metab_terms):
            terms.update(metab_terms)
        return list(terms)

    def _score_doc_bonus(self, doc: Document, terms: List[str]) -> float:
        """Bônus lexical para reranking."""
        doc_lower = doc.page_content.lower()
        matches = sum(1 for term in terms if term in doc_lower)
        return matches * 0.02

    def _rerank_docs(self, docs: List[Document], question: str, rewritten_question: str) -> List[Document]:
        """Reranking leve pós-dedup."""
        terms = self._get_rerank_terms(question, rewritten_question)

        def rerank_key(d: Document) -> float:
            sim = d.metadata.get("similarity", 0.0)
            bonus = self._score_doc_bonus(d, terms)
            return sim + bonus

        return sorted(docs, key=rerank_key, reverse=True)

    def _is_text_garbled(self, text: str, threshold: float = 0.04) -> bool:
        """Detecta texto com problema de encoding: muitos '?' indicam caracteres não decodificados."""
        if not text or len(text) < 50:
            return True
        ratio = text.count('?') / len(text)
        return ratio > threshold

    def _is_context_poor(self, context: str) -> bool:
        """Retorna True se o contexto recuperado é insuficiente para resposta quantitativa."""
        if not context or len(context.strip()) < 200:
            return True
        return self._is_text_garbled(context)

    def _add_data_companion_chunks(
        self,
        docs: List[Document],
        max_companions: int = 5,
    ) -> List[Document]:
        """Injeta os chunks mais ricos em dados do mesmo arquivo que ficaram fora da busca semântica.

        Para perguntas conceptuais/implicações, a busca semântica retorna os chunks de
        discussão/conclusão com alta similaridade, mas esses chunks não contêm as tabelas
        e métricas (FIS, DEST, p-values) que suportam as afirmações. Este método adiciona
        os N chunks com maior densidade numérica de cada arquivo já presente no contexto.
        """
        present_ids = {d.metadata.get("db_id") for d in docs}
        file_ids = {
            d.metadata.get("original_file_id")
            for d in docs
            if d.metadata.get("original_file_id")
        }
        if not file_ids:
            return docs

        companions: List[Document] = []
        for file_id in file_ids:
            try:
                resp = (
                    self.supabase_admin.table("documents")
                    .select("id, content, metadata")
                    .filter("metadata->>original_file_id", "eq", file_id)
                    .execute()
                )
                # Ordenar por densidade de dígitos — chunks de tabelas têm muitos números
                def digit_density(row: Dict[str, Any]) -> float:
                    c = row.get("content", "")
                    return sum(1 for ch in c if ch.isdigit()) / max(len(c), 1)

                sorted_rows = sorted(resp.data, key=digit_density, reverse=True)
                added = 0
                for row in sorted_rows:
                    if added >= max_companions:
                        break
                    db_id = row["id"]
                    if db_id in present_ids:
                        continue
                    meta = dict(row.get("metadata") or {})
                    meta["db_id"] = db_id
                    meta["similarity"] = 0.0   # não veio da busca semântica
                    meta["companion"] = True
                    companions.append(Document(page_content=row["content"], metadata=meta))
                    present_ids.add(db_id)
                    added += 1
            except Exception as exc:
                logger.warning("[data_companion] falha ao buscar chunks de %s: %s", file_id, exc)

        if companions:
            logger.info("[data_companion] adicionando %d chunks de dados ao contexto", len(companions))
        return docs + companions

    def _retrieve_docs_via_rpc(
        self,
        question: str,
        k: int = 20,
        skip_threshold: bool = False,
        use_llm_expansion: bool = True,
    ) -> List[Document]:
        """Recuperação via RPC com k variável.

        Args:
            skip_threshold:    se True, ignora o filtro de similaridade (retries).
            use_llm_expansion: se True, usa LLM para expandir a query (recuperação inicial).
                               Retries usam expansão por regras para evitar dupla chamada.
        """
        lang = self._detect_question_language(question)
        if use_llm_expansion:
            rewritten_question = self._expand_query_with_llm(question, lang)
        else:
            rewritten_question = self._rewrite_query(question, lang)
        query_vector = self._embed_query(rewritten_question)
        matches = self._search_rpc(query_vector, k)
        docs = [self._normalize_match_doc(m) for m in matches]
        seen: Dict[str, Document] = {}
        for doc in docs:
            key = self._make_retrieval_dedup_key(doc)
            current_sim = doc.metadata.get("similarity", 0)
            if key not in seen or current_sim > seen[key].metadata.get("similarity", 0):
                seen[key] = doc
        deduped = sorted(
            seen.values(),
            key=lambda d: d.metadata.get("similarity", 0),
            reverse=True,
        )
        deduped = self._rerank_docs(deduped, question, rewritten_question)

        if skip_threshold:
            logger.info("[retrieve] threshold ignorado (retry) — %d docs", len(deduped))
        else:
            above = [d for d in deduped if d.metadata.get("similarity", 0) >= self.similarity_threshold]
            if above:
                logger.info(
                    "[retrieve] %d/%d docs acima do threshold %.2f (scores: %.3f–%.3f)",
                    len(above), len(deduped),
                    self.similarity_threshold,
                    above[-1].metadata.get("similarity", 0),
                    above[0].metadata.get("similarity", 0),
                )
                deduped = above
            else:
                logger.warning(
                    "[retrieve] Nenhum doc acima do threshold %.2f — fallback top-1 (score=%.3f)",
                    self.similarity_threshold,
                    deduped[0].metadata.get("similarity", 0) if deduped else 0,
                )
                deduped = deduped[:1]

        return deduped[:k]


_rag_service_instance = None


def get_rag_service():
    """Get or create RAG service instance lazily."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        _SUPABASE_URL = os.getenv("SUPABASE_URL")
        _SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not _OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it before using RAG service."
            )
        if not _SUPABASE_URL:
            raise ValueError(
                "SUPABASE_URL environment variable is not set. "
                "Please set it before using RAG service."
            )
        if not _SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY environment variable is not set. "
                "Please set it before using RAG service."
            )
        _rag_service_instance = RAGService(_OPENAI_API_KEY, _SUPABASE_URL, _SUPABASE_KEY)
    return _rag_service_instance


class _RagServiceProxy:
    """Proxy that lazily instantiates rag_service on first access"""

    def __getattr__(self, name):
        return getattr(get_rag_service(), name)


rag_service = _RagServiceProxy()