# CAMINHO: backend/tests/test_rag_retrieval_refusal.py
"""Testes de regressão para a lógica nova de retrieval-refusal-quality.

Cobertura mínima e deliberada: a mudança que motivou esta mudança inteira
(embedding caindo silenciosamente para ada-002 por meses) só passou
despercebida porque nada testava a configuração efetiva nem o
comportamento de recuperação. Estes testes existem para não repetir isso.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.rag_service import get_rag_service
from app.utils.rag_config import REFUSAL_FLOOR_SIMILARITY


@pytest.fixture
def service():
    return get_rag_service()


def _mock_match(similarity: float, content: str = "conteudo de teste", db_id: str = "id-1"):
    return {"id": db_id, "content": content, "similarity": similarity, "metadata": {}}


class TestRefusalFallback:
    """`_retrieve_docs_via_rpc`: comportamento em três faixas de similaridade."""

    def test_above_threshold_returns_docs_normally(self, service):
        with patch.object(service, "_embed_query", return_value=[0.0] * 1536), \
             patch.object(service, "_search_rpc", return_value=[_mock_match(service.similarity_threshold + 0.1)]):
            docs = service._retrieve_docs_via_rpc("pergunta", k=5, use_llm_expansion=False)
        assert len(docs) == 1

    def test_between_floor_and_threshold_keeps_all_candidates(self, service):
        """Zona fraca mantém TODOS os candidatos (não só o top-1) — restringir
        a 1 chunk sacrificaria recall de perguntas legítimas que caem aqui só
        pela sobreposição real entre as distribuições de score."""
        weak_score = (REFUSAL_FLOOR_SIMILARITY + service.similarity_threshold) / 2
        assert REFUSAL_FLOOR_SIMILARITY < weak_score < service.similarity_threshold
        matches = [_mock_match(weak_score, db_id="id-1"), _mock_match(weak_score - 0.01, db_id="id-2")]
        with patch.object(service, "_embed_query", return_value=[0.0] * 1536), \
             patch.object(service, "_search_rpc", return_value=matches):
            docs = service._retrieve_docs_via_rpc("pergunta", k=5, use_llm_expansion=False)
        assert len(docs) == 2, "zona fraca não deve descartar candidatos além do top-1"

    def test_below_floor_refuses_with_empty_docs(self, service):
        below_floor = max(REFUSAL_FLOOR_SIMILARITY - 0.1, 0.0)
        with patch.object(service, "_embed_query", return_value=[0.0] * 1536), \
             patch.object(service, "_search_rpc", return_value=[_mock_match(below_floor)]):
            docs = service._retrieve_docs_via_rpc("pergunta", k=5, use_llm_expansion=False)
        assert docs == [], "score abaixo do piso de recusa não deve devolver nenhum chunk"

    def test_skip_threshold_bypasses_refusal_logic(self, service):
        """Retries (skip_threshold=True) não aplicam o piso de recusa —
        já é uma tentativa deliberadamente mais permissiva."""
        below_floor = max(REFUSAL_FLOOR_SIMILARITY - 0.1, 0.0)
        with patch.object(service, "_embed_query", return_value=[0.0] * 1536), \
             patch.object(service, "_search_rpc", return_value=[_mock_match(below_floor)]):
            docs = service._retrieve_docs_via_rpc(
                "pergunta", k=5, skip_threshold=True, use_llm_expansion=False
            )
        assert len(docs) == 1


class TestConfigFromEnvironment:
    """Config de recuperação/recusa não pode voltar a ser hardcoded."""

    def test_retrieval_constants_are_read_from_env(self, monkeypatch):
        monkeypatch.setenv("RETRIEVAL_K", "77")
        monkeypatch.setenv("REFUSAL_FLOOR_SIMILARITY", "0.42")
        import importlib
        from app.utils import rag_config
        importlib.reload(rag_config)
        try:
            assert rag_config.RETRIEVAL_K == 77
            assert rag_config.REFUSAL_FLOOR_SIMILARITY == pytest.approx(0.42)
        finally:
            monkeypatch.delenv("RETRIEVAL_K", raising=False)
            monkeypatch.delenv("REFUSAL_FLOOR_SIMILARITY", raising=False)
            importlib.reload(rag_config)


class TestFollowupCondensation:
    """`_condense_followup_question`: só age quando há histórico."""

    def test_no_history_returns_question_unchanged(self, service):
        mock_llm = MagicMock()
        with patch.object(service, "llm", mock_llm):
            result = service._condense_followup_question("pergunta original", [], "pt-BR")
        assert result == "pergunta original"
        mock_llm.invoke.assert_not_called()

    def test_with_history_condenses_via_llm(self, service):
        mock_response = MagicMock()
        mock_response.content = "Qual a margem por unidade do equipamento BIA?"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        history = [["Qual o preço do equipamento BIA?", "R$ 17.000 por unidade."]]
        with patch.object(service, "llm", mock_llm):
            result = service._condense_followup_question(
                "E qual a margem por unidade?", history, "pt-BR"
            )
        assert result == "Qual a margem por unidade do equipamento BIA?"
        mock_llm.invoke.assert_called_once()

    def test_llm_failure_falls_back_to_mechanical_concat(self, service):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API indisponível")
        history = [["Qual o preço do BIA?", "R$ 17.000."]]
        with patch.object(service, "llm", mock_llm):
            result = service._condense_followup_question("E a margem?", history, "pt-BR")
        assert "Qual o preço do BIA?" in result
        assert "E a margem?" in result
