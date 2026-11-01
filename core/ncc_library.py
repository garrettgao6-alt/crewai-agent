from core.storage_lock import Connection as SnapshotConnection
"""Persistent, per-user references to an operator-approved server NCC directory."""
import math
import os
from pathlib import Path
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from functools import lru_cache

from core.document_pipeline import chunk_text

DB_PATH = Path(__file__).resolve().parent.parent / "ncc_library.db"
MAX_FILES = 100
MAX_FILE_BYTES = 75 * 1024 * 1024
SUPPORTED = {".pdf", ".txt"}


class NCCReferenceError(ValueError):
    pass


def library_root():
    configured = os.getenv("NCC_DOCUMENT_ROOT", "").strip()
    if not configured:
        raise NCCReferenceError("Ask the administrator to configure NCC_DOCUMENT_ROOT on the server.")
    root = Path(configured).expanduser().resolve()
    if not root.is_dir():
        raise NCCReferenceError("The configured NCC document root is not an accessible directory.")
    return root


def resolve_reference(value):
    root = library_root()
    candidate = Path(value).expanduser()
    path = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not path.is_relative_to(root):
        raise NCCReferenceError("Choose a file or directory inside the configured NCC document root.")
    if not path.exists():
        raise NCCReferenceError("The NCC reference path does not exist on the server.")
    return path


def reference_files(value, user_id=None):
    path = resolve_reference(value)
    from core.ncc_catalog import check_owner
    try:
        check_owner(library_root(), path, user_id)
    except PermissionError as exc:
        raise NCCReferenceError(str(exc)) from None
    candidates = path.iterdir() if path.is_dir() else [path]
    files = []
    total_bytes = 0
    for candidate in candidates:
        if candidate.suffix.lower() not in SUPPORTED or not candidate.is_file():
            continue
        # Recheck symlinks inside an otherwise approved directory.
        candidate = resolve_reference(str(candidate))
        try:
            check_owner(library_root(), candidate, user_id)
        except PermissionError as exc:
            raise NCCReferenceError(str(exc)) from None
        if candidate.stat().st_size > MAX_FILE_BYTES:
            raise NCCReferenceError(f"{candidate.name} exceeds the 75 MB reference file limit.")
        total_bytes += candidate.stat().st_size
        if total_bytes > 200 * 1024 * 1024:
            raise NCCReferenceError("Choose reference files totaling at most 200 MB.")
        files.append(candidate)
        if len(files) > MAX_FILES:
            raise NCCReferenceError("Choose a directory with at most 100 PDF or TXT files.")
    if not files:
        raise NCCReferenceError("No PDF or TXT reference files found. Scanned PDFs need OCR text first.")
    return sorted(files)


@contextmanager
def _connection():
    connection = sqlite3.connect(DB_PATH, factory=SnapshotConnection)
    try:
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS ncc_references (user_id TEXT PRIMARY KEY, path TEXT NOT NULL, edition TEXT NOT NULL)")
            yield connection
    finally:
        connection.close()


def load_reference(user_id):
    row = None
    if Path(DB_PATH).exists():
        with _connection() as connection:
            row = connection.execute("SELECT path, edition FROM ncc_references WHERE user_id = ?", (str(user_id),)).fetchone()
    if row:
        return {"path": row[0], "edition": row[1]} if row[0] else None
    default = os.getenv("NCC_DEFAULT_REFERENCE", "").strip()
    if default:
        return {"path": default, "edition": "NCC 2025 operator reference library", "operator_default": True}
    return None


def save_reference(user_id, value, edition):
    files = reference_files(value, user_id=user_id)
    resolved = resolve_reference(value)
    if resolved.is_file() and (resolved.parent / ".ncc-index.sqlite3").exists():
        raise NCCReferenceError("Select the indexed library directory to preserve edition and building-class matching.")
    path = resolved.relative_to(library_root()).as_posix()
    if not edition.strip():
        raise NCCReferenceError("Enter the NCC edition/volume to identify this reference accurately.")
    with _connection() as connection:
        connection.execute("INSERT INTO ncc_references VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET path=excluded.path, edition=excluded.edition", (str(user_id), path, edition.strip()))
    return len(files)


def clear_reference(user_id):
    with _connection() as connection:
        if os.getenv("NCC_DEFAULT_REFERENCE", "").strip():
            connection.execute("INSERT INTO ncc_references VALUES (?, '', '') ON CONFLICT(user_id) DO UPDATE SET path='',edition=''", (str(user_id),))
        else:
            connection.execute("DELETE FROM ncc_references WHERE user_id = ?", (str(user_id),))


@lru_cache(maxsize=8)
def _read_pages(path, modified_ns, size):
    file = Path(path)
    try:
        if file.suffix.lower() == ".txt":
            return [(1, file.read_text(encoding="utf-8-sig"))]
        from PyPDF2 import PdfReader
        reader = PdfReader(str(file))
        pages = [(index, page.extract_text() or "") for index, page in enumerate(reader.pages, 1)]
        if not any(text.strip() for _, text in pages):
            raise NCCReferenceError(f"{file.name} has no extractable text; run OCR before using it.")
        return pages
    except NCCReferenceError:
        raise
    except Exception as exc:
        raise NCCReferenceError(f"Could not read {file.name}; check the file format and server permissions.") from exc


