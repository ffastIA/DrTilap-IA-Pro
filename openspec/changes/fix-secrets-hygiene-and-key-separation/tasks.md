## 1. Rotação de chave (ação manual do usuário — não automatizável)

- [ ] 1.1 No Supabase Dashboard do projeto `tfdripphcwbjiveksuet`, gerar uma nova chave `service_role` (a atual foi exposta em texto puro nesta conversa). **PENDENTE — aguardando ação do usuário.**
- [x] 1.2 Avaliar se a chave `anon` também deve ser rotacionada por precaução: **não é necessário** — `anon` é uma chave de baixo privilégio, feita para ser pública (já exposta deliberadamente em `NEXT_PUBLIC_SUPABASE_ANON_KEY` desde a mudança `fix-admin-middleware-jwt-validation`); rotacioná-la não traria ganho de segurança, só custo de atualização.

## 2. Corrigir `backend/.env`

- [x] 2.1 Removida a linha `SECRET_KEY` (não referenciada por nenhum código). Confirmado que o app ainda importa/inicia normalmente sem ela.
- [ ] 2.2 Atualizar `SUPABASE_SERVICE_ROLE_KEY` com o valor rotacionado do passo 1.1. **Bloqueado por 1.1.**

## 3. Corrigir `.env` da raiz

- [x] 3.1 Buscado por referências ao `.env` da raiz fora de `.py`/`.ts`: só `backend/docker-compose.yml` (já corrigido na seção 4) e nenhum workflow de CI (`.github/workflows` não existe no repo).
- [x] 3.2 `SUPABASE_URL` corrigida para `tfdripphcwbjiveksuet` (mesmo projeto de `backend/.env`).
- [x] 3.3 `SUPABASE_KEY` e `SUPABASE_ANON_KEY` corrigidas para a chave `anon` real do projeto certo (antes: `SUPABASE_KEY` era uma `service_role` do projeto errado).
- [x] 3.4 Removidos `JWT_SECRET`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DATABASE_URL`, `SUPABASE_DB_HOST/PORT/NAME/USER` (confirmado, nenhum usado por código).
- [x] 3.5 Removida a linha comentada `//SUPABASE_SERVICE_ROLE_KEY=...` — como a task 3.1 confirmou que nada além do `docker-compose.yml` dependia deste arquivo (e o compose agora usa `backend/.env`), não há necessidade de preenchê-la.

## 4. Corrigir `backend/docker-compose.yml`

- [x] 4.1 `../.env:/app/.env` → `./.env:/app/.env`.
- [x] 4.2 `env_file: - ../.env` → `env_file: - ./.env`.

## 5. Verificação

- [x] 5.1 Confirmado: `backend/.env` e o `.env` referenciado por `docker-compose.yml` (agora `backend/.env`) apontam para o mesmo projeto (`tfdripphcwbjiveksuet`).
- [ ] 5.2 Reiniciar o backend local com a nova `service_role` e confirmar que `/auth/login` e um endpoint `/admin/*` continuam funcionando. **Bloqueado por 1.1/2.2.** (Confirmado nesta sessão, com a chave *atual* ainda não rotacionada: o app importa e inicia normalmente após a limpeza do `.env` — task 2.1.)
- [ ] 5.3 (Se o Docker estiver disponível) Subir `docker compose up` a partir de `backend/` e confirmar que o container inicializa sem `ValueError`. **Pendente** — não executado nesta sessão (requer Docker Desktop rodando; não verificado se está disponível no ambiente).
- [x] 5.4 Confirmado por busca no repositório: nenhum arquivo de configuração contém mais uma chave `service_role` sob um nome de baixo privilégio (`SUPABASE_KEY`/`SUPABASE_ANON_KEY` agora são `anon` em ambos os `.env`).

## Pendências para retomar depois (rodar `/opsx:apply fix-secrets-hygiene-and-key-separation` após rotacionar a chave)

- Task 1.1: rotacionar a `service_role` no Dashboard.
- Task 2.2: colar o novo valor em `backend/.env`.
- Task 5.2: reiniciar o backend com a chave nova e reconfirmar `/auth/login` + um endpoint `/admin/*`.
- Task 5.3: testar `docker compose up`, se o ambiente tiver Docker disponível.
