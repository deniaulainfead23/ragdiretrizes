from rag_project.run_curated_pipeline import audit_corpus


def test_audit_blocks_build_when_corpus_has_curation_divergences(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'canada'
    country_dir.mkdir(parents=True)
    (country_dir / 'approved.pdf').write_bytes(b'%PDF approved')
    (country_dir / 'pending.pdf').write_bytes(b'%PDF pending')
    (country_dir / 'unregistered.pdf').write_bytes(b'%PDF unregistered')

    registry = {
        'countries': [
            {
                'country': 'canada',
                'include_in_analysis': True,
                'documents': [
                    {'document_id': 'CA-01', 'file': 'approved.pdf', 'role': 'primary', 'validation_status': 'validated'},
                    {'document_id': 'CA-02', 'file': 'missing.pdf', 'role': 'primary', 'validation_status': 'validated'},
                    {'document_id': 'CA-03', 'file': 'pending.pdf', 'role': 'primary', 'validation_status': 'pending_review'},
                ],
            }
        ]
    }

    audit = audit_corpus(corpus_root, registry)

    assert audit['verified_present_documents'] == 1
    assert audit['missing_verified_files'] == ['canada/missing.pdf']
    assert audit['unregistered_excluded_files'] == ['canada/unregistered.pdf']
    assert audit['pending_verification_excluded_files'] == ['canada/pending.pdf']
    assert audit['is_buildable'] is False


def test_audit_allows_build_for_fully_curated_corpus(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'canada'
    country_dir.mkdir(parents=True)
    (country_dir / 'approved.pdf').write_bytes(b'%PDF approved')
    registry = {
        'countries': [
            {
                'country': 'canada',
                'include_in_analysis': True,
                'documents': [
                    {'document_id': 'CA-01', 'file': 'approved.pdf', 'role': 'primary', 'validation_status': 'validated'},
                ],
            }
        ]
    }

    audit = audit_corpus(corpus_root, registry)

    assert audit['is_buildable'] is True