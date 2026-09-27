"""CLI de compatibilidade para gerar a matriz de evidências DLGF 2018."""

from rag_project.build_evidence_matrix import build_evidence_matrix, main

__all__ = ["build_evidence_matrix", "main"]


if __name__ == "__main__":
    main()
