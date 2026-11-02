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


def _office_archive(data):
    import zipfile
    archive=zipfile.ZipFile(BytesIO(data));items=archive.infolist()
    if len(items)>5000 or sum(i.file_size for i in items)>40*1024*1024 or any(i.file_size>20*1024*1024 for i in items):
        raise ValueError('Office document exceeds the safe expanded-size limit. Split the file.')
    return archive


def native_pages(filename,data):
    suffix=filename.rsplit('.',1)[-1].lower()
    if suffix=='pdf':
        from PyPDF2 import PdfReader
        reader=PdfReader(BytesIO(data))
        if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported. Upload an unlocked copy.')
        if len(reader.pages)>500:raise ValueError('PDF exceeds 500 pages. Split the file.')
        pages=[(n,page.extract_text() or '') for n,page in enumerate(reader.pages,1)]
    elif suffix=='docx':
        from docx import Document
        _office_archive(data).close();document=Document(BytesIO(data))
        text=[p.text for p in document.paragraphs]
        for table in document.tables:
            text.extend(' | '.join(cell.text for cell in row.cells) for row in table.rows)
        pages=[(1,'\n'.join(text))]
    elif suffix=='xlsx':
        from openpyxl import load_workbook
        _office_archive(data).close();book=load_workbook(BytesIO(data),read_only=True,data_only=False,keep_links=False)
        pages=[];cells=0
        try:
            for number,sheet in enumerate(book.worksheets,1):
                rows=['Worksheet: '+sheet.title]
                for row in sheet.iter_rows():
                    cells+=len(row)
                    if cells>100000:raise ValueError('Workbook exceeds 100,000 cells. Split the file.')
                    values=['%s: %s'%(cell.coordinate,str(cell.value)) for cell in row if cell.value is not None]
                    if values:rows.append(' | '.join(values))
                pages.append((number,'\n'.join(rows)))
        finally:book.close()
    elif suffix=='txt':pages=[(1,extract_txt_text(data))]
    else:raise ValueError('Supported searchable documents: PDF, TXT, DOCX and XLSX.')
    if sum(len(text.encode('utf-8')) for _,text in pages)>80000:raise ValueError('Extracted text exceeds the 80 KB indexing limit. Split the document; the original is retained.')
    return pages


def extract_document_text(filename: str,file_bytes: bytes)->str:
    return clean_text('\n'.join(text for _,text in native_pages(filename,file_bytes)))


def split_by_sections(text: str):
    sections = re.split(r"(Section \d+\.?\d*|Clause \d+\.?\d*)", clean_text(text))

    chunks = []

    for i in range(1, len(sections), 2):
        title = sections[i]
        content = sections[i + 1] if i + 1 < len(sections) else ""
        chunk = clean_text(title + content)
        if chunk:
            chunks.append(chunk)

    return chunks


def semantic_chunk(text):
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []

    chunks = []
    current = ""

    for sentence in cleaned_text.split(". "):
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence_text = sentence if sentence.endswith(".") else sentence + "."
        if len(current) + len(sentence_text) < 800:
            current += sentence_text + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence_text + " "

    if current.strip():
        chunks.append(current.strip())

    return chunks


def chunk_text(text: str) -> list:
    structured = split_by_sections(text)

    if len(structured) > 3:
        return structured

    return semantic_chunk(text)


def infer_document_type(filename: str, text: str) -> str:
    # Project notes routinely mention the NCC. That does not make those notes
    # a code publication or justify indexing their claims as regulatory text.
    import re
    from pathlib import Path
    title = Path(filename).stem.lower().replace('_', ' ').replace('-', ' ')
    project_document = re.search(r'\b(notes?|reports?|reviews?|assessments?|plans?|checklists?|summar(?:y|ies))\b', title)
    publication = re.search(r'\bncc\s*(?:20\d{2})?\s*(?:(?:abcb\s*)?(?:volume\s*(?:one|two|1|2)|housing\s+provisions))?\s*(?:\(\d+\))?$', title)
    if not project_document and (publication or 'national construction code' in title):
        return 'housing' if 'housing provisions' in title else 'ncc'
    # A strong publication heading is useful for generically named PDFs, but
    # incidental mentions anywhere in the body must remain project evidence.
    heading = text[:250].strip().lower()
    if not project_document and re.match(r'(?:ncc\s*20\d{2}|national construction code\s*20\d{2})\s*[:\-\n ]*volume\s*(?:one|two|1|2)\b', heading):
        return 'ncc'
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
