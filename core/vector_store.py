import hashlib
import os
import re

import chromadb
import numpy as np
from openai import OpenAI


EMBEDDING_MODEL = "text-embedding-3-large"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
DEFAULT_USER_ID = "default"

client = None
last_retrieval: list[dict] = []


def _get_client() -> OpenAI:
    return OpenAI()


def get_chroma_client():
    global client
    if client is None:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client


def _safe_user_id(user_id: str) -> str:
    safe_user_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(user_id))
    return safe_user_id or DEFAULT_USER_ID


def _collection_name(user_id: str) -> str:
    return f"user_{_safe_user_id(user_id)}"


def _ncc_collection_name(user_id: str, housing: bool = False) -> str:
    suffix = "housing" if housing else "ncc"
    return f"user_{_safe_user_id(user_id)}_{suffix}"


def get_collection(user_id: str):
    return get_chroma_client().get_or_create_collection(
        name=_collection_name(user_id),
        metadata={"hnsw:space": "cosine"},
    )


def get_ncc_collection(user_id: str, housing: bool = False):
    return get_chroma_client().get_or_create_collection(
        name=_ncc_collection_name(user_id, housing=housing),
        metadata={"hnsw:space": "cosine"},
    )


def persist() -> None:
    chroma_client = get_chroma_client()
    if hasattr(chroma_client, "persist"):
        chroma_client.persist()


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
        collection_names = [
            _collection_name(user_id),
            _ncc_collection_name(user_id),
            _ncc_collection_name(user_id, housing=True),
        ]
        for collection_name in collection_names:
            try:
                get_chroma_client().delete_collection(collection_name)
            except Exception:
                pass
    else:
        for collection in get_chroma_client().list_collections():
            collection_name = getattr(collection, "name", collection)
            if str(collection_name).startswith("user_"):
                try:
                    get_chroma_client().delete_collection(str(collection_name))
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


def add_ncc_documents(user_id, chunks, metadatas, housing: bool = False):
    if not chunks:
        return 0

    collection = get_ncc_collection(str(user_id), housing=housing)
    embeddings = [embed_text(chunk).tolist() for chunk in chunks]
    ids = [
        _document_id(f"{user_id}_{'housing' if housing else 'ncc'}", chunk, metadatas[index], index)
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


def search_ncc_chunks(user_id, query, top_k=5, filter_type=None, housing: bool = False):
    collection = get_ncc_collection(str(user_id), housing=housing)
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
    context_parts = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        clause = metadata.get("clause")
        section = metadata.get("section")
        prefix = " ".join(part for part in [section, clause] if part)
        if prefix:
            context_parts.append(f"{prefix}\n{chunk['text']}")
        else:
            context_parts.append(chunk["text"])
    return "\n\n".join(context_parts)


def format_sources(chunks: list[dict]) -> str:
    sources = []
    seen = set()
    for chunk in chunks:
        metadata = chunk["metadata"]
        clause = metadata.get("clause")
        source = clause or metadata.get("source", "Unknown source")
        if source in seen:
            continue
        seen.add(source)
        sources.append(f"[{len(sources) + 1}] {source}")
    return "\n".join(sources)


def get_last_retrieval() -> list[dict]:
    return last_retrieval
