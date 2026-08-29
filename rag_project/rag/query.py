import os
import json
from typing import List
from .indexer import Indexer
import openai

def rag_query(index_folder: str, question: str, top_k: int = 5, openai_api_key: str = None):
    idx = Indexer()
    idx.load(index_folder)
    hits = idx.query(question, top_k=top_k)
    snippets = [h['metadata'] for h in hits]
    # Build prompt
    context = "\n\n---\n\n".join([f"Source: {s.get('source')}\nText:\n{s.get('text')[:1000]}" for s in snippets])
    prompt = f"Responda a pergunta usando apenas as evidências listadas abaixo. Retorne uma síntese curta e liste as fontes utilizadas.\n\nEVIDÊNCIAS:\n{context}\n\nPERGUNTA: {question}\n\nRESPOSTA:"
    if openai_api_key:
        openai.api_key = openai_api_key
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            max_tokens=512,
            temperature=0.0,
        )
        return resp['choices'][0]['message']['content']
    else:
        # fallback: return the concatenated snippets and question
        out = {
            "question": question,
            "retrieved": snippets,
            "prompt": prompt[:4000]
        }
        return json.dumps(out, ensure_ascii=False, indent=2)
