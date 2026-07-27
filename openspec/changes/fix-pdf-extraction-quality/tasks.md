## 1. Calibrar os limiares contra dados reais

- [ ] 1.1 **BLOQUEADO (2026-07-27)** — o usuário informou que ainda não dispõe do `BIP 2024 publicado.pdf`. Também falta o `Genetic and phenotypic characterization of Nile tilapia.pdf`. Enquanto não houver os arquivos, as tasks 6.2, 6.3, 6.7, 7.1 e 7.2 permanecem pendentes.
- [x] 1.2 Extrair, para cada um dos 4 documentos, as métricas candidatas por página: palavras por página, caracteres por página, proporção de tokens com 1-2 caracteres, proporção de dígitos.
- [x] 1.3 Limiares escolhidos: `MIN_WORDS_PER_PAGE=120`, `MAX_ISOLATED_NUMBER_RATIO=0.05`, `MAX_SPARSE_PAGE_RATIO=0.5`. **Duas métricas foram testadas e descartadas** (tokens ≤2 char e de 1 char) por não discriminarem — ver decisão 3 corrigida no design. Original: escolher os limiares que separam com folga os 3 documentos íntegros (216-394 palavras/chunk) do BIP 2024 (51). **Limiares conservadores** — o alvo é falha grosseira, não caso limítrofe.
- [x] 1.4 Registrado no design (seção 'Calibração medida'). **Margem obtida**: documentos íntegros entre 0% e 25% de páginas esparsas; BIP 2024 em 92%, contra limiar de 50%.

## 2. Detecção de extração incompleta

- [x] 2.1 Criar a função de avaliação de densidade por página (palavras/página + proporção de tokens órfãos), separada de `_is_text_garbled`, que permanece intacta (decisão 4).
- [x] 2.2 Criar a avaliação em nível de documento: fração de páginas esparsas acima da qual o documento é reprovado.
- [x] 2.3 Integrar a nova avaliação ao critério de aceite de cada estágio da cascata em `_load_pdf_with_fallback` (~linha 196), que hoje aceita por "> 200 caracteres e não garbled".
- [x] 2.4 Endurecer `_validate_pdf_quality` (~linha 373), hoje "> 50 caracteres, > 0 páginas".
- [x] 2.5 **Decidido: medir ANTES da limpeza.** A avaliação roda dentro de `_load_pdf_with_fallback`, que é anterior a `clean_loaded_pages` — é o ponto certo, porque o que se julga é a saída do *extrator*, não do limpador. A remoção de linhas em branco não afeta contagem de palavras, e a de números de página remove poucos tokens. Confirmado empiricamente: os valores medidos nos PDFs reais (BIA_RAG 255, Indice 216 palavras/página) batem com os da calibração feita sobre o conteúdo já armazenado (pós-limpeza).

## 3. Limites de custo do OCR

- [x] 3.1 Adicionar `OCR_MAX_PAGES` (configurável, com default conservador) em `.env.example` e `.env`.
- [x] 3.2 Aplicar o teto ao caminho de Vision (`_extract_text_via_vision`, ~linha 312), que hoje processa páginas em laço serial sem limite algum.
- [x] 3.3 Ultrapassar o teto deve **falhar com motivo explícito**, nunca truncar silenciosamente (decisão 5).
- [x] 3.4 Adicionar timeout por página nas chamadas de Vision (hoje inexistente).
- [x] 3.5 Verificar disponibilidade do Tesseract antes de tentá-lo — o caminho do binário é hardcoded com um usuário específico (`rag_service.py:36-40`); se ausente, a cascata pula para o Vision, que é muito mais caro, e isso precisa ficar registrado em log.

## 4. Registro auditável da qualidade

- [x] 4.1 Gravar `extraction_method` para **todos** os caminhos, inclusive quando o `pypdf` primário funciona — hoje só os caminhos de OCR gravam esse campo.
- [x] 4.2 Gravar as métricas de qualidade obtidas (densidade, proporção de tokens órfãos) nos metadados do documento.
- [x] 4.3 Confirmado: cada chunk passa a carregar `extraction_method` e `extraction_quality` (páginas, palavras totais, média por página, fração de números isolados, páginas esparsas, veredito e motivo). Exemplo real gravado para `Studium.pdf`: `{"pages":1,"total_words":228,"mean_words_per_page":228.0,"mean_isolated_number_ratio":0.0,"sparse_pages":0,"adequate":true}`. **Ressalva**: os 49 chunks já existentes na base não têm esses campos — só documentos ingeridos daqui em diante.

