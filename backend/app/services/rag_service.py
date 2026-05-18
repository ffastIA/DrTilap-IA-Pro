import os
import json
import hashlib
from typing import TypedDict, Dict, Any, List
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import supabase


class State(TypedDict):
    question: str
    context: str
    answer: str


class RAGService:
    def __init__(
            self,
            openai_api_key: str,
            supabase_url: str,
            supabase_key: str,
    ):
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=openai_api_key,
        )
        self.supabase_admin = supabase.create_client(supabase_url, supabase_key)
        self.vectorstore = SupabaseVectorStore(
            client=self.supabase_admin,
            embedding=self.embeddings,
            table_name="documents"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        self.graph = self._build_graph()

    def ingest_pdf(self, file_path: str) -> None:
        """Ingestão de PDF mantida inalterada."""
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        splits = self.text_splitter.split_documents(docs)
        self.vectorstore.add_documents(splits)

    def get_answer(self, question: str) -> str:
        """Ponto de entrada: invoca grafo com pergunta."""
        input_state = {"question": question}
        result = self.graph.invoke(input_state)
        return result["answer"]

    def _build_graph(self) -> Any:
        """Grafo com retrieve -> generate."""
        workflow = StateGraph(State)

        def retrieve(state: State) -> Dict[str, str]:
            """Nó: recupera docs e monta context."""
            docs = self._retrieve_docs_via_rpc(state["question"], k=20)
            context = "\n\n".join(doc.page_content for doc in docs)
            return {"context": context}

        def generate(state: State) -> Dict[str, str]:
            """Nó: gera resposta com prompt AGRESSIVO para números."""
            prompt = ChatPromptTemplate.from_template(
                """You are an expert extracting NUMBERS and VALUES from scientific documents. Extract DATA with ACTUAL NUMERIC VALUES paired with headers.

**MISSION:** Extract DATA, METHODOLOGY, INTERPRETATION, LIMITATIONS.

**RULES:**

1. RETURN FORMAT (4 SECTIONS - EXACTLY THIS):

DATA:
[numbers, values, tables with actual data]

METHODOLOGY:
[procedures, methods]

INTERPRETATION:
[discussion, conclusions]

LIMITATIONS:
[limitations mentioned]

   - No intro/outro. No 'ERROR' or 'No data'. Use 'Empty section.' only if truly empty.

2. **AGGRESSIVE NUMBER EXTRACTION:**
   - NUMBERS: 0-9, decimals (45.2), ranges, percentages (90%), ± (45.2 ± 3.1), p-values (p<0.001), n=values (n=50).
   - **PAIR WITH HEADERS**: "Weight gain (g)" → find "45.2" → "Weight gain: 45.2 g"
   - **SCAN ALL LINES**: headers, parentheses (value ± error), commas, any line with digits 0-9

3. **TABLE RECONSTRUCTION:**
   - If header and data are separate lines, PAIR them:
     "Weight gain (g) | FCR | Survival (%)" + "45.2 | 2.1 | 95" → 
     Weight gain: 45.2 g, FCR: 2.1, Survival: 95%

4. **DATA SECTION FORMAT:**
   - "Table [X]:" with all columns and numeric values
   - Include n=, p=, confidence intervals if present
   - EXAMPLE:
     Table 1: Zootechnical Performance
     Weight gain: 45.2 ± 3.1 g (n=50)
     Final Biomass: 1200.5 ± 89.2 g
     FCR: 2.1
     Survival: 95% (p<0.05)

5. **MALFORMED CONTEXT:**
   - Ignore garbage symbols, breaks, tabs, case variations
   - Extract fragments even if scattered

6. **METHODOLOGY EXTRACTION:**
   - Look for: "Materials and Methods", "Method", "Procedure", "Statistical analysis", "Design"
   - Extract procedural descriptions, study parameters, sample characteristics
   - Even if fragmented, pair descriptions with numbers (n=, sample size, duration, etc.)

7. **INTERPRETATION EXTRACTION:**
   - Look for: "Results", "Discussion", "Findings", "Observed", "Showed", "Demonstrated"
   - Extract what results mean, comparisons between treatments, statistical significance
   - Link numbers to their interpretation (e.g., "Weight gain was higher (p<0.05)" not just the p-value)

---

**CONTEXT:**
{context}

**QUESTION:**
{question}

---

**EXTRACT - PRIORITIZE NUMBERS AND PAIR WITH HEADERS. EXTRACT ALL 4 SECTIONS IF DATA EXISTS. FOLLOW FORMAT. NEVER HEADERS WITHOUT NUMBERS.**"""
            )
            chain = prompt | self.llm
            response = chain.invoke(state)
            return {"answer": response.content}

        workflow.add_node("retrieve", retrieve)
        workflow.add_node("generate", generate)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
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
                    'alevinos'}
        en_words = {'what', 'how', 'which', 'feed', 'restriction', 'restricted', 'diet', 'under', 'growth',
                    'fingerlings'}
        pt_accents = any(c in 'áéíóúãõçÁÉÍÓÚÃÕÇ' for c in question)
        pt_score = sum(1 for w in pt_words if w in q_lower) + (1 if pt_accents else 0)
        en_score = sum(1 for w in en_words if w in q_lower)
        return 'pt-BR' if pt_score >= en_score else 'en'

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

    def _retrieve_docs_via_rpc(self, question: str, k: int = 20) -> List[Document]:
        """Recuperação via RPC com k=20."""
        lang = self._detect_question_language(question)
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