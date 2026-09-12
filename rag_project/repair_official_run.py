from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "analysis" / "official_run_20260912"
CONTENT_JSONL = ROOT / "data" / "conteudos.jsonl"


def _norm(text: object) -> str:
    s = str(text or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _load_content_index(path: Path) -> dict[str, list[dict]]:
    by_doc: dict[str, list[dict]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            by_doc.setdefault(str(r.get("document_id", "")), []).append(r)
    return by_doc


def _locate_page(source_text: str, document_id: str, idx: dict[str, list[dict]]) -> tuple[object, object, str, str]:
    needle = _norm(source_text)
    if not needle or document_id not in idx:
        return "", "", "", "not_found"

    # 1) correspondência direta normalizada
    for r in idx[document_id]:
        hay = _norm(r.get("source_text", ""))
        if needle in hay or hay in needle:
            return r.get("page_start", ""), r.get("page_end", ""), r.get("chunk_id", ""), "exact_normalized"

    # 2) fallback por janela inicial/final para tolerar OCR/acentuação quebrada
    tokens = needle.split()
    if len(tokens) >= 8:
        anchors = [" ".join(tokens[:8]), " ".join(tokens[-8:])]
        for r in idx[document_id]:
            hay = _norm(r.get("source_text", ""))
            if all(a in hay for a in anchors if a):
                return r.get("page_start", ""), r.get("page_end", ""), r.get("chunk_id", ""), "anchors"

    return "", "", "", "not_found"


def _extract_embedded_json(text: object) -> dict:
    s = str(text or "").strip()
    if not s.startswith("{"):
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def repair(run_dir: Path, content_jsonl: Path) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = run_dir / "repair_backup" / ts
    backup.mkdir(parents=True, exist_ok=True)
    log_rows: list[dict] = []
    idx = _load_content_index(content_jsonl)

    for country_dir in sorted(p for p in run_dir.iterdir() if p.is_dir() and p.name not in {"audit", "repair_backup"}):
        rfile = country_dir / "respostas.csv"
        efile = country_dir / "evidencias.csv"
        if not rfile.exists() or not efile.exists():
            continue

        shutil.copy2(rfile, backup / f"{country_dir.name}__respostas.csv")
        shutil.copy2(efile, backup / f"{country_dir.name}__evidencias.csv")

        r = pd.read_csv(rfile)
        e = pd.read_csv(efile)

        # A) recuperar evidências que ficaram embutidas no campo response quando o parser falhou
        for ridx, rr in r.iterrows():
            qid = str(rr.get("question_id", ""))
            current = e[e["question_id"].astype(str).eq(qid)] if not e.empty else pd.DataFrame()
            if not current.empty:
                continue

            obj = _extract_embedded_json(rr.get("response", ""))
            evs = obj.get("evidences", []) if obj else []
            if not isinstance(evs, list) or not evs:
                continue

            new_rows = []
            ids = []
            for pos, ev in enumerate(evs, 1):
                if not isinstance(ev, dict):
                    continue
                raw_doc = str(ev.get("document_id") or "")
                doc = raw_doc.split("__", 1)[0]
                ps = ev.get("page_start", "")
                pe = ev.get("page_end", "") or ps
                chunk = ev.get("chunk_id") or (f"{doc}_p{int(ps):04d}_c001" if str(ps).isdigit() else "")
                evid = f"EVID_{country_dir.name.upper().replace('-', '_')}_{qid}_{doc.upper().replace('-', '_')}_P{int(ps):04d}_{pos:03d}" if str(ps).isdigit() else f"EVID_{country_dir.name.upper().replace('-', '_')}_{qid}_{doc.upper().replace('-', '_')}_PNA_{pos:03d}"
                ids.append(evid)
                new_rows.append({
                    "evidence_id": evid,
                    "run_id": rr.get("run_id", ""),
                    "question_run_id": rr.get("question_run_id", ""),
                    "response_id": rr.get("response_id", ""),
                    "question_id": qid,
                    "category_id": rr.get("category_id", ""),
                    "framework": rr.get("framework", ""),
                    "country": country_dir.name,
                    "document_id": doc,
                    "document_title": ev.get("document_title", ""),
                    "page_start": ps,
                    "page_end": pe,
                    "chunk_id": chunk,
                    "source_language": ev.get("source_language", ""),
                    "source_text": ev.get("source_text", ""),
                    "translated_text_pt": ev.get("translated_text_pt", ""),
                    "translation_status": ev.get("translation_status", ""),
                    "semantic_score": ev.get("semantic_score", ""),
                    "evidence_classification": ev.get("evidence_classification", ""),
                    "validation_status": "candidate" if ev.get("source_text") else "inconclusive",
                    "review_notes": "recovered_from_embedded_json",
                })

            if new_rows:
                e = pd.concat([e, pd.DataFrame(new_rows)], ignore_index=True)
                r.at[ridx, "evidence_ids"] = "; ".join(ids)
                inner_response = str(obj.get("response") or "").strip()
                if inner_response:
                    r.at[ridx, "response"] = inner_response
                    r.at[ridx, "validation_status"] = "candidate"
                else:
                    r.at[ridx, "validation_status"] = "inconclusive"
                    r.at[ridx, "review_notes"] = "embedded_json_recovered_but_response_empty"
                log_rows.append({"country": country_dir.name, "question_id": qid, "action": "recover_embedded_evidences", "details": f"{len(new_rows)} evidencias"})

        # B) completar páginas ausentes a partir do dataset conteudos.jsonl
        if not e.empty:
            for eidx, er in e.iterrows():
                ps = er.get("page_start")
                missing_page = pd.isna(ps) or str(ps).strip() in {"", "0", "nan", "None"}
                if not missing_page:
                    continue
                doc = str(er.get("document_id", "")).strip()
                src = str(er.get("source_text", ""))
                p1, p2, chunk, method = _locate_page(src, doc, idx)
                if p1 != "":
                    e.at[eidx, "page_start"] = p1
                    e.at[eidx, "page_end"] = p2 or p1
                    e.at[eidx, "chunk_id"] = chunk
                    note = str(er.get("review_notes", "") or "")
                    e.at[eidx, "review_notes"] = (note + "; " if note else "") + f"page_recovered:{method}"
                    log_rows.append({"country": country_dir.name, "question_id": er.get("question_id", ""), "action": "recover_page", "details": f"{doc} -> {p1} ({method})"})
                else:
                    log_rows.append({"country": country_dir.name, "question_id": er.get("question_id", ""), "action": "page_not_found", "details": doc})

        r.to_csv(rfile, index=False, encoding="utf-8-sig")
        e.to_csv(efile, index=False, encoding="utf-8-sig")

    audit_dir = run_dir / "audit"
    audit_dir.mkdir(exist_ok=True)
    log = pd.DataFrame(log_rows, columns=["country", "question_id", "action", "details"])
    log.to_csv(audit_dir / "repair_log.csv", index=False, encoding="utf-8-sig")
    print(f"Backup: {backup}")
    print(f"Repair log: {audit_dir / 'repair_log.csv'}")
    print(log.to_string(index=False) if not log.empty else "Nenhuma alteração realizada.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Repara somente rastreabilidade/pós-processamento da execução oficial, preservando o conteúdo recuperado.")
    ap.add_argument("--run-dir", default=str(DEFAULT_RUN))
    ap.add_argument("--content-jsonl", default=str(CONTENT_JSONL))
    args = ap.parse_args()
    repair(Path(args.run_dir), Path(args.content_jsonl))


if __name__ == "__main__":
    main()
