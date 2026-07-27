## 1. Pré-requisitos (antes de qualquer coisa destrutiva)

- [ ] 1.1 Confirmar que a linha de base do harness (`add-rag-evaluation-harness`) existe e está salva. Sem ela não há como provar que esta mudança funcionou.
- [ ] 1.2 Confirmar com o usuário que os **4 PDFs originais** estão disponíveis e legíveis: `Genetic and phenotypic characterization of Nile tilapia.pdf`, `BIP 2024 publicado.pdf`, `Indice volumetrico abate.pdf`, `BIA_RAG.pdf`. Só 3 estão em `backend/docs/` — o `BIP 2024` precisa ser localizado.
- [ ] 1.3 Fazer um dump de segurança do conteúdo atual (`SELECT content, metadata FROM documents`) antes de limpar — permite reconstruir o golden set se algo der errado.

## 2. Configuração explícita

- [ ] 2.1 Adicionar `EMBEDDING_MODEL` (default `text-embedding-3-large`), `EMBEDDING_DIMENSIONS` (default `1536`), `CHUNK_SIZE` (default `1200`) e `CHUNK_OVERLAP` (default `200`) em `backend/.env.example`, com comentários explicando o porquê de cada valor.
- [ ] 2.2 Definir as mesmas variáveis em `backend/.env`.
- [ ] 2.3 `rag_service.py`: passar `model=` e `dimensions=` explicitamente ao `OpenAIEmbeddings`, lendo das variáveis.
- [ ] 2.4 `rag_service.py`: ler `chunk_size`/`chunk_overlap` das variáveis no `RecursiveCharacterTextSplitter`.
- [ ] 2.5 Estender o log de inicialização (hoje só mostra `similarity_threshold`) para registrar **modelo de embedding, dimensões, chunk_size e chunk_overlap efetivos**. É esta linha que teria denunciado a regressão original.

## 3. Chunking contínuo com rastreamento de página

- [ ] 3.1 Substituir `split_documents(cleaned_docs)` (que trata cada página como documento independente) por: concatenar o texto das páginas mantendo um mapa de deslocamento → número de página.
- [ ] 3.2 Fazer o split sobre o texto contínuo e, para cada chunk, derivar a página inicial e final a partir do mapa de deslocamentos.
- [ ] 3.3 Confirmar que o overlap agora atravessa a fronteira de página (inspecionar dois chunks consecutivos que cruzam uma quebra).
- [ ] 3.4 Manter o filtro de chunks curtos existente (`_filter_chunks`, < 120 chars).

## 4. Metadados de rastreabilidade

- [ ] 4.1 Adicionar `chunk_index` (ordinal dentro do documento) ao metadata de cada chunk.
- [ ] 4.2 Adicionar `page_start`/`page_end` (ou `page` quando iguais) ao metadata.
- [ ] 4.3 Criar as colunas `page` e `chunk_index` em `public.documents` — o `vector_admin_repository.py:108-112` já as lê e hoje sempre recebe `None`.
- [ ] 4.4 Popular as colunas top-level além do JSONB. O `SupabaseVectorStore` do LangChain só escreve JSONB, então isso exige um passo adicional após o `add_documents` (ou uma via de inserção própria).
- [ ] 4.5 Confirmar que `original_file_id` e `original_file_name` continuam sendo populados nas colunas top-level (hoje estão 49/49, por backfill anterior — a ingestão nova precisa manter isso).

## 5. Alinhar o caminho de reindexação

- [ ] 5.1 `clean_reindex_service.py:25-26` duplica `chunk_size`/`chunk_overlap` — passar a usar a mesma configuração central.
- [ ] 5.2 `clean_reindex_service.py:16` constrói `OpenAIEmbeddings(...)` **sem `http_client`**, ignorando a resolução de TLS do projeto (`_resolve_ssl_verify`) — corrigir, sob pena de falhar em ambientes com proxy de inspeção TLS.
- [ ] 5.3 Confirmar que os dois caminhos produzem chunks equivalentes para o mesmo documento.

## 6. Reingestão (destrutivo — só depois de 1.x e 2-5 concluídos)

- [ ] 6.1 Limpar a base vetorial (`POST /admin/vector-base/cleanup` com confirmação real) e **confirmar que ficou zerada** (`SELECT count(*) FROM documents` = 0) — se sobrar linha, `_check_file_exists` bloqueará a reingestão por causa do MD5 do nome.
- [ ] 6.2 Reingerir **um** documento e validar: contagem de chunks coerente com o tamanho do PDF, `chunk_index` sequencial, `page` preenchido, dimensão do embedding = 1536.
- [ ] 6.3 Reingerir os demais, validando a contagem a cada um (falha parcial não é tratada — se divergir, excluir e reingerir aquele arquivo).
- [ ] 6.4 Confirmar `vector_dims` uniforme em toda a base e nenhuma linha sem embedding.

## 7. Verificação

- [ ] 7.1 Rodar o harness completo e **comparar com a linha de base**: recall dos trechos esperados e similaridade do melhor chunk devem melhorar.
- [ ] 7.2 Registrar os números obtidos no `design.md` desta mudança, ao lado dos da linha de base.
- [ ] 7.3 **Se não houver melhora**, não aceitar a mudança: revisar `chunk_size` (testar 800 e 1600) e reavaliar antes de dar por concluída. A hipótese é bem fundamentada mas não é garantida.
- [ ] 7.4 Verificar se chunks menores exigem aumentar o `k` (hoje 20) para cobrir a mesma extensão de texto — registrar a observação para a mudança de recuperação, sem alterar `k` aqui.
- [ ] 7.5 Confirmar que o chat continua respondendo normalmente de ponta a ponta.
- [ ] 7.6 Confirmar que o admin lista os arquivos corretamente, agora com `page` e `chunk_index` preenchidos.
