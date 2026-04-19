# CAMINHO: backend/app/services/vector_admin_service.py

import logging
import inspect
from app.vector_admin_repository import VectorAdminRepository
from app.services.rag_service import rag_service


class VectorAdminService:
    """
    Serviço administrativo para operações na base vetorial.
    Gerencia arquivos, chunks, conteúdo e operações de manutenção.
    """

    def __init__(self):
        """
        Inicializa o serviço com repositório e logger.
        """
        self.repository = VectorAdminRepository()
        self.logger = logging.getLogger(__name__)

    def list_files(self):
        """
        Lista todos os arquivos na base vetorial.

        Returns:
            list: Lista de arquivos.
        """
        self.logger.info("Listando arquivos na base vetorial.")
        return self.repository.list_files()

    def get_file(self, original_file_id: str):
        """
        Obtém detalhes de um arquivo específico.

        Args:
            original_file_id (str): ID do arquivo original.

        Returns:
            dict: Detalhes do arquivo.
        """
        self.logger.info(f"Obtendo detalhes do arquivo: {original_file_id}")
        return self.repository.get_file(original_file_id)

    def get_file_chunks(self, original_file_id: str):
        """
        Obtém os chunks de um arquivo específico.

        Args:
            original_file_id (str): ID do arquivo original.

        Returns:
            list: Lista de chunks.
        """
        self.logger.info(f"Obtendo chunks do arquivo: {original_file_id}")
        return self.repository.get_file_chunks(original_file_id)

    def recover_file_content(self, original_file_id: str):
        """
        Recupera o conteúdo de um arquivo específico.

        Args:
            original_file_id (str): ID do arquivo original.

        Returns:
            str: Conteúdo do arquivo.
        """
        self.logger.info(f"Recuperando conteúdo do arquivo: {original_file_id}")
        return self.repository.recover_file_content(original_file_id)

    def diagnose_file_recovery(self, original_file_id: str):
        """
        Diagnóstica a recuperação de um arquivo específico.

        Args:
            original_file_id (str): ID do arquivo original.

        Returns:
            dict: Diagnóstico da recuperação.
        """
        self.logger.info(f"Diagnosticando recuperação do arquivo: {original_file_id}")
        return self.repository.diagnose_file_recovery(original_file_id)

    def delete_file(self, original_file_id: str, confirmation_phrase: str, reason: str | None = None,
                    hard_delete: bool = True):
        """
        Deleta um arquivo da base vetorial após validação da frase de confirmação.

        Args:
            original_file_id (str): ID do arquivo original.
            confirmation_phrase (str): Frase de confirmação (deve ser 'CONFIRMAR_EXCLUSAO').
            reason (str | None): Motivo da exclusão.
            hard_delete (bool): Se deve fazer exclusão física.

        Returns:
            dict: Resultado da operação.

        Raises:
            ValueError: Se a frase de confirmação for inválida.
        """
        if confirmation_phrase != "CONFIRMAR_EXCLUSAO":
            raise ValueError("Frase de confirmação inválida para exclusão.")
        self.logger.info(f"Deletando arquivo: {original_file_id}, razão: {reason}")
        return self.repository.delete_file(original_file_id, confirmation_phrase, reason, hard_delete)

    def cleanup_vector_base(self, confirmation_phrase: str):
        """
        Limpa toda a base vetorial após validação da frase de confirmação.

        Args:
            confirmation_phrase (str): Frase de confirmação (deve ser 'CONFIRMAR_LIMPEZA_TOTAL').

        Returns:
            dict: Resultado da operação.

        Raises:
            ValueError: Se a frase de confirmação for inválida.
        """
        if confirmation_phrase != "CONFIRMAR_LIMPEZA_TOTAL":
            raise ValueError("Frase de confirmação inválida para limpeza total.")
        self.logger.info("Iniciando limpeza total da base vetorial.")
        return self.repository.cleanup_vector_base(confirmation_phrase)

    async def reindex_files(self, confirmation_phrase: str, original_file_ids: list[str] | None = None):
        """
        Reindexa arquivos na base vetorial após validação da frase de confirmação.

        Args:
            confirmation_phrase (str): Frase de confirmação (deve ser 'CONFIRMAR_REINDEXACAO').
            original_file_ids (list[str] | None): IDs dos arquivos a reindexar (None para todos).

        Returns:
            dict: Resultado da reindexação com contadores e status.

        Raises:
            ValueError: Se a frase de confirmação for inválida.
        """
        if confirmation_phrase != "CONFIRMAR_REINDEXACAO":
            raise ValueError("Frase de confirmação inválida para reindexação.")
        self.logger.info("Iniciando reindexação de arquivos.")

        all_files = self.repository.list_files()
        if original_file_ids:
            eligible_files = [f for f in all_files if
                              f.get('original_file_id') in original_file_ids and f.get('storage_path') and f.get(
                                  'original_file_name')]
        else:
            eligible_files = [f for f in all_files if f.get('storage_path') and f.get('original_file_name')]

        if not eligible_files:
            return {
                "processed_files": 0,
                "failed_files": 0,
                "total_chunks_created": 0,
                "status": "success",
                "message": "Nenhum arquivo elegível encontrado para reindexação."
            }

        processed_files = 0
        failed_files = 0
        total_chunks_created = 0

        for file_info in eligible_files:
            try:
                file_id = file_info['original_file_id']
                storage_path = file_info['storage_path']
                self.logger.info(f"Reindexando arquivo: {file_id}")

                # Tentar métodos de reingestão defensivamente
                result = None
                if hasattr(rag_service, 'reindex_file_from_storage'):
                    result = await self._maybe_await(rag_service.reindex_file_from_storage(storage_path))
                elif hasattr(rag_service, 'reingest_file'):
                    result = await self._maybe_await(rag_service.reingest_file(storage_path))
                elif hasattr(rag_service, 'ingest_pdf_from_storage'):
                    result = await self._maybe_await(rag_service.ingest_pdf_from_storage(storage_path))
                else:
                    raise AttributeError("Nenhum método de reingestão disponível.")

                chunks_created = self._extract_chunks_created(result)
                total_chunks_created += chunks_created
                processed_files += 1
                self.logger.info(f"Arquivo {file_id} reindexado com sucesso, chunks criados: {chunks_created}")
            except Exception as e:
                failed_files += 1
                self.logger.error(f"Falha ao reindexar arquivo {file_id}: {str(e)}")
                continue

        status = "success" if failed_files == 0 else "partial_success"
        message = f"Reindexação concluída: {processed_files} processados, {failed_files} falharam."

        return {
            "processed_files": processed_files,
            "failed_files": failed_files,
            "total_chunks_created": total_chunks_created,
            "status": status,
            "message": message
        }

    def _extract_chunks_created(self, result):
        """
        Extrai o número de chunks criados do resultado da operação.

        Args:
            result: Resultado da operação de reingestão.

        Returns:
            int: Número de chunks criados.
        """
        if isinstance(result, dict):
            for key in ['total_chunks_created', 'chunks_created', 'chunks']:
                if key in result and isinstance(result[key], int):
                    return result[key]
        return 0

    async def _maybe_await(self, coro_or_result):
        """
        Aguarda se for uma coroutine, senão retorna diretamente.

        Args:
            coro_or_result: Coroutine ou resultado.

        Returns:
            Resultado da operação.
        """
        if inspect.isawaitable(coro_or_result):
            return await coro_or_result
        return coro_or_result


# Instância singleton do serviço
vector_admin_service = VectorAdminService()
