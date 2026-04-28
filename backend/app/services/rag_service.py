from typing import TypedDict, List, Optional, Sequence, Any
import uuid
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from app.database import supabase_admin

State = TypedDict('State', {
    'question': str,
    'chat_history': Sequence[dict[str, str]],
    'docs': List[Document],
    'generation': str,
    'hallucination': str,
    'critique': Optional[str],
    'answer': Optional[str],
})

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        self.vectorstore = SupabaseVectorStore(
            embedding=self.embeddings,
            client=supabase_admin,
            table_name='documents'
        )
        self.generate_prompt = ChatPromptTemplate.from_template(
            """<system>\nYou are a world class AI model who answers questions in a helpful way.\nUse the provided context and chat history to answer the question.\nDo not use any external knowledge or hallucinate.\n</system>\n<context>{context}</context>\n<chat_history>{history}</chat_history>\n<previous_critique>{critique}</previous_critique>\n<question>{question}</question>\nAnswer:"""
        )
        self.grade_prompt = ChatPromptTemplate.from_template(
            """<system>\nYou are an impartial judge. Determine if the answer hallucinates or contains information not grounded in the context.\nRespond with only 'yes' (hallucinates) or 'no' (grounded).\n</system>\n<context>{context}</context>\n<generation>{generation}</generation>"""
        )
        self.critique_prompt = ChatPromptTemplate.from_template(
            """<system>\nYou are a critical evaluator. Analyze the generation for factual accuracy against the context.\nProvide a detailed critique highlighting any hallucinations, errors, or improvements.\n</system>\n<context>{context}</context>\n<generation>{generation}</generation>\nCritique:"""
        )
        self.respond_prompt = ChatPromptTemplate.from_template(
            """<system>\nYou are a helpful assistant. Synthesize the final answer using the generation and any critique.\n</system>\n<chat_history>{history}</chat_history>\n<question>{question}</question>\n<generation>{generation}</generation>\n<critique>{critique}</critique>\nFinal Answer:"""
        )
        self.rag_graph = self._build_graph()

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node('generate', self._generate)
        graph_builder.add_node('grade_hallucination', self._grade_hallucination)
        graph_builder.add_node('critique', self._critique)
        graph_builder.add_node('respond', self._respond)
        graph_builder.set_entry_point('generate')
        graph_builder.add_edge('generate', 'grade_hallucination')
        graph_builder.add_conditional_edges(
            'grade_hallucination',
            self._should_continue,
            {
                'critique': 'critique',
                'respond': 'respond',
            }
        )
        graph_builder.add_edge('critique', 'respond')
        graph_builder.add_edge('respond', END)
        return graph_builder.compile()

    async def _generate(self, state: State) -> State:
        chain = self.generate_prompt | self.llm
        context = '\n\n'.join(doc.page_content for doc in state['docs'])
        history = '\n'.join([
            f"Human: {msg['content']}" if msg['role'] == 'user' else f"Assistant: {msg['content']}"
            for msg in state['chat_history'][-6:]
        ])
        critique = state.get('critique', '')
        msg = await chain.ainvoke({
            'context': context,
            'history': history,
            'question': state['question'],
            'critique': critique,
        })
        return {'generation': msg.content}

    async def _grade_hallucination(self, state: State) -> State:
        chain = self.grade_prompt | self.llm
        context = '\n\n'.join(doc.page_content for doc in state['docs'])
        msg = await chain.ainvoke({
            'context': context,
            'generation': state['generation'],
        })
        hallucination = msg.content.strip().lower()
        hallucination = 'yes' if 'yes' in hallucination else 'no'
        return {'hallucination': hallucination}

    async def _critique(self, state: State) -> State:
        chain = self.critique_prompt | self.llm
        context = '\n\n'.join(doc.page_content for doc in state['docs'])
        msg = await chain.ainvoke({
            'context': context,
            'generation': state['generation'],
        })
        return {'critique': msg.content}

    async def _respond(self, state: State) -> State:
        chain = self.respond_prompt | self.llm
        history = '\n'.join([
            f"Human: {msg['content']}" if msg['role'] == 'user' else f"Assistant: {msg['content']}"
            for msg in state['chat_history'][-6:]
        ])
        critique = state.get('critique', '')
        msg = await chain.ainvoke({
            'history': history,
            'question': state['question'],
            'generation': state['generation'],
            'critique': critique,
        })
        return {'answer': msg.content}

    def _should_continue(self, state: State) -> str:
        if state['hallucination'].lower() == 'yes':
            return 'critique'
        return 'respond'

    async def ingest_pdf(self, file_path: str, filename: str) -> int:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        splits = self.text_splitter.split_documents(docs)
        file_id = str(uuid.uuid4())
        for split in splits:
            split.metadata.update({
                'original_file_id': file_id,
                'original_file_name': filename,
                'storage_bucket': 'pdf_storage',
                'storage_path': filename,
            })
        self.vectorstore.add_documents(splits)
        return len(splits)

    async def get_answer(self, question: str, chat_history: List[dict]) -> str:
        docs = self.vectorstore.similarity_search(question, k=5)
        initial_state: State = {
            'question': question,
            'chat_history': chat_history,
            'docs': docs,
            'generation': '',
            'hallucination': '',
            'critique': None,
            'answer': None,
        }
        result = await self.rag_graph.ainvoke(initial_state)
        return result['answer']

rag_service = RAGService()