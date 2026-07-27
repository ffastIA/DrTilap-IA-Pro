## Context

Estado verificado no código e no banco:

- `rag_service.py:70-74`: `OpenAIEmbeddings(openai_api_key=..., http_client=..., http_async_client=...)` — **sem `model=`**, caindo no default `text-embedding-ada-002` (1536 dims).
- `rag_service.py:89-93`: `RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=500, separators=["\n\n", "\n", ". ", " ", ""])` — hardcoded.
- `rag_service.py:134`: `split_documents(cleaned_docs)` onde cada `Document` é **uma página** → o split reinicia a cada página.
- `rag_service.py:141-143`: apenas `original_file_id` e `original_file_name` são adicionados ao metadata. `chunk_index` não existe em lugar nenhum (0/49 no banco).
- Banco: 49 chunks, 4 arquivos, `vector_dims` = 1536 uniformes. Comprimento de conteúdo: mín 219 / médio 1900 / máx 3982 — a dispersão confirma o chunking por página (páginas curtas viram chunks curtos).
- Não existem colunas `page` nem `chunk_index` na tabela, embora `vector_admin_repository.py:108-112` as leia (sempre `None`).

Restrição incontornável: embeddings de modelos diferentes ocupam espaços vetoriais distintos. Não existe migração incremental — ou a base inteira é reindexada com o modelo novo, ou as similaridades ficam sem significado.

## Goals / Non-Goals

**Goals:**
- Recuperar chunks mais precisos para a mesma pergunta, comprovado por medição contra a linha de base.
- Tornar as escolhas de modelo e chunking **explícitas e versionadas**, para que uma regressão como a atual não possa acontecer em silêncio de novo.
- Habilitar rastreabilidade por chunk (posição e página), pré-requisito da citação de fontes.

**Non-Goals:**
- Não mexe em threshold, `k`, reranking, prompts ou montagem de contexto — isso é a mudança seguinte, e deliberadamente separada para que o efeito de cada uma seja medível isoladamente.
- Não implementa upload do PDF original para o Storage (fica para a mudança de robustez), embora a ausência disso seja o que torna esta mudança dependente de o usuário ter os arquivos.
- Não muda o OCR nem o parsing de PDF.

## Decisions

1. **`text-embedding-3-large` com `dimensions=1536`.** Os modelos v3 suportam redução de dimensão (Matryoshka), e o `3-large` truncado em 1536 supera tanto o `ada-002` quanto o `3-small` na mesma dimensionalidade. Escolhido por isso: **cabe no schema `vector(1536)` atual, sem migração de coluna nem de índice**, e ainda assim entrega a melhor qualidade de recuperação disponível. O custo adicional é irrelevante aqui — a base é minúscula e a query são ~20 tokens.
   - Alternativa considerada: `3-large` em 3072 dims nativos. Rejeitada por exigir `ALTER COLUMN` e recriação do índice HNSW em troca de ganho marginal neste acervo.
   - Alternativa considerada: `3-small`. Seria suficiente e mais barato, mas como o volume é irrisório, não há motivo para não pegar a qualidade melhor.

2. **`chunk_size=1200`, `chunk_overlap=200`.** Restaura a ordem de grandeza da versão que funcionava (1000/200), com folga para tabelas científicas que ficariam truncadas em 1000. A relação overlap/size (~17%) é conservadora e evita a redundância excessiva do 500/4000 atual.

3. **Ambos configuráveis por variável de ambiente, com o valor efetivo registrado em log na inicialização.** Esta é a decisão que impede a repetição do bug: hoje o serviço loga o `similarity_threshold` mas não o modelo de embedding nem o chunking, então a regressão passou despercebida por meses. O log de inicialização deve dizer qual modelo está em uso de fato.

4. **Chunking contínuo com rastreamento de página.** Concatenar as páginas do documento antes do split, mantendo um mapa de deslocamento → página, para atribuir a cada chunk a página inicial e final. Resolve o problema de conteúdo partido na quebra de página **sem** perder a rastreabilidade que a citação de fontes vai precisar.
   - Alternativa considerada: manter por página e apenas aumentar o overlap. Rejeitada — overlap não atravessa documentos distintos, que é exatamente o que cada página é hoje para o splitter.

5. **Metadados em JSONB e em colunas top-level.** O `vector_admin_repository` já lê `page` e `chunk_index` como colunas; o LangChain só escreve JSONB. Popular ambos resolve o descompasso sem reescrever o repositório. As colunas passam a existir de fato.

6. **A verificação é comparativa, não absoluta.** O critério de sucesso é a melhora das métricas de recuperação contra a linha de base registrada pela mudança `add-rag-evaluation-harness` — não uma impressão de que "as respostas parecem melhores".

## Risks / Trade-offs

- **[Risco] Reingestão é destrutiva e sem volta.** Limpar a base antes de reingerir significa que, se a reingestão falhar no meio, fica-se sem base. → Mitigação: confirmar que os 4 PDFs estão em mãos e legíveis **antes** de limpar; reingerir um documento e validar antes de processar os demais.
- **[Risco] `original_file_id = MD5(nome do arquivo)`** faz com que reingerir o mesmo nome seja bloqueado por `_check_file_exists`. Depois de limpar a base isso não bloqueia, mas se a limpeza for parcial, sim. → Mitigação: confirmar base zerada antes de reingerir. A correção definitiva (hash de conteúdo) está na mudança de robustez.
- **[Risco] Falha parcial de ingestão deixa o arquivo preso pela metade** (sem transação; `_check_file_exists` passa a dizer `already_exists`). → Mitigação: verificar a contagem de chunks por arquivo após cada ingestão; se divergir, excluir o arquivo pelo admin e reingerir.
- **[Risco] `clean_reindex_service.py` duplica os parâmetros de chunking e cria seu próprio cliente de embeddings sem o `http_client` do projeto** — se não for atualizado junto, reintroduz a divergência (e ignora a resolução de TLS do projeto). → Mitigação: tratá-lo explicitamente como parte desta mudança, não como detalhe.
- **[Trade-off] Chunks menores significam mais chunks e mais linhas** — mais chamadas de embedding na ingestão e um `k` que talvez precise subir para cobrir a mesma quantidade de texto. Aceito: é exatamente o trade-off que dá precisão. O ajuste de `k` fica para a mudança de recuperação, que é quem mede.
- **[Incerteza] O ganho não está garantido.** A hipótese de que chunk menor + modelo v3 melhora a recuperação é fortemente fundamentada, mas **precisa ser comprovada** neste acervo. Se a medição não mostrar melhora, a decisão deve ser revista em vez de racionalizada.

## Migration Plan

1. Implementar as mudanças de código (modelo, chunking, metadados) sem executar reingestão.
2. Adicionar as colunas de rastreabilidade no banco.
3. Confirmar que os 4 PDFs originais estão disponíveis.
4. Limpar a base vetorial (operação destrutiva, com confirmação explícita).
5. Reingerir os documentos um a um, validando a contagem de chunks a cada um.
6. Rodar o harness de avaliação e comparar com a linha de base.

Rollback: reverter o código por git e reingerir com a configuração anterior. Como os vetores são descartáveis e os originais estão preservados, o rollback é sempre possível — **desde que os PDFs originais continuem disponíveis**.

## Open Questions

- Chunks menores podem exigir aumentar o `k` de recuperação (hoje 20) para cobrir a mesma extensão de texto. A decisão fica para a mudança de recuperação, que tem a medição para fundamentá-la — mas convém observar o efeito já na verificação desta.
