import axios, { AxiosInstance, AxiosError } from 'axios';
import Cookies from 'js-cookie';

// ============ CONFIGURAÇÃO BASE ============
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============ INTERCEPTORS ============

// Interceptor REQUEST: Adiciona JWT em todas as requisições
apiClient.interceptors.request.use(
  (config) => {
    const token = Cookies.get('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Interceptor RESPONSE: Trata erros de autenticação (401)
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expirado ou inválido
      console.warn('Unauthorized (401) - Logging out');
      Cookies.remove('accessToken');
      Cookies.remove('user');

      // Redirecionar para login (se estiver no navegador)
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
    }

    if (error.response?.status === 403) {
      console.warn('Forbidden (403) - Acesso negado');
    }

    return Promise.reject(error);
  }
);

// ============ INTERFACES DE TIPO ============

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    role: 'admin' | 'user';
  };
}

export interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  debug_info?: string;
}

export interface UploadResponse {
  message: string;
  chunks_criados: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// ============ AUTH API ============

export const authApi = {
  /**
   * Realiza login com email e senha
   * Endpoint: POST /auth/login
   */
  login: async (email: string, password: string): Promise<LoginResponse> => {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/login', {
        email,
        password,
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        throw new Error((error.response.data as ApiError).detail || 'Erro ao fazer login');
      }
      throw error;
    }
  },

  /**
   * Faz logout (local apenas - remove tokens)
   */
  logout: () => {
    Cookies.remove('accessToken');
    Cookies.remove('user');
    console.log('Logout realizado');
  },

  /**
   * Verifica se token é válido
   * Endpoint: GET /auth/verify (se implementado no backend)
   */
  verifyToken: async (): Promise<boolean> => {
    try {
      const response = await apiClient.get('/auth/verify');
      return response.status === 200;
    } catch {
      return false;
    }
  },
};

// ============ CHAT API (RAG) ============

export const chatApi = {
  /**
   * Envia mensagem para consultor IA
   * Endpoint: POST /consultoria/chat
   */
  sendMessage: async (
    message: string,
    history: Array<[string, string]> = []
  ): Promise<ChatResponse> => {
    try {
      const response = await apiClient.post<ChatResponse>('/consultoria/chat', {
        message,
        history, // Histórico do chat [[pergunta1, resposta1], [pergunta2, resposta2], ...]
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        const errorData = error.response.data as ApiError;
        throw new Error(errorData.detail || 'Erro ao processar mensagem');
      }
      throw new Error('Erro na comunicação com o servidor');
    }
  },

  /**
   * Obtém histórico de chat (se implementado no backend)
   * Endpoint: GET /consultoria/history
   */
  getHistory: async (): Promise<Array<[string, string]>> => {
    try {
      const response = await apiClient.get<Array<[string, string]>>(
        '/consultoria/history'
      );
      return response.data;
    } catch {
      return [];
    }
  },

  /**
   * Limpa histórico de chat (se implementado no backend)
   * Endpoint: DELETE /consultoria/history
   */
  clearHistory: async (): Promise<void> => {
    try {
      await apiClient.delete('/consultoria/history');
    } catch (error) {
      console.error('Erro ao limpar histórico:', error);
    }
  },
};

// ============ UPLOAD API (ADMIN) ============

export const uploadApi = {
  /**
   * Upload de arquivo PDF
   * Endpoint: POST /admin/upload
   */
  uploadPdf: async (file: File): Promise<UploadResponse> => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post<UploadResponse>('/admin/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        // Callback de progresso (opcional)
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            console.log(`Upload progress: ${percentCompleted}%`);
          }
        },
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        const errorData = error.response.data as ApiError;
        throw new Error(
          errorData.detail || 'Erro ao fazer upload do arquivo'
        );
      }
      throw new Error('Erro na comunicação com o servidor');
    }
  },

  /**
   * Reindexar base de conhecimento (limpar cache e reconstruir FAISS)
   * Endpoint: POST /admin/reindex (se implementado no backend)
   */
  reindexKnowledgeBase: async (): Promise<{ message: string }> => {
    try {
      const response = await apiClient.post<{ message: string }>(
        '/admin/reindex'
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        const errorData = error.response.data as ApiError;
        throw new Error(
          errorData.detail || 'Erro ao reindexar base de conhecimento'
        );
      }
      throw new Error('Erro na comunicação com o servidor');
    }
  },

  /**
   * Obtém lista de documentos carregados
   * Endpoint: GET /admin/documents (se implementado no backend)
   */
  getDocuments: async (): Promise<Array<{ id: string; name: string; chunks: number }>> => {
    try {
      const response = await apiClient.get<Array<{ id: string; name: string; chunks: number }>>(
        '/admin/documents'
      );
      return response.data;
    } catch {
      return [];
    }
  },

  /**
   * Deleta um documento
   * Endpoint: DELETE /admin/documents/:id (se implementado no backend)
   */
  deleteDocument: async (documentId: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.delete<{ message: string }>(
        `/admin/documents/${documentId}`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        const errorData = error.response.data as ApiError;
        throw new Error(errorData.detail || 'Erro ao deletar documento');
      }
      throw new Error('Erro na comunicação com o servidor');
    }
  },
};

// ============ HEALTH CHECK ============

export const healthApi = {
  /**
   * Verifica saúde da API
   * Endpoint: GET /health
   */
  check: async (): Promise<{ status: string; version: string }> => {
    try {
      const response = await apiClient.get<{ status: string; version: string }>(
        '/health'
      );
      return response.data;
    } catch {
      throw new Error('API está offline');
    }
  },
};

// ============ UTILITY FUNCTIONS ============

/**
 * Formata erro da API para exibição ao usuário
 */
export const formatApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response?.data) {
      const data = error.response.data as ApiError;
      return data.detail || 'Erro desconhecido';
    }
    if (error.message === 'Network Error') {
      return 'Erro de conexão com o servidor';
    }
    return error.message || 'Erro desconhecido';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Erro desconhecido';
};

/**
 * Verifica se erro é de autenticação
 */
export const isAuthError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.response?.status === 401 || error.response?.status === 403;
  }
  return false;
};

/**
 * Verifica se erro é de rede
 */
export const isNetworkError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.code === 'ECONNABORTED' || error.message === 'Network Error';
  }
  return false;
};

// ============ EXPORT DEFAULT ============

export default apiClient;