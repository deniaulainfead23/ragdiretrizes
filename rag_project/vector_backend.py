"""Vector backend abstraction for the project.

The project is expected to use the OpenAI Vector Store as the primary backend
for semantic retrieval, while keeping a local FAISS-based backend as an optional
fallback for small experiments and local testing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_VECTOR_BACKEND = "openai"
BACKEND_CHOICES = {"openai", "local"}


def resolve_backend(backend: str | None = None, api_key: str | None = None) -> str:
    """Resolve the active backend.

    The rule is simple: if the caller explicitly chooses a backend, respect it.
    Otherwise prefer OpenAI when an API key is available; otherwise fall back to
    the local FAISS backend.
    """
    if backend:
        normalized = backend.strip().lower()
        if normalized in BACKEND_CHOICES:
            return normalized
        raise ValueError(f"Backend inválido: {backend!r}. Opções válidas: {sorted(BACKEND_CHOICES)}")

    resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
    return "openai" if resolved_key else "local"


def default_manifest_path() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / "metadata" / "vector_store_manifest.json"


def load_vector_backend_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path is not None else default_manifest_path()
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def write_vector_backend_manifest(payload: dict[str, Any], path: str | Path | None = None) -> Path:
    manifest_path = Path(path) if path is not None else default_manifest_path()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
