import ast
import json

from openai import OpenAI

from core.vector_store import (
    build_context,
    format_sources,
    get_last_retrieval,
    retrieve,
    set_last_retrieval,
)


def _get_client() -> OpenAI:
    return OpenAI()


def generate_queries(query: str):
    try:
        client = _get_client()
        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"""
Generate 3 alternative search queries for:

{query}

Return list only.
""",
            temperature=0,
        )
        parsed = ast.literal_eval(response.output_text)
        if isinstance(parsed, list):
            queries = [str(item).strip() for item in parsed if str(item).strip()]
            return queries or [query]
    except Exception:
        return [query]

    return [query]


def _dedupe_chunks(chunks: list[dict]) -> list[dict]:
    unique_chunks = []
    seen = set()

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        key = (
            metadata.get("source", ""),
            metadata.get("type", ""),
            chunk.get("text", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_chunks.append(chunk)

    return unique_chunks


def retrieve_multi(query, top_k=5, filter_type=None):
    queries = generate_queries(query)
    if query not in queries:
        queries.insert(0, query)

    results = []

    for generated_query in queries:
        results.extend(retrieve(generated_query, top_k=top_k, filter_type=filter_type))

    unique = _dedupe_chunks(results)
    set_last_retrieval(unique[:top_k])
    return unique[:top_k]


def _parse_ranked_indexes(text: str) -> list[int]:
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []

    if isinstance(parsed, dict):
        parsed = parsed.get("ranked_indexes", parsed.get("indices", []))

    if not isinstance(parsed, list):
        return []

    return [index for index in parsed if isinstance(index, int)]


def rerank(query, chunks):
    if len(chunks) <= 1:
        set_last_retrieval(chunks)
        return chunks

    try:
        client = _get_client()
        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"""
Rank these chunks by relevance:

Query: {query}

Chunks:
{chunks}

Return sorted indices.
""",
            temperature=0,
        )
        ranked_indexes = _parse_ranked_indexes(response.output_text)
        ranked_chunks = []
        seen = set()

        for index in ranked_indexes:
            if 0 <= index < len(chunks) and index not in seen:
                ranked_chunks.append(chunks[index])
                seen.add(index)

        ranked_chunks.extend(chunk for index, chunk in enumerate(chunks) if index not in seen)
        set_last_retrieval(ranked_chunks)
        return ranked_chunks
    except Exception:
        fallback = sorted(chunks, key=lambda chunk: chunk.get("score", 0), reverse=True)
        set_last_retrieval(fallback)
        return fallback


def retrieve_context(query: str, top_k=5, filter_type=None):
    retrieved = retrieve_multi(query, top_k=top_k, filter_type=filter_type)
    ranked = rerank(query, retrieved)[:top_k]
    set_last_retrieval(ranked)
    return {
        "chunks": ranked,
        "context": build_context(ranked),
        "sources": format_sources(ranked),
    }
