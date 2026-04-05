import os


def gerar_relatorio(diretorio_raiz, arquivo_saida, extensoes=None):
    """
    extensoes: tupla/lista de extensões, ex: ('.py', '.js', '.ts')
    se extensoes for None, pega todos os arquivos
    """
    if extensoes is not None:
        extensoes = tuple(extensoes)

    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(f"Conteúdo completo do diretório: {os.path.basename(diretorio_raiz)}\n")
        f.write("=" * 80 + "\n\n")

        for root, dirs, files in os.walk(diretorio_raiz):
            # Ignora diretórios que começam com "."
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            rel_path = os.path.relpath(root, diretorio_raiz)
            f.write(f"Diretório: {rel_path if rel_path != '.' else diretorio_raiz}\n")
            f.write("-" * 50 + "\n")

            for file in sorted(files):
                if extensoes is not None and not file.endswith(extensoes):
                    continue

                caminho_completo = os.path.join(root, file)
                caminho_rel = os.path.relpath(caminho_completo, diretorio_raiz)
                f.write(f"\nArquivo: {caminho_rel}\n")
                f.write("Conteúdo:\n")
                try:
                    with open(caminho_completo, 'r', encoding='utf-8') as arquivo:
                        conteudo = arquivo.read()
                        f.write(conteudo)
                except UnicodeDecodeError:
                    f.write("[Erro: arquivo binário ou encoding inválido - conteúdo omitido]\n")
                except Exception as e:
                    f.write(f"[Erro ao ler: {str(e)}]\n")
                f.write("\n" + "=" * 50 + "\n")


# Uso
diretorio = r'C:\Users\usuario\Python\DrTilapIA'
extensoes_desejadas = ('.py',)
nome_saida = f"{os.path.basename(diretorio)}_relatorio_completo.txt"

gerar_relatorio(diretorio, nome_saida, extensoes=extensoes_desejadas)
print(f"Relatório gerado: {nome_saida}")