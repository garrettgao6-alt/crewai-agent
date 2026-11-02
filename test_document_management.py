from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import json,sqlite3,time
import pytest
from test_project_integrity import system as legacy_system
from core import document_store as store,vector_store
from core.ingestion import ingest_document
import project_store,subscription_store,report_store


@pytest.fixture
def system(legacy_system,monkeypatch):
    monkeypatch.setattr(vector_store,'embed_batch',lambda chunks:[vector_store.embed_text(chunk).tolist() for chunk in chunks])
    return legacy_system


def query(owner,project):return vector_store.search_chunks(project_store.document_scope(owner,project),'project evidence')

def test_managed_versions_restore_archive_and_original_isolation(system):
    a,b,p,q,_=system
    first=store.upload(a['id'],p['id'],'plan.txt',b'Original project evidence ALPHA',kind='business')
    again=store.upload(a['id'],p['id'],'plan.txt',b'Original project evidence ALPHA',kind='business')
    assert first['id']==again['id'] and subscription_store.get_usage(a['id'])['current_document_count']==1
    saved=report_store.save_report(a['id'],p['id'],{'result':'Snapshot','sources':query(a['id'],p['id'])})
    second=store.upload(a['id'],p['id'],'PLAN.txt',b'Changed project evidence BRAVO',kind='business')
    assert second['version']==2 and len(store.versions(a['id'],p['id'],first['file_id']))==2
    assert 'BRAVO' in query(a['id'],p['id'])[0]['text'] and len(query(a['id'],p['id']))==1
    assert store.original(a['id'],p['id'],first['file_id'],first['id'])==b'Original project evidence ALPHA'
    with pytest.raises(PermissionError):store.original(b['id'],p['id'],first['file_id'],first['id'])
    with pytest.raises(PermissionError):store.original(a['id'],q['id'],first['file_id'],first['id'])
    store.set_archived(a['id'],p['id'],first['file_id']);assert query(a['id'],p['id'])==[]
    assert store.list_files(a['id'],p['id'])==[] and store.list_files(a['id'],p['id'],True)
    assert report_store.get_report(a['id'],p['id'],saved['id'])['sources']==saved['sources']
    store.activate_version(a['id'],p['id'],first['file_id'],first['id'])
    assert 'ALPHA' in query(a['id'],p['id'])[0]['text'] and subscription_store.get_usage(a['id'])['current_document_count']==2


def test_failed_replacement_keeps_active_and_refunds_document_allowance(system,monkeypatch):
    a,_,p,_,_=system
    first=store.upload(a['id'],p['id'],'plan.txt',b'Active evidence',kind='business')
    def fail(*args):raise RuntimeError('SECRET_TOKEN')
    monkeypatch.setattr(vector_store,'embed_text',fail)
    with pytest.raises(ValueError,match='Processing failed') as exc:store.upload(a['id'],p['id'],'plan.txt',b'New evidence',kind='business')
    assert 'SECRET_TOKEN' not in str(exc.value)
    assert store.list_files(a['id'],p['id'])[0]['active_version']==first['id']
    history=store.versions(a['id'],p['id'],first['file_id'])
    assert history[0]['status']=='failed' and history[0]['charged']==0
    assert subscription_store.get_usage(a['id'])['current_document_count']==1


def test_legacy_index_survives_failed_first_managed_attempt(system,monkeypatch):
    a,_,p,_,_=system
    ingest_document(a['id'],p['id'],'old.txt',b'Legacy original evidence',document_type='business')
    assert store.legacy_indexes(a['id'],p['id'])
    import core.ingestion
    original=core.ingestion.ingest_document
    def partial(*args,**kwargs):original(*args,**kwargs);raise RuntimeError('Failed before activation')
    monkeypatch.setattr(core.ingestion,'ingest_document',partial)
    with pytest.raises(ValueError):store.upload(a['id'],p['id'],'old.txt',b'Failed new evidence',kind='business')
    chunks=query(a['id'],p['id']);assert len(chunks)==1 and 'Legacy' in chunks[0]['text']


def test_one_analysis_uses_one_document_manifest_during_replacement(system):
    a,_,p,_,_=system;scope=project_store.document_scope(a['id'],p['id'])
    store.upload(a['id'],p['id'],'plan.txt',b'Version ALPHA evidence',kind='business')
    with store.retrieval_snapshot(scope):
        store.upload(a['id'],p['id'],'plan.txt',b'Version BRAVO evidence',kind='business')
        assert 'ALPHA' in query(a['id'],p['id'])[0]['text']
    assert 'BRAVO' in query(a['id'],p['id'])[0]['text']


