import numpy as np
from openai import OpenAI

from core.skills import build_skill_chain, route_primary_skill


DOMAIN_VECTORS = {
    "construction": None,
    "business": None,
    "general": None,
}

FALLBACK_MAPPING = {
    "analysis": "construction",
    "risk": "construction",
    "strategy": "business",
    "finance": "business",
    "general": "general",
}


def _get_client() -> OpenAI:
    return OpenAI()


def init_vectors() -> bool:
    try:
        client = _get_client()
        for domain in DOMAIN_VECTORS:
            if DOMAIN_VECTORS[domain] is not None:
                continue
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=domain,
            )
            DOMAIN_VECTORS[domain] = np.array(emb.data[0].embedding)
    except Exception:
        return False

    return all(vector is not None for vector in DOMAIN_VECTORS.values())


def cosine_sim(a, b):
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0
    return np.dot(a, b) / denominator


def _fallback_route_task(task: str) -> str:
    return FALLBACK_MAPPING.get(task.strip().lower(), "general")


def route_task(task: str) -> str:
    if not init_vectors():
        return _fallback_route_task(task)

    try:
        client = _get_client()
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=task,
        )

        task_vec = np.array(emb.data[0].embedding)

        scores = {
            domain: cosine_sim(task_vec, vec)
            for domain, vec in DOMAIN_VECTORS.items()
            if vec is not None
        }

        if not scores:
            return _fallback_route_task(task)

        return max(scores, key=scores.get)
    except Exception:
        return _fallback_route_task(task)


def route_skill(query: str) -> str | None:
    return route_primary_skill(query)


def route_skill_chain(query: str, *, is_rag_response: bool = False, client_deliverable: bool = True) -> list[str]:
    return build_skill_chain(
        query,
        is_rag_response=is_rag_response,
        client_deliverable=client_deliverable,
    )
