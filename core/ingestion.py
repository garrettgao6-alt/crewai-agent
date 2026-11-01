"""Single project-authorized ingestion route for automatic and explicit types."""
from hashlib import sha256
from io import BytesIO
from threading import RLock
from core.document_pipeline import extract_document_text, infer_document_type, chunk_text
from core.ncc_parser import parse_ncc_clauses, clauses_to_documents
from core.vector_store import add_documents, add_ncc_documents, get_collection, get_ncc_collection
import project_store

_ingestion_lock = RLock()


def ingest_document(user_id, project_id, filename, data, document_type=None, edition="Unspecified edition", *, managed_version_id=None):
    scope = project_store.document_scope(user_id, project_id)
    from core import document_store
    if managed_version_id:
        document_store.validate_managed_version(user_id,project_id,managed_version_id,filename,sha256(data).hexdigest())
    elif document_store.is_managed(user_id,project_id,filename):
        raise ValueError('This file has retained versions. Use the document library to replace it safely.')
    if len(data) > 50 * 1024 * 1024:
        raise ValueError("Document exceeds the 50 MB file limit.")
    if managed_version_id and not filename.lower().endswith('.txt'):
        from core.file_processing import document_pages
        pages=document_pages(filename,data)
    else:
        from core.document_pipeline import native_pages
        pages=native_pages(filename,data)
    text = '\n'.join(content for _, content in pages)
    if not text.strip():
        raise ValueError("No extractable text. Scanned PDFs must be processed with OCR first.")
    kind = document_type or infer_document_type(filename, text)
    regulatory = kind in {'ncc', 'housing'}
    if regulatory and (not edition.strip() or edition == 'Unspecified edition'):
        raise ValueError("Enter the actual NCC edition and volume before indexing regulatory documents.")
    docs, metadata = [], []
    digest = sha256(data).hexdigest()
    for page, content in pages:
        if regulatory:
            page_docs, page_metadata = clauses_to_documents(parse_ncc_clauses(content), filename, code=edition)
            if not page_docs:
                page_docs = chunk_text(content)
                page_metadata = [{'source':filename,'code':edition,'type':'general','clause':''} for _ in page_docs]
        else:
            page_docs = chunk_text(content)
            page_metadata = [{'source':filename,'type':kind} for _ in page_docs]
        for item in page_metadata:
            item.update(user_id=str(user_id),project_id=int(project_id),document_sha256=digest,page=page)
            if managed_version_id:item["managed_version_id"]=managed_version_id
            if regulatory:
                item['reference_kind'] = 'project_ncc'
        docs.extend(page_docs)
        metadata.extend(page_metadata)
    if len(docs)>60:raise ValueError('The document exceeds 60 searchable chunks. Split it before indexing.')
    if not docs:
        raise ValueError('No searchable text could be extracted.')
    # Serialize replacement in this application process. Upsert first; a failed
    # embedding leaves the previous indexed version intact.
    with _ingestion_lock:
        target = get_ncc_collection(scope, housing=kind=='housing') if regulatory else get_collection(scope)
        collections = [get_collection(scope),get_ncc_collection(scope),get_ncc_collection(scope,housing=True)]
        old_ids = [(collection, collection.get(where={'source':filename},include=[])['ids']) for collection in collections]
        count = (add_ncc_documents(scope,docs,metadata,housing=kind=='housing') if regulatory else add_documents(scope,docs,metadata))
        current = set(target.get(where={'$and':[{'source':filename},{'document_sha256':digest}]},include=[])['ids'])
        for collection, ids in ([] if managed_version_id else old_ids):
            obsolete = set(ids) - current if collection.name == target.name else set(ids)
            if obsolete:
                collection.delete(ids=list(obsolete))
    return count