def test_concurrent_duplicate_upload_only_creates_and_charges_once(system):
    a,_,p,_,_=system
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:store.upload(a['id'],p['id'],'same.txt',b'Same evidence',kind='business'),range(2)))
    assert results[0]['id']==results[1]['id']
    assert subscription_store.get_usage(a['id'])['current_document_count']==1


def test_interrupted_processing_is_recoverable_and_refunded_once(system):
    a,_,p,_,_=system
    version=store.upload(a['id'],p['id'],'plan.txt',b'Evidence',kind='business')
    with store.connect() as c:
        c.execute("UPDATE document_versions SET status='processing',created=? WHERE id=?",(int(time.time())-1800,version['id']))
        c.execute('UPDATE document_files SET active_version=NULL WHERE id=?',(version['file_id'],))
    store.recover_interrupted(a['id'],p['id']);store.recover_interrupted(a['id'],p['id'])
    assert store.versions(a['id'],p['id'],version['file_id'])[0]['status']=='failed'
    assert subscription_store.get_usage(a['id'])['current_document_count']==0
    assert store.original(a['id'],p['id'],version['file_id'],version['id'])==b'Evidence'


def test_original_checksum_tampering_cannot_be_activated(system):
    a,_,p,_,_=system
    version=store.upload(a['id'],p['id'],'plan.txt',b'Evidence',kind='business')
    store.path_for(version).write_bytes(b'Changed on disk')
    with pytest.raises(RuntimeError,match='checksum'):store.activate_version(a['id'],p['id'],version['file_id'],version['id'])


def test_filename_storage_and_quota_boundaries(system,monkeypatch):
    a,_,p,_,_=system
    for name in ('../a.txt','folder/a.txt','x.exe'):
        with pytest.raises(ValueError):store.upload(a['id'],p['id'],name,b'Content')
    monkeypatch.setattr(store,'OWNER_BYTES',3)
    with pytest.raises(PermissionError):store.upload(a['id'],p['id'],'file.txt',b'long evidence')
    assert subscription_store.get_usage(a['id'])['current_document_count']==0


def test_docx_tables_and_xlsx_cells_are_searchable(system):
    from docx import Document
    from openpyxl import Workbook
    a,_,p,_,_=system
    doc=Document();doc.add_paragraph('Contract terms');doc.add_table(rows=1,cols=1).cell(0,0).text='PAYMENT_EVIDENCE_42'
    data=BytesIO();doc.save(data)
    v=store.upload(a['id'],p['id'],'contract.docx',data.getvalue(),kind='business');assert v['status']=='ready'
    book=Workbook();book.active.title='Costs';book.active['A1']='COST_EVIDENCE_42';book.active['B1']='=1+1'
    data=BytesIO();book.save(data)
    store.upload(a['id'],p['id'],'costs.xlsx',data.getvalue(),kind='business')
    text=' '.join(chunk['text'] for chunk in query(a['id'],p['id']))
    assert 'PAYMENT_EVIDENCE_42' in text and 'COST_EVIDENCE_42' in text and '=1+1' in text


def test_failed_large_extraction_is_retained_without_search_or_charge(system):
    a,_,p,_,_=system
    with pytest.raises(ValueError,match='80 KB'):store.upload(a['id'],p['id'],'large.txt',b'E'*80001,kind='business')
    file=store.list_files(a['id'],p['id'])[0];version=store.versions(a['id'],p['id'],file['id'])[0]
    assert version['status']=='failed' and len(store.original(a['id'],p['id'],file['id'],version['id']))==80001
    assert subscription_store.get_usage(a['id'])['current_document_count']==0 and query(a['id'],p['id'])==[]


def test_scan_has_explicit_failed_status_not_a_successful_index(system):
    from reportlab.pdfgen import canvas
    a,_,p,_,_=system;data=BytesIO();pdf=canvas.Canvas(data);pdf.showPage();pdf.save()
    with pytest.raises(ValueError,match='OCR'):store.upload(a['id'],p['id'],'scan.pdf',data.getvalue(),kind='business')
    assert store.list_files(a['id'],p['id'])[0]['status']=='failed'
    assert subscription_store.get_usage(a['id'])['current_document_count']==0


