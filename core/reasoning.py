import os

from openai import OpenAI


DEFAULT_REASONING_MODEL = os.getenv("OPENAI_REASONING_MODEL", "gpt-4o-mini")


def _get_client() -> OpenAI:
    return OpenAI()


def build_reasoning_prompt(query, clauses):
    context = "\n\n".join(
        [
            f"{clause['clause']} - {clause['content']}"
            for clause in clauses
        ]
    )

    prompt = f"""
You are a construction compliance expert.

Using the following NCC clauses:

{context}

Answer:

{query}

You must:

* combine multiple clauses
* explain relationships
* identify conflicts
* cite clause numbers
* do NOT guess

If unsure, say:
'Insufficient NCC reference found.'

Return:
Compliance Summary
Relevant Clauses
Assessment
Risk Level
"""

    return prompt


def chunks_to_clauses(chunks: list[dict]) -> list[dict]:
    clauses = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        clause = metadata.get("clause") or metadata.get("source", "Unknown clause")
        clauses.append(
            {
                "clause": clause,
                "content": chunk.get("text", ""),
                "section": metadata.get("section", ""),
                "title": metadata.get("title", ""),
            }
        )
    return clauses


def run_multi_clause_reasoning(query: str, chunks: list[dict]) -> str:
    clauses = chunks_to_clauses(chunks)
    if not clauses:
        return "Insufficient NCC reference found."

    prompt = build_reasoning_prompt(query, clauses)

    try:
        client = _get_client()
        response = client.responses.create(
            model=DEFAULT_REASONING_MODEL,
            input=prompt,
            temperature=0,
        )
        return response.output_text
    except Exception:
        clause_list = "\n".join(f"* {clause['clause']}" for clause in clauses)
        return (
            "Compliance Summary\n"
            "Insufficient NCC reference found.\n\n"
            "Relevant Clauses\n"
            f"{clause_list}\n\n"
            "Assessment\n"
            "A definitive assessment requires GPT reasoning over the retrieved clauses.\n\n"
            "Risk Level\n"
            "Unknown"
        )
