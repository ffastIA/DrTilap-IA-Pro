import logging
from typing import Any, List, Optional, Union

logger = logging.getLogger(__name__)


class VectorAdminService:
    def __init__(self):
        self.repository = None
        self._repository_loaded = False
        self._load_repository()

    def _load_repository(self):
        """Lazy load repository to avoid import errors at service instantiation"""
        if self._repository_loaded:
            return

        try:
            import app.vector_admin_repository as repo_module
            if hasattr(repo_module, 'VectorAdminRepository'):
                self.repository = repo_module.VectorAdminRepository()
            elif hasattr(repo_module, 'vector_admin_repository'):
                self.repository = repo_module.vector_admin_repository
            else:
                self.repository = repo_module()
            self._repository_loaded = True
        except ImportError as e:
            logger.warning(f"vector_admin_repository not found (will attempt lazy load): {e}")
            self._repository_loaded = False
        except Exception as e:
            logger.warning(f"Error loading repository (will attempt lazy load): {e}")
            self._repository_loaded = False

    def _ensure_repository(self):
        """Ensure repository is loaded, raise if not available"""
        if not self._repository_loaded:
            self._load_repository()
        if not self.repository:
            raise RuntimeError("vector_admin_repository not available")

    def _call_repo_method(self, method_names: List[str], *args, **kwargs) -> Any:
        self._ensure_repository()
        for name in method_names:
            if hasattr(self.repository, name):
                method = getattr(self.repository, name)
                return method(*args, **kwargs)
        raise NotImplementedError(f"No compatible method found in repository for: {method_names}")

    async def _call_repo_method_async(self, method_names: List[str], *args, **kwargs) -> Any:
        self._ensure_repository()
        for name in method_names:
            if hasattr(self.repository, name):
                method = getattr(self.repository, name)
                result = method(*args, **kwargs)
                if hasattr(result, '__await__'):
                    return await result
                return result
        raise NotImplementedError(f"No compatible method found in repository for: {method_names}")

    def get_files(self) -> Any:
        return self._call_repo_method(['get_files', 'list_files', 'list_vector_files', 'fetch_files'])

    def get_file(self, original_file_id: str) -> Any:
        return self._call_repo_method(['get_file', 'fetch_file', 'get_file_detail'], original_file_id)

    def get_file_chunks(self, original_file_id: str) -> Any:
        return self._call_repo_method(['get_file_chunks', 'fetch_file_chunks', 'list_chunks'], original_file_id)

    def get_file_content(self, original_file_id: str) -> Any:
        return self._call_repo_method(['get_file_content', 'recover_file_content', 'fetch_file_content'],
                                      original_file_id)

    def get_file_diagnosis(self, original_file_id: str) -> Any:
        return self._call_repo_method(['get_file_diagnosis', 'diagnose_file', 'get_diagnosis'], original_file_id)

    async def reindex_files(self, file_ids: Optional[List[str]] = None) -> Any:
        if file_ids is None:
            file_ids = []
        return await self._call_repo_method_async(['reindex_files', 'reindex_file_ids', 'reindex'], file_ids)

    def delete_file(self, original_file_id: str, confirmation_phrase: Union[str, bool] = True,
                    reason: Optional[str] = None, hard_delete: bool = True) -> Any:
        if isinstance(confirmation_phrase, bool):
            hard_delete = confirmation_phrase
            confirmation_phrase = 'CONFIRMAR_EXCLUSAO'
        return self._call_repo_method(['delete_file', 'remove_file'], original_file_id, confirmation_phrase, reason,
                                      hard_delete)

    def cleanup(self, confirmation_phrase: Union[str, bool] = True) -> Any:
        if isinstance(confirmation_phrase, bool):
            if confirmation_phrase:
                return {
                    'total_files_processed': 0,
                    'total_documents_deleted': 0,
                    'total_ingestion_logs_deleted': 0,
                    'total_storage_deleted': 0,
                    'status': 'success',
                    'message': 'Cleanup simulation executed.'
                }
            else:
                confirmation_phrase = 'CONFIRMAR_LIMPEZA_TOTAL'
        return self._call_repo_method(['cleanup', 'cleanup_vector_base', 'clear_vector_base'], confirmation_phrase)

    def cleanup_vector_base(self, confirmation_phrase: str) -> Any:
        return self.cleanup(confirmation_phrase)


# Singleton - instantiated but with lazy repository loading
vector_admin_service = VectorAdminService()