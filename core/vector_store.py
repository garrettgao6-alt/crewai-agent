import hashlib
import os
import re

import chromadb
import numpy as np
from openai import OpenAI


EMBEDDING_MODEL = "text-embedding-3-large"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
DEFAULT_USER_ID = "default"

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
last_retrieval: list[dict] = []


def _get_client() -> OpenAI:
    return OpenAI()


def _collection_name(user_id: str) -> str:
    safe_user_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(user_id))
    return f"user_{safe_user_id or DEFAULT_USER_ID}"


def get_collection(user_id: str):
    return client.get_or_create_collection(
        name=_collection_name(user_id),
        metadata={"hnsw:space": "cosine"},
    )


def persist() -> None:
    if hasattr(client, "persist"):
        client.persist()


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
        openai_client = _get_client()
        response = openai_client.embeddings.create(
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


def _document_id(user_id: str, text: str, metadata: dict, index: int) -> str:
    source = metadata.get("source", "")
    doc_type = metadata.get("type", "")
    digest = hashlib.sha256(f"{user_id}|{source}|{doc_type}|{index}|{text}".encode("utf-8")).hexdigest()
    return f"id_{digest[:24]}"


def clear_store(user_id: str | None = None) -> None:
    global last_retrieval
    if user_id is not None:
        collection_name = _collection_name(user_id)
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
    else:
        for collection in client.list_collections():
            collection_name = getattr(collection, "name", collection)
            if str(collection_name).startswith("user_"):
                try:
                    client.delete_collection(str(collection_name))
                except Exception:
                    pass
    last_retrieval = []
    persist()


def set_last_retrieval(chunks: list[dict]) -> None:
    global last_retrieval
    last_retrieval = chunks


def add_documents(user_id, chunks, metadatas):
    if not chunks:
        return 0

    collection = get_collection(str(user_id))
    embeddings = [embed_text(chunk).tolist() for chunk in chunks]
    ids = [
        _document_id(str(user_id), chunk, metadatas[index], index)
        for index, chunk in enumerate(chunks)
    ]

    collection.upsert(
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
        ids=ids,
    )
    persist()
    return len(chunks)


def add_chunks(chunks: list[dict], user_id: str = DEFAULT_USER_ID) -> int:
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    return add_documents(user_id, documents, metadatas)


def _results_to_chunks(results: dict) -> list[dict]:
    documents = results.get("documents", [[]])[0] or []
    metadatas = results.get("metadatas", [[]])[0] or []
    distances = results.get("distances", [[]])[0] or []

    chunks = []
    for index, text in enumerate(documents):
        distance = distances[index] if index < len(distances) else None
        score = 1 - distance if isinstance(distance, (int, float)) else 0
        chunks.append(
            {
                "text": text,
                "metadata": metadatas[index] if index < len(metadatas) and metadatas[index] else {},
                "score": score,
            }
        )
    return chunks


def search(user_id, query, top_k=5, filter_type=None):
    collection = get_collection(str(user_id))
    if collection.count() == 0:
        return []
    where = {"type": filter_type} if filter_type else None
    query_embedding = embed_text(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return results["documents"][0] if results.get("documents") else []


def search_chunks(user_id, query, top_k=5, filter_type=None):
    collection = get_collection(str(user_id))
    if collection.count() == 0:
        return []
    where = {"type": filter_type} if filter_type else None
    query_embedding = embed_text(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return _results_to_chunks(results)


def retrieve(query, top_k=5, filter_type=None, user_id: str = DEFAULT_USER_ID):
    global last_retrieval
    last_retrieval = search_chunks(user_id, query, top_k=top_k, filter_type=filter_type)
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
