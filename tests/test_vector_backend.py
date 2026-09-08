import json
from pathlib import Path

from rag_project.vector_backend import (
    DEFAULT_VECTOR_BACKEND,
    load_vector_backend_manifest,
    resolve_backend,
    write_vector_backend_manifest,
)


def test_backend_resolution_prefers_openai_when_available(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    assert resolve_backend() == 'openai'
    assert resolve_backend('local') == 'local'
    assert resolve_backend('openai') == 'openai'


def test_backend_resolution_falls_back_to_local_without_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert resolve_backend() == 'local'


def test_manifest_can_be_written_and_read(tmp_path):
    manifest_path = tmp_path / 'vector_store_manifest.json'
    payload = {
        'backend': 'openai',
        'vector_store_id': 'vs_test_123',
        'model': 'gpt-4o-mini',
        'index_folder': 'indexed'
    }

    write_vector_backend_manifest(payload, manifest_path)
    loaded = load_vector_backend_manifest(manifest_path)

    assert loaded['backend'] == 'openai'
    assert loaded['vector_store_id'] == 'vs_test_123'
    assert json.loads(manifest_path.read_text(encoding='utf-8'))['backend'] == 'openai'


def test_default_backend_constant_is_defined():
    assert DEFAULT_VECTOR_BACKEND in {'openai', 'local'}
