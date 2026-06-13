import re

from core.document_pipeline import clean_text


NCC_MARKER_PATTERN = re.compile(r"(C\d+\.\d+|Section [A-Z])")


def parse_ncc_clauses(text: str, default_type: str = "fire") -> list[dict]:
    cleaned_text = clean_text(text)
    parts = NCC_MARKER_PATTERN.split(cleaned_text)

    clauses = []
    current_section = ""

    for index in range(1, len(parts), 2):
        marker = parts[index].strip()
        content = parts[index + 1].strip() if index + 1 < len(parts) else ""

        if marker.startswith("Section "):
            current_section = marker
            continue

        clause = marker
        title = _extract_title(content)
        clause_text = clean_text(f"{clause} {content}")

        if clause_text:
            clauses.append(
                {
                    "section": current_section,
                    "clause": clause,
                    "title": title,
                    "text": clause_text,
                    "type": _infer_clause_type(clause_text, default_type),
                }
            )

    return clauses


def _extract_title(content: str) -> str:
    if not content:
        return ""

    first_line = content.splitlines()[0].strip()
    if len(first_line) <= 120:
        return first_line.rstrip(".")

    first_sentence = first_line.split(". ", 1)[0].strip()
    return first_sentence[:120].rstrip(".")


def _infer_clause_type(text: str, default_type: str) -> str:
    text_lower = text.lower()
    if any(term in text_lower for term in ["fire", "egress", "smoke", "exit", "sprinkler"]):
        return "fire"
    if any(term in text_lower for term in ["structure", "structural", "load", "beam", "footing"]):
        return "structure"
    return default_type


def clauses_to_documents(clauses: list[dict], source: str, code: str = "NCC2025") -> tuple[list[str], list[dict]]:
    documents = []
    metadatas = []

    for clause in clauses:
        documents.append(clause["text"])
        metadatas.append(
            {
                "code": code,
                "section": clause.get("section", ""),
                "clause": clause.get("clause", ""),
                "title": clause.get("title", ""),
                "source": source,
                "type": clause.get("type", "fire"),
            }
        )

    return documents, metadatas
