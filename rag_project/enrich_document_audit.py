from pathlib import Path
import pandas as pd

INPUT = Path('metadata/auditoria/auditoria_corpus.csv')
OUTPUT = Path('metadata/auditoria/auditoria_corpus_classificacao_ABCD.csv')
SUMMARY = Path('metadata/auditoria/resumo_qualidade_documental_por_pais.csv')

STRUCTURAL_FILES = {
    'brasil_referencial-saberes-digitais-docentes_2024.pdf',
    'brasil_matriz-saberes-digitais-docentes_2024.pdf',
}

GROUP_B_TOKENS = (
    'bncc',
    'k12-computer-science-framework',
    'keris-white-paper',
    'hong-kong',
    'plan-ceibal',
    'high-school-curriculum-guidelines',
    'high-school-information-commentary',
)


def classify(row: pd.Series) -> str:
    filename = Path(str(row['arquivo'])).name.lower()
    status = str(row['status']).upper()
    pages = int(row['paginas'])
    pct = float(row['percentual_problematico'])

    if filename in STRUCTURAL_FILES:
        return 'Grupo D'
    if status == 'OCR_NEEDED':
        return 'Grupo C'
    if status == 'LAYOUT_COMPLEXO' or (pages >= 100 and pct >= 3):
        return 'Grupo B'
    if any(token in filename for token in GROUP_B_TOKENS):
        return 'Grupo B'
    return 'Grupo A'


def main():
    df = pd.read_csv(INPUT)
    df['grupo_analitico'] = df.apply(classify, axis=1)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False, encoding='utf-8-sig')

    summary = df.groupby('pais').agg(
        documentos=('arquivo', 'count'),
        paginas_totais=('paginas', 'sum'),
        paginas_problematicas=('paginas_problematicas', 'sum'),
    ).reset_index()
    summary['percentual_paginas_problematicas'] = (
        100 * summary['paginas_problematicas'] / summary['paginas_totais'].where(summary['paginas_totais'] > 0, 1)
    )
    for group in ('Grupo A', 'Grupo B', 'Grupo C', 'Grupo D'):
        counts = df[df['grupo_analitico'] == group].groupby('pais').size()
        summary[group] = summary['pais'].map(counts).fillna(0).astype(int)
    summary.sort_values('pais').to_csv(SUMMARY, index=False, encoding='utf-8-sig')

    print('Auditoria enriquecida:', OUTPUT)
    print('Resumo por país/fonte:', SUMMARY)
    print(df['grupo_analitico'].value_counts().sort_index())


if __name__ == '__main__':
    main()
