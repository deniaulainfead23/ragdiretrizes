import re
from typing import List

def normalize_text(text: str) -> str:
    text = text.replace('\r', '\n')
    # remove multiple newlines
    text = re.sub(r"\n{2,}", "\n\n", text)
    # remove page numbers like "Página 1" or "Page 1"
    text = re.sub(r"(?i)page\s*\d+|página\s*\d+", "", text)
    # collapse spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    """Yield chunks from text by characters preserving overlap. Generator to reduce memory usage."""
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        start = end - overlap
        if start < 0:
            start = 0
        if start >= length:
            break
