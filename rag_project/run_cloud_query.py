"""Consulta exploratória ao OpenAI Vector Store sem depender do backend FAISS local."""
import argparse
import os
from dotenv import load_dotenv

from rag_project.openai_vector_store import cloud_rag_query

DEFAULT_VECTOR_STORE_ID = "vs_6aa4d08cc1948191bc425516c4087b85"


def main(question: str, vector_store_id: str = DEFAULT_VECTOR_STORE_ID, openai_key: str | None = None):
    load_dotenv()
    if openai_key is None:
        openai_key = os.environ.get("OPENAI_API_KEY")

    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no ambiente/.env")

    print("[1/2] Consultando OpenAI Vector Store...")
    out = cloud_rag_query(vector_store_id, question, openai_key)
    print("\n--- RESULTADO FINAL ---")
    print(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="Pergunta livre sobre o corpus")
    parser.add_argument("--vector_store_id", default=DEFAULT_VECTOR_STORE_ID, help="ID do Vector Store OpenAI")
    parser.add_argument("--openai_key", default=None, help="Chave OpenAI opcional; se omitida usa .env")
    args = parser.parse_args()
    main(args.question, args.vector_store_id, args.openai_key)
