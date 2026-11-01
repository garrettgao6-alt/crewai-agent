from core.storage_lock import snapshot_writer
from core.private_ai import project_scope
from contextvars import ContextVar
from copy import deepcopy
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
_last_retrieval = ContextVar("last_retrieval", default=None)


def _get_client() -> OpenAI:
    from core.private_ai import client
    return client(OpenAI)


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


def embed_text(text: str) -> np.ndarray:
    try:
        openai_client = _get_client()
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return np.array(response.data[0].embedding)
    except Exception as exc:
        raise RuntimeError("Embedding service unavailable; indexing/search was not completed. Please retry.") from exc


def embed_batch(chunks):
    response=_get_client().embeddings.create(model=EMBEDDING_MODEL,input=chunks)
    data=sorted(response.data,key=lambda item:item.index)
    if [item.index for item in data]!=list(range(len(chunks))) or any(not item.embedding for item in data):
        raise RuntimeError('The embedding batch was incomplete.')
    dimensions={len(item.embedding) for item in data}
    if len(dimensions)!=1:raise RuntimeError('The embedding batch has inconsistent dimensions.')
    return [item.embedding for item in data]


def cosine_sim(a, b) -> float:
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def _document_id(user_id: str, text: str, metadata: dict, index: int) -> str:
    source = metadata.get("source", "") + str(metadata.get('managed_version_id',''))
    doc_type = metadata.get("type", "")
    digest = hashlib.sha256(f"{user_id}|{source}|{doc_type}|{index}|{text}".encode("utf-8")).hexdigest()
    return f"id_{digest[:24]}"


@snapshot_writer
def clear_store(user_id: str | None = None) -> None:
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
    _last_retrieval.set([])
    persist()


def set_last_retrieval(chunks: list[dict]) -> None:
    _last_retrieval.set(deepcopy(chunks))


@project_scope
@snapshot_writer
def add_documents(user_id, chunks, metadatas):
    if not chunks:
        return 0

    collection = get_collection(str(user_id))
    embeddings = embed_batch(chunks) if all(m.get('managed_version_id') for m in metadatas) else [embed_text(chunk).tolist() for chunk in chunks]
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


@project_scope
@snapshot_writer
def add_ncc_documents(user_id, chunks, metadatas, housing: bool = False):
    if not chunks:
        return 0

    collection = get_ncc_collection(str(user_id), housing=housing)
    embeddings = embed_batch(chunks) if all(m.get('managed_version_id') for m in metadatas) else [embed_text(chunk).tolist() for chunk in chunks]
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


@project_scope
def search(user_id, query, top_k=5, filter_type=None):
    collection = get_collection(str(user_id))
    if collection.count() == 0:
        return []
    from core.document_store import retrieval_filter
    where = retrieval_filter(user_id, {"type": filter_type} if filter_type else None)
    query_embedding = embed_text(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return results["documents"][0] if results.get("documents") else []


@project_scope
def search_chunks(user_id, query, top_k=5, filter_type=None):
    collection = get_collection(str(user_id))
    if collection.count() == 0:
        return []
    from core.document_store import retrieval_filter
    where = retrieval_filter(user_id, {"type": filter_type} if filter_type else None)
    query_embedding = embed_text(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return _results_to_chunks(results)


@project_scope
def search_ncc_chunks(user_id, query, top_k=5, filter_type=None, housing: bool = False):
    collection = get_ncc_collection(str(user_id), housing=housing)
    if collection.count() == 0:
        return []
    from core.document_store import retrieval_filter
    where = retrieval_filter(user_id, {"type": filter_type} if filter_type else None)
    query_embedding = embed_text(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    return _results_to_chunks(results)


def retrieve(query, top_k=5, filter_type=None, user_id: str = DEFAULT_USER_ID):
    chunks = search_chunks(user_id, query, top_k=top_k, filter_type=filter_type)
    set_last_retrieval(chunks)
    return chunks


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
        if metadata.get("reference_kind") in {"server_local_ncc", "project_ncc"}:
            location = metadata.get("source", "Unknown source")
            if metadata.get("reference_kind") == "project_ncc" and metadata.get("page"):
                location += f", p. {metadata['page']}"
            source = " · ".join(str(value) for value in (metadata.get("code"), location, clause) if value)
        if source in seen:
            continue
        seen.add(source)
        sources.append(f"[{len(sources) + 1}] {source}")
    return "\n".join(sources)


def get_last_retrieval() -> list[dict]:
    return deepcopy(_last_retrieval.get() or [])