def _tokens(text):
    for chinese, english in {"防火墙": " fire wall ", "外墙": " external wall ", "保温": " insulation ", "防水": " waterproofing ", "屋面": " roof ", "窗户": " windows ", "能效": " energy efficiency ", "防火": " fire ", "消防": " fire safety ", "出口": " exits egress ", "结构": " structural ", "住宅": " housing residential ", "通风": " ventilation ", "无障碍": " accessibility ", "楼梯": " stairs ", "疏散": " egress ", "墙": " walls "}.items():
        text = text.replace(chinese, english)
    stop = {"the", "and", "for", "with", "this", "that", "from", "ncc", "code", "compliance", "review", "check"}
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in stop]


def search_local_references(user_id, query, top_k=5, context=None):
    reference = load_reference(user_id)
    if not reference:
        return []
    path = resolve_reference(reference["path"])
    from core.ncc_catalog import check_owner, search_catalog
    try:
        check_owner(library_root(), path, user_id)
        relative_parts = path.relative_to(library_root()).parts
        configured_default = os.getenv("NCC_DEFAULT_REFERENCE", "").strip()
        managed = (relative_parts and relative_parts[0] == "private") or (configured_default and path == resolve_reference(configured_default))
        if managed and (not path.is_dir() or not (path / ".ncc-index.sqlite3").is_file()):
            raise NCCReferenceError("The managed NCC catalog index is unavailable. Rebuild the catalog; unfiltered PDF or older-edition fallback is disabled.")
        if path.is_dir():
            indexed = search_catalog(user_id, path, query, context, top_k)
            if indexed is not None:
                return indexed
    except PermissionError as exc:
        raise NCCReferenceError(str(exc)) from None
    query_words = set(_tokens(query))
    candidates = []
    for file in reference_files(reference["path"], user_id=user_id):
        stat = file.stat()
        for page, text in _read_pages(str(file), stat.st_mtime_ns, stat.st_size):
            for chunk in chunk_text(text):
                words = Counter(_tokens(chunk))
                score = sum(1 + math.log(words[word]) for word in query_words if words[word])
                if not score:
                    continue
                clause = re.search(r"\b(?:[A-Z]{1,3}\d+[A-Z]\d+(?:\.\d+)*|[A-Z]\d+\.\d+)\b", chunk)
                candidates.append({"text": chunk, "score": score, "metadata": {
                    "source": f"{file.name}, p. {page}", "page": page,
                    "code": reference["edition"], "clause": clause.group() if clause else "",
                    "reference_kind": "server_local_ncc",
                }})
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:top_k]


def load_project_context(user_id, project_id):
    import project_store
    project = project_store.require_project_access(int(user_id), int(project_id))
    with _connection() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS ncc_project_context(user_id TEXT, project_id INTEGER, edition TEXT, building_class TEXT, jurisdiction TEXT, PRIMARY KEY(user_id,project_id))")
        row = connection.execute("SELECT edition,building_class,jurisdiction FROM ncc_project_context WHERE user_id=? AND project_id=?", (str(user_id), int(project_id))).fetchone()
    context = dict(zip(("edition", "building_class", "jurisdiction"), row)) if row else {}
    # Explicit details in the owned project description are useful defaults.
    description = project.get("description", "") or ""
    match = re.search(r"\bNCC\s*(2022|2025)\b", description, re.I)
    if match and not context.get("edition"): context["edition"] = match.group(1)
    match = re.search(r"\bclass\s*(10|[1-9])\s*([abc])?\b", description, re.I)
    if match and not context.get("building_class"): context["building_class"] = match.group(1) + (match.group(2) or "")
    for state in ("VIC", "NSW", "QLD", "SA", "WA", "TAS", "NT", "ACT"):
        if re.search(r"\b" + state + r"\b", description) and not context.get("jurisdiction"):
            context["jurisdiction"] = state
    return context


def save_project_context(user_id, project_id, edition, building_class, jurisdiction):
    load_project_context(user_id, project_id)  # Enforce owner access and initialize schema.
    if edition not in ("", "2022", "2025") or building_class not in ("", "1a", "1b", "2", "3", "4", "5", "6", "7a", "7b", "8", "9a", "9b", "9c", "10a", "10b", "10c") or jurisdiction not in ("", "VIC", "NSW", "QLD", "SA", "WA", "TAS", "NT", "ACT"):
        raise NCCReferenceError("Choose a valid NCC project context.")
    with _connection() as connection:
        connection.execute("INSERT INTO ncc_project_context VALUES(?,?,?,?,?) ON CONFLICT(user_id,project_id) DO UPDATE SET edition=excluded.edition,building_class=excluded.building_class,jurisdiction=excluded.jurisdiction", (str(user_id), int(project_id), edition, building_class, jurisdiction))


def has_catalog(user_id):
    reference = load_reference(user_id)
    if not reference: return False
    path = resolve_reference(reference["path"])
    from core.ncc_catalog import check_owner
    try:
        check_owner(library_root(), path, user_id)
    except PermissionError as exc:
        raise NCCReferenceError(str(exc)) from None
    return path.is_dir() and (path / ".ncc-index.sqlite3").is_file()
