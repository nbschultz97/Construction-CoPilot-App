import os, requests, math
from typing import List, Tuple, Dict, Any
from api.settings import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

# Embeddings (OpenAI or local provided by ingest)

def openai_embed(texts: List[str]) -> List[List[float]]:
    key = settings.OPENAI_API_KEY
    if not key:
        # Shouldn't be called without key, but guard anyway
        return [[0.0] * 1536 for _ in texts]
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"model": "text-embedding-3-large", "input": texts}
    resp = requests.post(url, headers=headers, json=data, timeout=60)
    resp.raise_for_status()
    out = resp.json()["data"]
    return [e["embedding"] for e in out]


def rank_and_filter(results, k: int, min_score: float):
    # Chroma returns distances; convert to similarity ~ 1 - dist (for cosine)
    items = []
    for i in range(len(results["ids"][0])):
        score = 1.0 - results["distances"][0][i]
        items.append((
            results["documents"][0][i],
            score,
            results["metadatas"][0][i]
        ))
    items.sort(key=lambda x: x[1], reverse=True)
    items = [it for it in items if it[1] >= min_score]
    return items[:k]


def search(project_id: str, query: str, top_k: int):
    client = chromadb.Client(ChromaSettings(persist_directory=settings.CHROMA_DIR))
    coll = client.get_or_create_collection(project_id)
    # embed query
    if settings.EMBEDDINGS_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        qvec = openai_embed([query])[0]
        results = coll.query(query_embeddings=[qvec], n_results=max(12, top_k))
    else:
        # local embedding handled by Chroma's default? No; we stored vectors at ingest time.
        # Use raw query_text to query; Chroma will embed only if collection has no embeddings.
        results = coll.query(query_texts=[query], n_results=max(12, top_k))
    return rank_and_filter(results, top_k, settings.MIN_SCORE)


PROMPT = """You are a construction document assistant. Answer using ONLY the provided context.
If the answer is not explicitly supported by the context, say:
"I don't know - no relevant passages found."

Format:
- Direct answer in 1-4 sentences.
- Then "Citations:" followed by references like [filename p.PAGE].

Context:
{context}

Question:
{question}

Rules:
- Never invent details.
- Always include citations like [specs.pdf p.121].
- If multiple sources corroborate, include multiple citations.
"""


def format_citations(items: List[Tuple[str, float, Dict[str, Any]]]):
    cites = []
    for _, score, meta in items:
        cites.append({"source": meta["source"], "page": int(meta["page"]), "score": float(score)})
    return cites


def call_openai(prompt: str) -> str:
    key = settings.OPENAI_API_KEY
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    r = requests.post(url, headers=headers, json=data, timeout=90)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def answer(project_id: str, question: str, top_k: int):
    items = search(project_id, question, top_k)
    if not items:
        return {
            "answer": "I don't know - no relevant passages found.",
            "citations": [],
            "used_chunks": 0
        }
    # Build context
    context_blocks = []
    for doc, score, meta in items:
        context_blocks.append(f"[{meta['source']} p.{meta['page']}] {doc}")
    context = "\n\n".join(context_blocks)
    # Choose LLM or extractive
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        prompt = PROMPT.format(context=context, question=question)
        out = call_openai(prompt)
        ans = out
    else:
        # Extractive fallback: return best snippet with citations
        best = items[0]
        ans = f"{best[0][:600]}...\n\nCitations: [{best[2]['source']} p.{best[2]['page']}]"
    return {
        "answer": ans,
        "citations": format_citations(items),
        "used_chunks": len(items)
    }
