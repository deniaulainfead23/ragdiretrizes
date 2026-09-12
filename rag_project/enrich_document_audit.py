from pathlib import Path
import pandas as pd

INPUT = Path('metadata/auditoria/auditoria_corpus.csv')
OUTPUT = Path('metadata/auditoria/auditoria_corpus_classificacao_ABCD.csv')


def classify(status: str, pct: float) -> str:
    status = str(status).upper()
    if status == 'OCR_NEEDED':
        return 'Grupo C'
    if status == 'LAYOUT_COMPLEXO' or float(pct) > 20:
        return 'Grupo B'
    return 'Grupo A'


def main():
    df = pd.read_csv(INPUT)
    df['grupo_analitico'] = [classify(s, p) for s, p in zip(df['status'], df['percentual_problematico'])]
    df.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
    print(df['grupo_analitico'].value_counts())


if __name__ == '__main__':
    main()