## 5. Falha visível

- [x] 5.1 Quando a cascata se esgotar sem qualidade adequada, retornar erro de ingestão com a causa identificada como qualidade de extração.
- [x] 5.2 Garantir que **nenhum chunk** do documento seja gravado nesse caso — hoje a ingestão não é transacional e uma falha parcial deixa chunks órfãos (a correção definitiva de transacionalidade é da mudança de robustez; aqui basta não gravar quando a extração reprova, o que acontece antes de qualquer escrita).
- [x] 5.3 Propagar a mensagem até a resposta de `POST /admin/upload`, para que o usuário saiba que o documento não entrou e por quê.

## 6. Verificação

- [x] 6.1 **Não-regressão VERIFICADA nos 3 PDFs disponíveis** (`BIA_RAG`, `Indice volumetrico abate`, `Studium`): todos aceitos pelo caminho primário `pypdf`, **sem acionar OCR**, com 216-255 palavras/página. O `Genetic characterization` não pôde ser testado (PDF ausente do repositório), mas sua avaliação sobre o conteúdo armazenado dá 639 palavras/página e 25% de esparsas — bem dentro do aceito. Original: **Não-regressão (o mais importante)**: os 3 documentos íntegros (`Genetic characterization`, `BIA_RAG`, `Indice volumetrico abate`) devem continuar sendo extraídos pelo caminho primário, **sem acionar OCR**. Falso positivo aqui custa tempo e dinheiro em toda ingestão futura.
- [ ] 6.2 **BLOQUEADO por 1.1** (PDF indisponível). Evidência indireta: a avaliação do detector sobre o conteúdo já armazenado desse documento dá 92% de páginas esparsas contra o limiar de 50% — reprova com folga. Falta confirmar rodando sobre o PDF real.
- [ ] 6.3 **BLOQUEADO por 1.1** — e é a questão em aberto mais importante da mudança: **não está provado que o Vision recupera as tabelas desse documento**. Original: verificar se o resgate de fato recupera o conteúdo: as linhas de dados da `Table 1` (weight gain, biomass, FCR, survival) devem passar a existir no texto extraído. **Se não recuperarem**, registrar o resultado honestamente — a mudança ainda entrega valor (falha visível em vez de lixo silencioso), mas o conteúdo continuará indisponível e a questão em aberto do design (tabelas via `pdfplumber.extract_tables()`) precisará ser decidida.
- [x] 6.4 Testado com `OCR_MAX_PAGES=2` sobre um PDF maior: levanta `ExtractionCostLimitExceeded` **antes de processar qualquer página** (o `pdf.close()` acontece antes do laço), com mensagem indicando o número de páginas e o limite. Nenhuma gravação parcial.
- [x] 6.5 Coberto indiretamente pelo teste de falha visível: um PDF sintético esparso percorreu a cascata inteira (`pypdf` → `pdfplumber` → Tesseract → **Vision OCR executou de fato**) antes de ser rejeitado. Confirma que o caminho de OCR está funcional. **Ressalva**: o binário do Tesseract não está instalado (só o wrapper Python), então esse estágio falha graciosamente e escala para o Vision — que é mais caro. Vale instalar o binário se o custo importar.
- [x] 6.6 `Studium.pdf`: aceito pelo `pypdf` com 228 palavras/página e 0% de páginas esparsas — decisão sensata, nenhum OCR desnecessário.
- [ ] 6.7 **Parcialmente observado**: o teste sintético de 6 páginas percorreu o Vision OCR completo. Custo e tempo exatos não foram instrumentados — fazer com um documento real quando o BIP 2024 estiver disponível.

## 7. Reingestão do documento afetado

- [ ] 7.1 **BLOQUEADO por 1.1.** Original: a reingestão do `BIP 2024` acontece na mudança `restore-embedding-and-chunking-quality`, que já prevê limpar e recarregar a base. **Coordenar a ordem**: esta mudança precisa estar aplicada antes daquela reingestão, senão o documento entrará quebrado de novo.
- [ ] 7.2 **BLOQUEADO por 7.1.** Original: após a reingestão, acrescentar perguntas sobre o BIP 2024 ao `golden_set.yaml` (hoje excluído por não haver conteúdo recuperável) e revalidar com `validate_golden_set.py`.
