import re
from io import BytesIO


MIN_CHUNK_SIZE = 500
MAX_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(file_bytes: bytes) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return clean_text("\n".join(pages))


def extract_txt_text(file_bytes: bytes) -> str:
    try:
        return clean_text(file_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        return clean_text(file_bytes.decode("latin-1", errors="ignore"))


def extract_document_text(filename: str, file_bytes: bytes) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower()
    if suffix == "pdf":
        return extract_pdf_text(file_bytes)
    if suffix == "txt":
        return extract_txt_text(file_bytes)
    raise ValueError("Unsupported document type. Upload a PDF or TXT file.")


def chunk_text(text: str) -> list:
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []

    chunks = []
    start = 0
    text_length = len(cleaned_text)

    while start < text_length:
        end = min(start + MAX_CHUNK_SIZE, text_length)
        chunk = cleaned_text[start:end]

        if end < text_length:
            split_at = max(chunk.rfind("\n\n"), chunk.rfind(". "), chunk.rfind(" "))
            if split_at >= MIN_CHUNK_SIZE:
                end = start + split_at + 1
                chunk = cleaned_text[start:end]

        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


def infer_document_type(filename: str, text: str) -> str:
    signal = f"{filename}\n{text[:2000]}".lower()
    if "ncc" in signal or "national construction code" in signal or "building code" in signal:
        return "ncc"
    return "business"


def process_document(filename: str, file_bytes: bytes, document_type: str | None = None) -> list[dict]:
    text = extract_document_text(filename, file_bytes)
    resolved_type = document_type or infer_document_type(filename, text)

    return [
        {
            "text": chunk,
            "metadata": {
                "source": filename,
                "type": resolved_type,
            },
        }
        for chunk in chunk_text(text)
    ]
