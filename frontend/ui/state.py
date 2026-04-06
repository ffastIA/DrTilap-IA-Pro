import reflex as rx
import httpx
import json
from typing import List, Tuple


class State(rx.State):
    # Lista de mensagens: [("pergunta", "resposta"), ...]
    chat_history: List[List[str]] = []
    current_message: str = ""
    is_loading: bool = False

    async def answer(self):
        if not self.current_message:
            return

        self.is_loading = True
        yield  # Atualiza a UI para mostrar o estado de carregamento

        # Prepara a pergunta e limpa o campo de input
        user_question = self.current_message
        self.current_message = ""

        # Adiciona a pergunta do usuário ao chat imediatamente
        self.chat_history.append([user_question, "Pensando..."])
        yield

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/consultoria/chat",
                    json={
                        "message": user_question,
                        "history": self.chat_history[:-1]  # Envia o histórico anterior
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    # Atualiza a última mensagem com a resposta real da IA
                    self.chat_history[-1][1] = data["answer"]
                else:
                    self.chat_history[-1][1] = "Erro ao conectar com o consultor."
        except Exception as e:
            self.chat_history[-1][1] = f"Erro de conexão: {str(e)}"

        self.is_loading = False
        yield