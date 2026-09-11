#!/usr/bin/env python3
"""
extrai_trechos_tfidf.py
Gera evidências citáveis para os termos do TF-IDF, localizando cada termo
no texto de origem e extraindo uma janela de contexto (concordância / KWIC).

Uso:
  python extrai_trechos_tfidf.py \
      --tfidf corpus/analysis_output/group_tfidf.csv \
      --dataset corpus/dataset_output/dataset_english.jsonl \
      --field english_text \
      --out corpus/analysis_output/evidencias_tfidf.csv \
      --top 10 --janela 160

Observações:
- Para casar com o termo do TF-IDF (que é normalizado: sem acento, minúsculo,
  uni/bigrama), a busca é feita sobre uma versão normalizada do texto, mas o
  trecho devolvido é o texto ORIGINAL (com acentos), para citação fiel.
- Se o termo for um bigrama ("digital systems"), aceita também pequena variação
  de espaços/pontuação entre as duas palavras.
- Se o termo não for encontrado (existe só na forma tokenizada), a linha é
  marcada como NAO_LOCALIZADO para conferência manual (abrir o PDF e usar Ctrl+F).
"""
from __future__ import annotations
import argparse, csv, json, re, unicodedata
from pathlib import Path


def strip_accents(s: str) -> str:
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', strip_accents(s).lower())


def group_name(rec: dict) -> str:
    if rec.get('dataset_group') == 'unesco':
        return 'UNESCO'
    if rec.get('dataset_group') == 'pisa':
        return 'PISA/OECD'
    return rec.get('country') or 'Sem pais'


def load_group_texts(dataset_path: Path, field: str):
    """Concatena, por grupo, os textos originais e uma versao normalizada paralela."""
    originals = {}   # group -> lista de (doc, texto_original)
    for line in dataset_path.open(encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        text = (rec.get(field) or rec.get('source_text') or '').strip()
        if not text:
            continue
        g = group_name(rec)
        originals.setdefault(g, []).append((rec.get('document', ''), text))
    return originals


def build_bigram_pattern(term: str) -> re.Pattern:
    """Padrao tolerante: entre as palavras do termo aceita espacos/pontuacao/quebra."""
    parts = term.split()
    escaped = [re.escape(p) for p in parts]
    # entre tokens: qualquer nao-letra (espaco, pontuacao, hifen, nova linha)
    joined = r'[^a-z0-9]{1,4}'.join(escaped)
    return re.compile(joined, flags=re.IGNORECASE)


def find_snippet(term: str, docs: list[tuple[str, str]], janela: int):
    """Procura o termo (normalizado) nos documentos do grupo; devolve (doc, trecho_original)."""
    pat = build_bigram_pattern(strip_accents(term))
    for doc, original in docs:
        norm = normalize(original)
        m = pat.search(norm)
        if not m:
            continue
        # mapear posicao aproximada no texto original: usamos o mesmo indice,
        # pois strip_accents preserva o comprimento na maioria dos casos.
        start = max(0, m.start() - janela // 2)
        end = min(len(original), m.end() + janela // 2)
        trecho = original[start:end].replace('\n', ' ')
        trecho = re.sub(r'\s+', ' ', trecho).strip()
        # aparar nas bordas para nao cortar no meio de palavra
        trecho = re.sub(r'^\S*\s', '', trecho)
        trecho = re.sub(r'\s\S*$', '', trecho)
        return doc, f'...{trecho}...'
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tfidf', default='corpus/analysis_output/group_tfidf.csv')
    ap.add_argument('--dataset', default='corpus/dataset_output/dataset_english.jsonl')
    ap.add_argument('--field', default='english_text', choices=['english_text', 'source_text'])
    ap.add_argument('--out', default='corpus/analysis_output/evidencias_tfidf.csv')
    ap.add_argument('--top', type=int, default=10, help='quantos termos por grupo (por rank)')
    ap.add_argument('--janela', type=int, default=160, help='caracteres de contexto ao redor do termo')
    args = ap.parse_args()

    group_texts = load_group_texts(Path(args.dataset), args.field)

    rows_out = []
    with Path(args.tfidf).open(encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if int(row.get('rank', 999)) > args.top:
                continue
            group = row['group']
            term = row['term']
            docs = group_texts.get(group, [])
            doc, snippet = (None, None)
            if docs:
                doc, snippet = find_snippet(term, docs, args.janela)
            rows_out.append({
                'grupo': group,
                'rank': row.get('rank', ''),
                'termo': term,
                'tfidf': row.get('tfidf', ''),
                'documento_fonte': doc or '',
                'trecho': snippet or 'NAO_LOCALIZADO (existe apenas na forma tokenizada; conferir no PDF via Ctrl+F)',
            })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['grupo', 'rank', 'termo', 'tfidf', 'documento_fonte', 'trecho'])
        w.writeheader()
        w.writerows(rows_out)

    achou = sum(1 for r in rows_out if not r['trecho'].startswith('NAO_LOCALIZADO'))
    print(f'Evidencias geradas: {out}')
    print(f'Termos processados: {len(rows_out)} | com trecho: {achou} | sem trecho: {len(rows_out)-achou}')


if __name__ == '__main__':
    main()
