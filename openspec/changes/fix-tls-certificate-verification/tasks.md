## 1. Implementar resolução de CA bundle

- [x] 1.1 Em `backend/app/database.py`, adicionado `_resolve_ssl_verify()`: retorna `SSL_CERT_FILE` se definido, senão `REQUESTS_CA_BUNDLE` se definido, senão `True`.
- [x] 1.2 `_ssl_options` agora usa `httpx.Client(verify=_resolve_ssl_verify())` em vez de `verify=False`.
- [x] 1.3 `backend/app/services/rag_service.py` importa `_resolve_ssl_verify` de `app.database` e o usa para `_http_client`/`_http_async_client`.

## 2. Documentação

- [x] 2.1 Criado `backend/.env.example` com `SUPABASE_URL`/`SUPABASE_KEY`/`SUPABASE_SERVICE_ROLE_KEY`/`OPENAI_API_KEY` e `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` documentados (opcionais, com comentário explicando o caso de uso do proxy corporativo).

## 3. Verificação

- [x] 3.1 `py_compile` em `backend/app/database.py` e `backend/app/services/rag_service.py` — sem erros.
- [x] 3.2 Backend rodando localmente (venv) com `_resolve_ssl_verify() -> True` (nenhuma variável de CA configurada): `POST /auth/login` com credenciais inválidas retornou `401 {"detail":"Invalid credentials"}` — confirma que a chamada real ao Supabase completou o handshake TLS com verificação de certificado ativa (não `verify=False`), sem erro de SSL.
- [x] 3.3 Confirmado via `grep -rn "verify=False" backend/app`: zero ocorrências. Só existem matches em `backend/.venv/` (bibliotecas de terceiros, fora do escopo).
