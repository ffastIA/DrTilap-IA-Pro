import jwt
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from email_validator import validate_email, EmailNotValidError
import logging
from typing import Optional

# Configuração de Logging
logger = logging.getLogger(__name__)

# --- Configurações de Segurança ---
SECRET_KEY = os.environ.get("SECRET_KEY", "uma_chave_secreta_muito_forte_e_aleatoria_para_o_DrTilapia_1.3")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Contexto para hashing de senhas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Funções de Validação ---

def validar_email(email: str) -> bool:
    """
    Valida o formato de um endereço de e-mail usando a biblioteca email_validator.

    Args:
        email (str): O endereço de e-mail a ser validado.

    Returns:
        bool: True se o e-mail for válido, False caso contrário.
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError as e:
        logger.warning(f"Validação de e-mail falhou para '{email}': {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado na validação de e-mail para '{email}': {e}")
        return False


def validar_senha(senha: str) -> bool:
    """
    Valida a força de uma senha com base em critérios mínimos.

    Critérios:
    - Mínimo de 8 caracteres.
    - Pelo menos uma letra maiúscula.
    - Pelo menos um dígito.
    - Pelo menos um caractere especial.

    Args:
        senha (str): A senha a ser validada.

    Returns:
        bool: True se a senha atender aos critérios de força, False caso contrário.
    """
    if len(senha) < 8:
        logger.warning("Validação de senha falhou: Senha muito curta (mínimo 8 caracteres).")
        return False
    if not any(c.isupper() for c in senha):
        logger.warning("Validação de senha falhou: Senha deve conter pelo menos uma letra maiúscula.")
        return False
    if not any(c.isdigit() for c in senha):
        logger.warning("Validação de senha falhou: Senha deve conter pelo menos um dígito.")
        return False

    special_characters = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_characters for c in senha):
        logger.warning("Validação de senha falhou: Senha deve conter pelo menos um caractere especial.")
        return False
    return True


# --- Funções de Hashing de Senha ---

def get_password_hash(password: str) -> str:
    """
    Gera o hash de uma senha usando bcrypt.

    Args:
        password (str): A senha em texto puro.

    Returns:
        str: O hash da senha.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha em texto puro corresponde a um hash de senha.

    Args:
        plain_password (str): A senha em texto puro fornecida pelo usuário.
        hashed_password (str): O hash da senha armazenado.

    Returns:
        bool: True se as senhas corresponderem, False caso contrário.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Erro ao verificar senha: {e}")
        return False


# --- Funções JWT (JSON Web Token) ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token de acesso JWT.

    Args:
        data (dict): Dados a serem codificados no token (ex: {"sub": "user@example.com"}).
        expires_delta (Optional[timedelta]): Tempo de expiração do token. Se None, usa o padrão.

    Returns:
        str: O token JWT codificado.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Token JWT criado para dados: {data.get('sub', 'N/A')}")
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verifica e decodifica um token de acesso JWT.

    Args:
        token (str): O token JWT a ser verificado.

    Returns:
        Optional[dict]: O payload do token se for válido, None caso contrário.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token JWT verificado com sucesso. Payload: {payload.get('sub', 'N/A')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Verificação de token falhou: Token expirado.")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Verificação de token falhou: Token inválido.")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado na verificação de token: {e}")
        return None