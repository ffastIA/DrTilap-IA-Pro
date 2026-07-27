"""Normalização e casamento de trechos para as métricas de recuperação.

Separado do executor porque é a parte com regra de negócio sutil: os chunks têm
fronteiras arbitrárias e o texto vem de extração de PDF, então comparar por
igualdade exata produziria falsos negativos sistemáticos.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Sequence


def normalize(text: str) -> str:
    """Normaliza texto para comparação tolerante a ruído de extração de PDF."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def passage_rank(passage: str, retrieved_contents: Sequence[str]) -> int | None:
    """Posição (0-based) do primeiro chunk recuperado que contém o trecho.

    Retorna None se nenhum chunk o contém.
    """
    needle = normalize(passage)
    if not needle:
        return None
    for position, content in enumerate(retrieved_contents):
        if needle in normalize(content):
            return position
    return None


def is_refusal(answer: str) -> bool:
    """Heurística para detectar recusa honesta.

    Deliberadamente conservadora: só considera recusa quando a resposta é curta
    OU contém um marcador explícito de ausência de informação. Uma resposta longa
    e substantiva que apenas menciona 'não foi possível' em uma seção NÃO conta
    como recusa — é exatamente o comportamento que queremos medir como falha.
    """
    normalized = normalize(answer)
    if not normalized:
        return True

    markers = (
        "não há informação",
        "nao ha informacao",
        "não encontrei",
        "nao encontrei",
        "não consta",
        "nao consta",
        "não está disponível no contexto",
        "nao esta disponivel no contexto",
        "não posso responder",
        "nao posso responder",
        "contexto não cobre",
        "contexto nao cobre",
        "base de conhecimento não",
        "base de conhecimento nao",
        "fora do escopo",
        "não foi possível encontrar",
        "nao foi possivel encontrar",
        "i don't have",
        "not available in the context",
    )
    has_marker = any(marker in normalized for marker in markers)

    # Resposta curta com marcador, ou muito curta: recusa.
    if len(normalized) < 400 and has_marker:
        return True
    if len(normalized) < 120:
        return True
    return False


def mention_coverage(answer: str, must_mention: Sequence[str]) -> float:
    """Fração dos pontos obrigatórios cujos termos numéricos/chave aparecem.

    Compara pelos tokens significativos de cada ponto (números e palavras longas),
    não pela frase inteira — a redação da resposta varia legitimamente.
    """
    if not must_mention:
        return 1.0

    normalized_answer = normalize(answer)
    covered = 0
    for point in must_mention:
        tokens = _significant_tokens(point)
        if not tokens:
            continue
        hits = sum(1 for token in tokens if token in normalized_answer)
        if hits / len(tokens) >= 0.6:
            covered += 1
    return covered / len(must_mention)


def _significant_tokens(text: str) -> list[str]:
    normalized = normalize(text)
    raw = re.findall(r"[a-záàâãéêíóôõúç0-9][a-záàâãéêíóôõúç0-9,.%-]*", normalized)
    return [token for token in raw if any(ch.isdigit() for ch in token) or len(token) > 4]
