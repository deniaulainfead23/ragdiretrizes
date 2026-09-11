from rag_project.corpus_registry import registered_documents


def test_registered_documents_does_not_discover_unregistered_files(tmp_path, monkeypatch):
    monkeypatch.setattr('rag_project.corpus_registry.CORPUS_PATH', tmp_path / 'corpus')
    (tmp_path / 'corpus' / 'brasil').mkdir(parents=True)
    (tmp_path / 'corpus' / 'brasil' / 'curriculo.pdf').write_bytes(b'%PDF')

    registry = {
        'countries': [
            {
                'country': 'brasil',
                'include_in_analysis': True,
                'documents': [],
            }
        ]
    }

    assert list(registered_documents(registry)) == []


def test_registered_documents_excludes_pending_review():
    registry = {
        'countries': [
            {
                'country': 'china',
                'include_in_analysis': True,
                'documents': [
                    {'file': 'pending.pdf', 'role': 'primary', 'validation_status': 'pending_review'},
                    {'file': 'approved.pdf', 'role': 'primary', 'validation_status': 'validated'},
                ],
            }
        ]
    }

    documents = list(registered_documents(registry))

    assert [document['file'] for _, document in documents] == ['approved.pdf']