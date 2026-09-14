from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "analysis" / "official_run_20260912"

COUNTRIES = [
    "africa-do-sul","australia","brasil","canada","chile","china",
    "coreia-do-sul","estonia","eua","finlandia","gana","hong-kong",
    "irlanda","japao","nova-zelandia","quenia","reino-unido","ruanda",
    "singapura","suica","taiwan","uruguai",
]

EXPECTED_QUESTIONS = {f"Q{i:02d}" for i in range(1, 14)}


def build(run_dir: Path):
    rows = []
    issues = []

    for country in COUNTRIES:
        rfile = run_dir / country / "respostas.csv"
        efile = run_dir / country / "evidencias.csv"

        if not rfile.exists() or not efile.exists():
            issues.append({
                "country": country,
                "question_id": "",
                "issue": "missing_input_file"
            })
            continue

        r = pd.read_csv(rfile)
        e = pd.read_csv(efile)

        for _, rr in r.iterrows():
            qid = str(rr.get("question_id", ""))

            if qid not in EXPECTED_QUESTIONS:
                continue

            ee = e[e["question_id"].astype(str).eq(qid)]

            evidence_ids = (
                ee["evidence_id"]
                .dropna()
                .astype(str)
                .tolist()
                if not ee.empty else []
            )

            document_ids = sorted({
                str(v).strip()
                for v in ee["document_id"].dropna().tolist()
                if str(v).strip()
            }) if not ee.empty else []

            pages = []

            if not ee.empty:
                for _, er in ee.iterrows():
                    doc = str(er.get("document_id", "")).strip()
                    p1 = er.get("page_start", "")
                    p2 = er.get("page_end", "")

                    if pd.isna(p1) or not str(p1).strip():
                        continue

                    try:
                        p1txt = str(int(float(p1)))
                    except Exception:
                        p1txt = str(p1)

                    if (
                        pd.notna(p2)
                        and str(p2).strip()
                        and str(p2) != str(p1)
                    ):
                        try:
                            p2txt = str(int(float(p2)))
                        except Exception:
                            p2txt = str(p2)

                        pages.append(f"{doc}:p{p1txt}-{p2txt}")
                    else:
                        pages.append(f"{doc}:p{p1txt}")

            status = str(
                rr.get("validation_status", "")
            ).strip().lower()

            if status == "candidate" and len(ee) == 0:
                issues.append({
                    "country": country,
                    "question_id": qid,
                    "issue": "candidate_without_evidence"
                })

            rows.append({
                "country": country,
                "question_id": qid,
                "question_text": rr.get("question_text", ""),
                "response": rr.get("response", ""),
                "validation_status": status,
                "evidence_count": len(ee),
                "evidence_ids": "; ".join(evidence_ids),
                "document_ids": "; ".join(document_ids),
                "pages": "; ".join(pages),
                "response_id": rr.get("response_id", ""),
                "run_id": rr.get("run_id", ""),
                "prompt_version": rr.get("prompt_version", ""),
                "question_version": rr.get("question_version", ""),
            })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(
            ["question_id", "country"]
        ).reset_index(drop=True)

    issues_df = pd.DataFrame(
        issues,
        columns=["country", "question_id", "issue"]
    )

    return df, issues_df


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Constrói a base consolidada Q01-Q13 "
            "para a comparação internacional Q14."
        )
    )

    ap.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN)
    )

    args = ap.parse_args()

    run_dir = Path(args.run_dir)

    out_dir = run_dir / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)

    df, issues = build(run_dir)

    output = out_dir / "q14_input.csv"
    audit = out_dir / "q14_input_issues.csv"

    df.to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    issues.to_csv(
        audit,
        index=False,
        encoding="utf-8-sig"
    )

    print("Linhas:", len(df))
    print(
        "Países:",
        df["country"].nunique() if not df.empty else 0
    )
    print(
        "Perguntas:",
        df["question_id"].nunique() if not df.empty else 0
    )
    print(
        "Candidates:",
        (df["validation_status"] == "candidate").sum()
        if not df.empty else 0
    )
    print(
        "Inconclusive:",
        (df["validation_status"] == "inconclusive").sum()
        if not df.empty else 0
    )
    print("Problemas:", len(issues))
    print("Arquivo:", output)
    print("Auditoria:", audit)


if __name__ == "__main__":
    main()
