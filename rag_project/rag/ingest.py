import os
from pathlib import Path
import pdfplumber
from PIL import Image
import pytesseract

try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None


def extract_text_from_pdf(path: str) -> str:
    pages = extract_pdf_pages(path)
    return "\n\n".join(page_text for _, page_text in pages)


def extract_pdf_pages(path: str):
    """Retorna lista de (page_number, text) para preservar paginação do PDF."""
    pages = []
    if fitz is not None:
        try:
            with fitz.open(path) as pdf:
                extracted_pages = [
                    (page_number, page.get_text())
                    for page_number, page in enumerate(pdf, start=1)
                    if page.get_text().strip()
                ]
            if extracted_pages:
                return extracted_pages
        except Exception:
            pass

    try:
        with pdfplumber.open(path) as pdf:
            extracted_pages = []
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    extracted_pages.append((page_number, text))
            if extracted_pages:
                return extracted_pages

            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    pil = page.to_image(resolution=150).original
                    ocr = pytesseract.image_to_string(pil, lang='por+eng')
                    if ocr.strip():
                        pages.append((page_number, ocr))
                except Exception:
                    pass
    except Exception:
        try:
            img = Image.open(path)
            ocr = pytesseract.image_to_string(img, lang='por+eng')
            if ocr.strip():
                pages.append((1, ocr))
        except Exception:
            pass
    return pages


def iter_corpus_files(corpus_dir: str):
    """Enumera caminhos sem abrir ou extrair o conteúdo dos arquivos."""
    root = Path(corpus_dir)
    if not root.exists():
        return
    for file in sorted(root.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(root).as_posix()
        ext = file.suffix.lower()
        yield rel, str(file), ext


def read_text_file(path: str) -> str:
    file = Path(path)
    try:
        return file.read_text(encoding='utf-8')
    except Exception:
        try:
            return file.read_text(encoding='latin-1')
        except Exception:
            return ""


def iter_corpus_documents(corpus_dir: str):
    """Gera documentos do corpus um a um para evitar carregar tudo em memória."""
    for rel, path, ext in iter_corpus_files(corpus_dir):
        if ext == ".pdf":
            pages = extract_pdf_pages(path)
            text = "\n\n".join(page_text for _, page_text in pages)
        else:
            text = read_text_file(path)
        if text and text.strip():
            yield rel, path, text, ext


def ingest_corpus(corpus_dir: str) -> dict:
    """Percorre a pasta `corpus_dir` e extrai texto dos arquivos encontrados.

    Retorna um dicionário {relative_path: text}
    """
    corpus = {}
    for rel, _, text, _ in iter_corpus_documents(corpus_dir):
        corpus[rel] = text
    return corpus
