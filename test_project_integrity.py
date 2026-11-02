"""Acceptance tests for authenticated, project-scoped document-to-report flow."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

import project_store
import report_store
import user_store
import subscription_store
from core import vector_store, engine, retriever, ncc_library
from core.ingestion import ingest_document
from core.memory import Memory


@pytest.fixture
def system(tmp_path, monkeypatch):
    import chromadb
    from chromadb.config import Settings
    for module, name in ((user_store,'users'),(subscription_store,'users'),(project_store,'projects'),(report_store,'reports'),(ncc_library,'ncc')):
        monkeypatch.setattr(module, 'DB_PATH', tmp_path / f'{name}.db')
    monkeypatch.delenv('ADMIN_USERNAME', raising=False)
    monkeypatch.delenv('ADMIN_PASSWORD', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('COPILOT_MEMORY_DB', str(tmp_path / 'memory.db'))
    monkeypatch.setattr(engine, 'memory', Memory())
    monkeypatch.setattr(vector_store, 'client', chromadb.PersistentClient(path=str(tmp_path / 'chroma'), settings=Settings(anonymized_telemetry=False)))
    # Fixed test embedding: real Chroma writes/queries, no paid provider calls.
    monkeypatch.setattr(vector_store, 'embed_text', lambda _: np.array([1.0,0.0,0.0]))
    monkeypatch.setattr(engine, 'plan_tasks', lambda _: ['analysis'])
    monkeypatch.setattr(engine, 'route_task', lambda _: 'construction')
    monkeypatch.setattr(retriever, 'rerank', lambda _, chunks: chunks)
    user_store.initialize_user_store()
    project_store.initialize_project_store()
    alice = user_store.create_user('alice', 'alice@example.com', 'safe-test-password')
    bob = user_store.create_user('bob', 'bob@example.com', 'safe-test-password')
    a = project_store.create_project(alice['id'], 'A')
    b = project_store.create_project(alice['id'], 'B')
    c = project_store.create_project(bob['id'], 'C')
    return alice, bob, a, b, c


def test_document_namespaces_are_disjoint_and_forged_access_rejected(system):
    alice, bob, a, b, c = system
    ingest_document(alice['id'], a['id'], 'ncc.txt', b'C2D2 Fire walls for ALPHA project', edition='Test code A')
    ingest_document(alice['id'], b['id'], 'ncc.txt', b'D2D3 Exit requirements for BRAVO project', edition='Test code B')
    ingest_document(bob['id'], c['id'], 'ncc.txt', b'H1D2 Housing for CHARLIE project', edition='Test code C')
    for user, project, expected in ((alice,a,'ALPHA'),(alice,b,'BRAVO'),(bob,c,'CHARLIE')):
        chunks = vector_store.search_ncc_chunks(project_store.document_scope(user['id'], project['id']), 'NCC')
        assert len(chunks) == 1 and expected in chunks[0]['text']
        assert chunks[0]['metadata']['project_id'] == project['id']
    with pytest.raises(PermissionError):
        ingest_document(bob['id'], a['id'], 'x.txt', b'private')
    with pytest.raises(PermissionError):
        engine.run_engine(str(bob['id']), 'NCC', project_id=a['id'])
    with pytest.raises(PermissionError):
        project_store.add_project_history(a['id'], 'upload', 'forged', user_id=bob['id'])
    with pytest.raises(PermissionError):
        project_store.list_project_history(a['id'], user_id=bob['id'])


def test_concurrent_analysis_returns_own_sources_and_scoped_memory(system, monkeypatch):
    alice, bob, a, b, c = system
    ingest_document(alice['id'], a['id'], 'alpha.txt', b'C2D2 Fire walls ALPHA', document_type='ncc', edition='NCC test A')
    ingest_document(bob['id'], c['id'], 'charlie.txt', b'D2D3 Exit travel CHARLIE', document_type='ncc', edition='NCC test C')
    barrier = Barrier(2)
    def model(prompt):
        barrier.wait(timeout=10)
        return 'Assessment based on ALPHA evidence' if 'ALPHA' in prompt else 'Assessment based on CHARLIE evidence'
    monkeypatch.setattr(engine, 'run_construction_agent', model)
    def analyze(user, project):
        return engine.run_engine(str(user['id']), 'NCC requirements', project_id=project['id'], return_details=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(analyze, alice, a)
        fc = pool.submit(analyze, bob, c)
        ra, rc = fa.result(), fc.result()
    assert {item['metadata']['source'] for item in ra['sources']} == {'alpha.txt'}
    assert {item['metadata']['source'] for item in rc['sources']} == {'charlie.txt'}
    assert 'CHARLIE' not in ra['result'] and 'ALPHA' not in rc['result']
    assert engine.memory.get(project_store.document_scope(alice['id'], b['id'])) == []
    assert len(engine.memory.get(project_store.document_scope(alice['id'], a['id']))) == 2
    assert engine.memory.get(alice['id']) == []


def test_local_references_and_project_evidence_are_combined_and_saved(system, tmp_path, monkeypatch):
    alice, bob, a, b, c = system
    root = tmp_path / 'references'
    root.mkdir()
    (root/'ncc.txt').write_text('C2D2 Fire resistance of walls and exits. REFERENCE ORIGINAL')
    monkeypatch.setenv('NCC_DOCUMENT_ROOT', str(root))
    ncc_library.save_reference(alice['id'], 'ncc.txt', 'Test edition')
    ingest_document(alice['id'], a['id'], 'design.txt', b'Design has fire wall evidence PROJECT ALPHA', document_type='business')
    monkeypatch.setattr(engine, 'run_construction_agent', lambda prompt: 'REFERENCE ORIGINAL and PROJECT ALPHA checked in supplied context.')
    payload = engine.run_engine(str(alice['id']), 'NCC fire walls', project_id=a['id'], return_details=True)
    assert {s['metadata']['source'] for s in payload['sources']} == {'ncc.txt, p. 1', 'design.txt'}
    entry = report_store.save_report(alice['id'], a['id'], {**payload, 'query':'NCC fire walls', 'mode':'Copilot'})
    original_snapshot = json.loads(json.dumps(entry['sources']))
    (root/'ncc.txt').write_text('C2D2 Fire resistance CHANGED LATER')
    # New connection reloads immutable full report/evidence, not session state.
    reloaded = report_store.get_report(alice['id'], a['id'], entry['id'])
    assert reloaded['sources'] == original_snapshot
    for source in reloaded['sources']:
        material = {k: source[k] for k in ('text','metadata')}
        assert hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == source['sha256']
    assert report_store.list_reports(alice['id'], b['id']) == []
    assert report_store.get_report(alice['id'], b['id'], entry['id']) is None
    with pytest.raises(PermissionError):
        report_store.get_report(bob['id'], a['id'], entry['id'])


def test_missing_ncc_evidence_refuses_compliance_conclusion(system, monkeypatch):
    alice, _, a, _, _ = system
    ingest_document(alice['id'], a['id'], 'design.txt', b'Unverified fire wall claim', document_type='business')
    monkeypatch.setattr(engine, 'run_construction_agent', lambda _: pytest.fail('Must not invent regulatory assessment'))
    result = engine.run_engine(str(alice['id']), 'NCC fire compliance', project_id=a['id'], return_details=True)
    assert result['status'] == 'insufficient_evidence'
    assert 'Insufficient NCC reference found' in result['result']


def test_embedding_failure_is_explicit_instead_of_changing_dimensions(monkeypatch):
    monkeypatch.setattr(vector_store, '_get_client', lambda: (_ for _ in ()).throw(RuntimeError('offline')))
    # This test intentionally exercises real production embed_text, unlike the fixture.
    with pytest.raises(RuntimeError, match='Embedding service unavailable'):
        vector_store.embed_text('do not silently downgrade')


def test_integer_user_memory_does_not_mean_global_limit(system):
    engine.memory.add(101, 'user', 'PRIVATE101')
    engine.memory.add('default', 'user', 'UNRELATED')
    assert engine.memory.get(101) == [{'role':'user','content':'PRIVATE101'}]


def test_authenticated_ui_restores_reports_and_clears_project_state(system, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import prompt_store
    import template_store
    alice, _, a, b, _ = system
    token = user_store.create_session(alice['id'])
    report_store.save_report(alice['id'], a['id'], {'query':'saved finding','mode':'Copilot','result':'PERSISTED REPORT','status':'draft','sources':[]})
    monkeypatch.setattr(template_store, 'DB_PATH', report_store.DB_PATH.with_name('templates.db'))
    source = Path('streamlit_app.py').read_text().replace('auth_cookies = initialize_cookie_manager()', f'auth_cookies = {{"session_token": {token!r}}}')
    def start(project):
        app = AppTest.from_string(source, default_timeout=30)
        app.session_state['active_project_id'] = project
        app.session_state['active_section'] = 'Reports'
        return app.run()
    app = start(a['id'])
    assert not app.exception
    assert any('PERSISTED REPORT' in item.value for item in app.markdown)
    fresh = start(a['id'])
    assert not fresh.exception
    assert fresh.session_state['history'][0]['result'] == 'PERSISTED REPORT'
    fresh.session_state['copilot_history'] = [{'response':'PRIVATE PROJECT A'}]
    fresh.session_state['active_project_id'] = b['id']
    fresh.run()
    assert not fresh.exception
    assert fresh.session_state['history'] == []
    assert fresh.session_state['copilot_history'] == []
    assert fresh.session_state['selected_history'] is None


def test_reupload_replaces_old_ncc_chunks_without_mutating_saved_reports(system, monkeypatch):
    alice, _, a, _, _ = system
    ingest_document(alice['id'], a['id'], 'ncc.txt', b'C2D2 OLD fire requirement', edition='Test old')
    monkeypatch.setattr(engine, 'run_construction_agent', lambda _: 'Assessment of OLD supplied requirement, retained for audit.')
    payload = engine.run_engine(str(alice['id']), 'NCC fire', project_id=a['id'], return_details=True)
    saved = report_store.save_report(alice['id'], a['id'], payload)
    ingest_document(alice['id'], a['id'], 'ncc.txt', b'C2D2 NEW fire requirement', edition='Test new')
    chunks = vector_store.search_ncc_chunks(project_store.document_scope(alice['id'],a['id']), 'NCC fire')
    assert len(chunks) == 1 and 'NEW' in chunks[0]['text'] and 'OLD' not in chunks[0]['text']
    assert 'OLD' in report_store.get_report(alice['id'],a['id'],saved['id'])['sources'][0]['text']


def test_failed_reupload_preserves_previous_index(system, monkeypatch):
    alice, _, a, _, _ = system
    ingest_document(alice['id'], a['id'], 'ncc.txt', b'C2D2 Previous fire requirement', edition='Test')
    with monkeypatch.context() as failure:
        failure.setattr(vector_store, 'embed_text', lambda _: (_ for _ in ()).throw(RuntimeError('provider failure')))
        with pytest.raises(RuntimeError):
            ingest_document(alice['id'], a['id'], 'ncc.txt', b'C2D2 Replacement fire requirement', edition='Test')
    chunks = vector_store.search_ncc_chunks(project_store.document_scope(alice['id'],a['id']), 'NCC')
    assert 'Previous' in chunks[0]['text']


def test_pdf_ingestion_preserves_page_and_modern_clause(system):
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    alice, _, a, _, _ = system
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(40,750,'C2D2 Type of construction')
    canvas.showPage()
    canvas.drawString(40,750,'D2D3 Number of exits')
    canvas.save()
    assert ingest_document(alice['id'],a['id'],'ncc.pdf',buffer.getvalue(),edition='Test code') == 2
    chunks = vector_store.search_ncc_chunks(project_store.document_scope(alice['id'],a['id']), 'NCC')
    assert {(c['metadata']['clause'],c['metadata']['page']) for c in chunks} == {('C2D2',1),('D2D3',2)}
    assert 'p. 2' in vector_store.format_sources(chunks)


def test_context_local_compatibility_references_do_not_cross_threads():
    first_ready, second_ready = Event(), Event()
    def first():
        vector_store.set_last_retrieval([{'text':'A','metadata':{'source':'A.txt'}}])
        first_ready.set()
        assert second_ready.wait(5)
        return vector_store.get_last_retrieval()
    def second():
        assert first_ready.wait(5)
        vector_store.set_last_retrieval([{'text':'B','metadata':{'source':'B.txt'}}])
        second_ready.set()
        return vector_store.get_last_retrieval()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(first), pool.submit(second)
        assert a.result()[0]['text'] == 'A'
        assert b.result()[0]['text'] == 'B'


def test_chinese_ncc_question_retrieves_local_english_fire_references(system, tmp_path, monkeypatch):
    alice, _, a, _, _ = system
    root = tmp_path / 'refs'
    root.mkdir()
    (root/'ncc.txt').write_text('C2D2 Fire resistance of walls and emergency exits')
    monkeypatch.setenv('NCC_DOCUMENT_ROOT',str(root))
    ncc_library.save_reference(alice['id'],'ncc.txt','Test edition')
    chunks = retriever.retrieve_multi(project_store.document_scope(alice['id'],a['id']),'请检查防火墙及紧急出口是否符合规范',reference_user_id=alice['id'])
    assert chunks and chunks[0]['metadata']['clause'] == 'C2D2'


def test_authenticated_copilot_to_persistent_report_and_pdf_ui(system, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import template_store
    alice, _, a, _, _ = system
    ingest_document(alice['id'],a['id'],'ncc.txt',b'C2D2 Fire resistance requirements for walls',edition='Test edition')
    monkeypatch.setattr(engine,'run_construction_agent',lambda _: 'Assessment: C2D2 fire resistance reference found. Project verification remains required.')
    monkeypatch.setattr(template_store,'DB_PATH',report_store.DB_PATH.with_name('templates.db'))
    token = user_store.create_session(alice['id'])
    source = Path('streamlit_app.py').read_text().replace('auth_cookies = initialize_cookie_manager()',f'auth_cookies = {{"session_token": {token!r}}}')
    app = AppTest.from_string(source,default_timeout=30)
    app.session_state['active_project_id'] = a['id']
    app.session_state['active_section'] = 'Copilot'
    app.run()
    assert not app.exception
    app.chat_input[0].set_value('NCC fire resistance requirements').run()
    assert not app.exception
    stored = report_store.list_reports(alice['id'],a['id'])
    assert len(stored) == 1 and stored[0]['sources'][0]['metadata']['clause'] == 'C2D2'
    assert app.session_state['copilot_history'][0]['response'] == stored[0]['result']
    app.selectbox(key='nav_selected').select('Reports').run()
    assert not app.exception
    assert len(app.get('download_button')) == 1
    assert any('Assessment: C2D2' in item.value for item in app.markdown)
    # Exercise real PDF generation and text extraction, not a mocked download.
    import ast
    import time
    from io import BytesIO
    from xml.sax.saxutils import escape
    from PyPDF2 import PdfReader
    tree = ast.parse(Path('streamlit_app.py').read_text())
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_pdf_report')
    ns = {'BytesIO':BytesIO,'escape':escape,'time':time}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'pdf-acceptance','exec'),ns)
    pdf = ns['build_pdf_report']('Copilot',stored[0]['result'])
    # PyPDF2's legacy CJK cmap decoder leaves UTF-16 NULs in Latin text.
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages).replace('\x00','')
    assert 'C2D2' in text and 'Sources' in text and 'ncc.txt' in text


def test_large_ncc_bundle_is_reviewed_once_and_saved_without_dropping_evidence(system,monkeypatch):
    owner,other,project,_,_=system
    chunks=[{'text':('Linked NCC provision %s. '%i)*85,'metadata':{'source':f'NCC 2025 Housing Provisions.pdf, p. {i+1}','page':i+1,'clause':f'9.2.{i+1}','code':'NCC 2025','reference_kind':'server_local_ncc'}} for i in range(24)]
    monkeypatch.setattr(engine,'retrieve_multi',lambda *args,**kwargs:chunks)
    def redundant(*args):raise AssertionError('Regulatory evidence was sent through redundant planning/routing')
    monkeypatch.setattr(engine,'plan_tasks',redundant);monkeypatch.setattr(engine,'route_task',redundant)
    calls=[]
    def review(prompt):
        calls.append(prompt)
        assert all(chunk['text'] in prompt for chunk in chunks)
        return 'Synthetic review complete. Construction evidence remains missing; no compliance determination.'
    monkeypatch.setattr(engine,'run_construction_agent',review)
    import analysis_service
    saved=analysis_service.analyze(owner['id'],project['id'],'NCC 2025 fire wall risks and strategy','large-ncc-one-pass')
    assert len(calls)==1 and len(saved['sources'])==24
    assert report_store.get_report(owner['id'],project['id'],saved['id'])['sources']==saved['sources']
    with pytest.raises(PermissionError):
        report_store.get_report(other['id'],project['id'],saved['id'])
