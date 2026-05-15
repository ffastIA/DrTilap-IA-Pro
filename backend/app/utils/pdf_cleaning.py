# backend/app/utils/pdf_cleaning.py

import re
from typing import List
from collections import Counter, defaultdict
from langchain_core.documents import Document


# Constantes para padrões de ruído
NOISE_PATTERNS = [
    r'Bol\.\s*Inst\.\s*Pesca',
    r'^\s*\d+/\s*\d+\s*$',
    r'\bISSN\b',
    r'\bDOI?\b',
    r'https?://',
    r'www\.',
    r'Revista\s+(?:Interdisciplinar|Ci\u00eancia\s+Rural)',
    r'Pakistan\s+Journal\s+Zoology',
]

# Headings de referências
REFERENCE_HEADINGS = [
    r'REFEREN[CES|\\\u00caNCIAS]',
    r'REFER\\\u00caNCIAS',
    r'BIBLIOGRAPHY',
    r'LITERATURE CITED',
]

# Palavras-chave científicas (tilápia e afins)
SCIENTIFIC_KEYWORDS = {
    'tilápia', 'tilápias', 'oreochromis', 'niloticus', 'nilo', 'nilotica',
    'dieta', 'feed', 'feeding', 'restriction', 'restrição',
    'growth', 'desempenho', 'metabolismo', 'metabol', 'histology', 'histologic', 'morphometry',
    'experiment', 'treatment', 'results', 'resultados', 'discussion', 'discussão',
    'conclusion', 'conclusão', 'abstract', 'introduction', 'introdução',
    'materials', 'methods', 'material', 'método', 'metodos',
}


# Normaliza linha: colapsa espaços, strip
def _normalize_line(line: str) -> str:
    line = re.sub(r'\s+', ' ', line.strip())
    # Corrige hifenização simples de quebra de linha
    line = re.sub(r' -([a-zA-Z])', r' \1', line)
    return line


def _normalize_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r' -([a-zA-Z])', r' \1', text)
    return text


def _looks_like_page_counter(line: str) -> bool:
    """Detecta paginação como 1/12"""
    return bool(re.match(r'^\s*\d+/\s*\d+\s*$', line))


def _looks_like_editorial_line(line: str) -> bool:
    """Detecta linhas editoriais, títulos em maiúscula, ABSTRACT isolado"""
    if len(line) < 50:
        upper_ratio = sum(c.isupper() for c in line) / max(len(line), 1)
        if upper_ratio > 0.6:
            return True
    line_upper = line.upper()
    if any(kw in line_upper for kw in ['ABSTRACT', 'KEYWORDS:', 'PALAVRAS-CHAVE:', 'RESUMO']):
        return True
    return bool(re.search('|'.join(NOISE_PATTERNS), line, re.I))


def _looks_like_reference_heading(line: str) -> bool:
    """Detecta inícios de seções de referências"""
    return bool(re.search('|'.join(REFERENCE_HEADINGS), line, re.I))


def _looks_like_reference_line(line: str) -> bool:
    """Heurística para linhas de referência: autores, ano, journal, DOI"""
    line_lower = line.lower()
    if re.search(r'\b\d{4}\b', line) and len(line.split(',')) > 1:
        return True
    if any(p in line_lower for p in ['doi:', 'http', 'www.', 'issn']):
        return True
    # Muitos iniciais maiúsculos (autores)
    initials = sum(1 for c in line if c.isupper())
    words = len(line.split())
    if words > 5 and initials / max(words, 1) > 0.3:
        return True
    return False


def _line_scientific_score(line: str) -> float:
    """Pontuação científica por linha"""
    line_lower = line.lower()
    words = line.split()
    sci_matches = sum(1 for kw in SCIENTIFIC_KEYWORDS if kw in line_lower)
    score = sci_matches / max(len(words), 1)
    # Bônus para números com unidades
    if re.search(r'\d+(?:\.\d+)?\s*(?:%|mg|kg|cm|g|mm|°C)', line):
        score += 0.3
    return score


def _text_scientific_score(text: str) -> float:
    """Pontuação científica média do texto"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return 0.0
    total_score = sum(_line_scientific_score(line) for line in lines)
    return total_score / len(lines)


def contains_scientific_signal(text: str) -> bool:
    """Verifica sinal científico forte (keywords ou dados numéricos)"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in SCIENTIFIC_KEYWORDS):
        return True
    if re.search(r'\b(?:experiment|treatment|result|dieta|growth|tilápia|metabolismo|desempenho)\b', text_lower):
        return True
    # Dados quantitativos
    if re.search(r'\d+(?:\.\d+)?\s*(?:%|g|kg|cm|mm|\d+)', text):
        return True
    return _text_scientific_score(text) > 0.1


def is_editorial_or_low_value(text: str) -> bool:
    """Classifica texto como editorial ou baixo valor"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return True
    ref_lines = sum(_looks_like_reference_line(l) for l in lines)
    if ref_lines / len(lines) > 0.5:
        return True
    noise_matches = sum(1 for line in lines if any(re.search(p, line, re.I) for p in NOISE_PATTERNS))
    if noise_matches / len(lines) > 0.4:
        return True
    sci_score = _text_scientific_score(text)
    if sci_score < 0.05 and len(text) < 200:
        return True
    return False


def clean_loaded_pages(docs: List[Document]) -> List[Document]:
    """Limpa páginas de PDF: remove ruído repetido, editorial, refs, preserva ciência"""
    if not docs:
        return []

    # Extrai linhas normalizadas de todas páginas
    page_lines: List[List[str]] = []
    all_lines_counter = Counter()
    for doc in docs:
        text = doc.page_content
        lines = [_normalize_line(l) for l in text.split('\n') if (norm := _normalize_line(l))]
        page_lines.append(lines)
        all_lines_counter.update(lines)

    # Linhas ruidosas repetidas (em >=2 páginas e curtas/padrão noise)
    repeated_noise_lines = {
        line for line, count in all_lines_counter.items()
        if count >= 2 and (len(line) < 60 or any(re.search(p, line, re.I) for p in NOISE_PATTERNS))
    }

    cleaned_docs = []
    for i, doc in enumerate(docs):
        lines = page_lines[i]
        cleaned_lines = []
        in_references = False
        ref_count = 0
        total_lines = len(lines)

        for line in lines:
            if not line:
                continue
            if line in repeated_noise_lines:
                continue
            if _looks_like_page_counter(line):
                continue
            if _looks_like_editorial_line(line):
                continue

            if _looks_like_reference_heading(line):
                in_references = True
            if in_references and _looks_like_reference_line(line):
                ref_count += 1
                continue
            if not in_references and _line_scientific_score(line) > 0 or len(line) > 15:
                cleaned_lines.append(line)

        # Texto limpo
        cleaned_text = '\n'.join(cleaned_lines)
        cleaned_text = _normalize_text(cleaned_text)

        # Descartar se densidade refs alta ou vazio/sem ciência
        if ref_count / max(total_lines, 1) > 0.6:
            cleaned_text = ''
        if len(cleaned_text) < 100 or not contains_scientific_signal(cleaned_text):
            continue

        new_doc = Document(
            page_content=cleaned_text,
            metadata=doc.metadata
        )
        cleaned_docs.append(new_doc)

    return cleaned_docs
