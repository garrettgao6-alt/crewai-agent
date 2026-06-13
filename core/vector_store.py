import hashlib
import json
from collections import Counter

import numpy as np
from openai import OpenAI


EMBEDDING_MODEL = "text-embedding-3-large"
store: list[dict] = []
last_retrieval: list[dict] = []


def _get_client() -> OpenAI:
    return OpenAI()


def _fallback_embedding(text: str, dimensions: int = 256) -> np.ndarray:
    vector = np.zeros(dimensions)
    words = [word.lower() for word in text.split()]
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0
    return vector


def embed_text(text: str) -> np.ndarray:
    try:
        client = _get_client()
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return np.array(response.data[0].embedding)
    except Exception:
        return _fallback_embedding(text)


def cosine_sim(a, b) -> float:
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def clear_store() -> None:
    global last_retrieval
    store.clear()
    last_retrieval = []


def set_last_retrieval(chunks: list[dict]) -> None:
    global last_retrieval
    last_retrieval = chunks


def add_chunks(chunks: list[dict]) -> int:
    for chunk in chunks:
        text = chunk["text"]
        store.append(
            {
                "text": text,
                "embedding": embed_text(text),
                "metadata": chunk["metadata"],
            }
        )
    return len(chunks)


def _candidate_chunks(filter_type=None) -> list[dict]:
    if filter_type is None:
        return store
    return [item for item in store if item["metadata"].get("type") == filter_type]


def _fallback_rerank(query: str, chunks: list[dict]) -> list[dict]:
    query_terms = Counter(query.lower().split())

    def lexical_score(chunk: dict) -> int:
        chunk_terms = Counter(chunk["text"].lower().split())
        return sum(min(count, chunk_terms.get(term, 0)) for term, count in query_terms.items())

    return sorted(chunks, key=lexical_score, reverse=True)


def rerank(query: str, chunks: list[dict]) -> list[dict]:
    if len(chunks) <= 1:
        return chunks

    try:
        client = _get_client()
        chunk_payload = [
            {
                "index": index,
                "source": chunk["metadata"].get("source", ""),
                "type": chunk["metadata"].get("type", ""),
                "text": chunk["text"],
            }
            for index, chunk in enumerate(chunks)
        ]
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Rank these chunks based on relevance to the query. "
                        "Return JSON only: {\"ranked_indexes\": [0, 1]}"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nChunks:\n{json.dumps(chunk_payload)}",
                },
            ],
            temperature=0,
        )
        ranked_indexes = json.loads(response.output_text).get("ranked_indexes", [])
        ranked_chunks = []
        seen = set()
        for index in ranked_indexes:
            if isinstance(index, int) and 0 <= index < len(chunks) and index not in seen:
                ranked_chunks.append(chunks[index])
                seen.add(index)
        ranked_chunks.extend(chunk for index, chunk in enumerate(chunks) if index not in seen)
        return ranked_chunks
    except Exception:
        return _fallback_rerank(query, chunks)


def retrieve(query, top_k=5, filter_type=None):
    global last_retrieval
    candidates = _candidate_chunks(filter_type)
    if not candidates:
        last_retrieval = []
        return []

    query_embedding = embed_text(query)
    scored_chunks = []
    for item in candidates:
        scored_item = item.copy()
        scored_item["score"] = cosine_sim(query_embedding, item["embedding"])
        scored_chunks.append(scored_item)

    top_candidates = sorted(scored_chunks, key=lambda item: item["score"], reverse=True)[: max(top_k * 3, top_k)]
    last_retrieval = rerank(query, top_candidates)[:top_k]
    return last_retrieval


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(chunk["text"] for chunk in chunks)


def format_sources(chunks: list[dict]) -> str:
    sources = []
    seen = set()
    for chunk in chunks:
        source = chunk["metadata"].get("source", "Unknown source")
        if source in seen:
            continue
        seen.add(source)
        sources.append(f"[{len(sources) + 1}] {source}")
    return "\n".join(sources)


def get_last_retrieval() -> list[dict]:
    return last_retrieval