def test_document_ui_reconnect_archive_and_project_switch_are_private(system,monkeypatch):
    from streamlit.testing.v1 import AppTest
    import template_store
    a,_,p,q,_=system;version=store.upload(a['id'],p['id'],'private.txt',b'PRIVATE_ORIGINAL_MARKER',kind='business')
    monkeypatch.setattr(template_store,'DB_PATH',Path(project_store.DB_PATH).with_name('templates.db'))
    token=__import__('user_store').create_session(a['id'])
    source=Path('streamlit_app.py').read_text().replace('auth_cookies = initialize_cookie_manager()',f'auth_cookies = {{"session_token": {token!r}}}')
    app=AppTest.from_string(source,default_timeout=30).run()
    app.session_state['active_project_id']=p['id'];app.session_state['active_section']='Documents';app.run()
    assert not app.exception
    links=' '.join(item.value for item in app.markdown)
    assert 'Download original' in links and '/private-download/' in links and token not in links
    assert '/media/' not in links
    next(button for button in app.button if button.label=='Archive file').click().run()
    assert store.list_files(a['id'],p['id'])==[]
    app.session_state['active_project_id']=q['id'];app.run()
    assert not app.exception and not any('Download original' in item.value for item in app.markdown)


def test_monthly_quota_is_backend_enforced_without_losing_the_original(system):
    a,_,p,_,_=system
    with __import__('user_store').get_connection() as c:c.execute('UPDATE users SET monthly_document_limit=0 WHERE id=?',(a['id'],))
    with pytest.raises(ValueError,match='quota'):store.upload(a['id'],p['id'],'quota.txt',b'Original retained despite quota denial',kind='business')
    file=store.list_files(a['id'],p['id'])[0];v=store.versions(a['id'],p['id'],file['id'])[0]
    assert store.original(a['id'],p['id'],file['id'],v['id'])==b'Original retained despite quota denial'
    assert query(a['id'],p['id'])==[]


def test_restore_verifier_covers_managed_originals_and_ownership(system):
    from deploy.operations import verify_document_store
    a,_,p,_,_=system
    version=store.upload(a['id'],p['id'],'backup.txt',b'Backup original',kind='business')
    verify_document_store(Path(project_store.DB_PATH).parent)
    store.path_for(version).write_bytes(b'Corrupt original')
    with pytest.raises(RuntimeError,match='integrity'):verify_document_store(Path(project_store.DB_PATH).parent)


def test_managed_embedding_batch_is_one_bounded_provider_request(monkeypatch):
    from types import SimpleNamespace
    calls=[]
    def create(**kwargs):
        calls.append(kwargs);return SimpleNamespace(data=[SimpleNamespace(index=1,embedding=[0.,1.]),SimpleNamespace(index=0,embedding=[1.,0.])])
    monkeypatch.setattr(vector_store,'_get_client',lambda:SimpleNamespace(embeddings=SimpleNamespace(create=create)))
    assert vector_store.embed_batch(['one','two'])==[[1.,0.],[0.,1.]]
    assert len(calls)==1 and calls[0]['input']==['one','two']


def test_auto_detected_project_notes_mentioning_ncc_are_not_regulatory(system):
    owner,_,project,other,_=system
    evidence=b'Class 1a dwelling. NCC 2025 external wall review. Missing fire resistance evidence. PROJECT_NOTES_MARKER'
    version=store.upload(owner['id'],project['id'],'review-notes.txt',evidence)
    assert version['status']=='ready'
    scope=project_store.document_scope(owner['id'],project['id'])
    hits=vector_store.retrieve('PROJECT_NOTES_MARKER',user_id=scope)
    assert hits and all(item['metadata']['type']=='business' for item in hits)
    assert vector_store.search_ncc_chunks(scope,'PROJECT_NOTES_MARKER')==[]
    assert query(owner['id'],other['id'])==[]


def test_publication_auto_detection_still_requires_edition(system):
    from core.document_pipeline import infer_document_type
    owner,_,project,_,_=system
    assert infer_document_type('NCC 2025 Housing Provisions.pdf','')=='housing'
    assert infer_document_type('NCC 2025 Volume Two (1).pdf','')=='ncc'
    assert infer_document_type('NCC compliance report.txt','NCC 2025 Volume Two\nProject review')=='business'
    with pytest.raises(ValueError,match='edition'):
        store.upload(owner['id'],project['id'],'ncc.txt',b'C2D2 Code publication fixture')
