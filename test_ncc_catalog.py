from io import BytesIO
from pathlib import Path
import pytest
from reportlab.pdfgen.canvas import Canvas
from core import ncc_catalog as catalog, ncc_library as library


def pdf(kind, text='Fire separation external wall requirements H1D1'):
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(40, 750, '2025 ' + kind)
    canvas.showPage()
    canvas.drawString(40, 750, 'Fire safety')
    canvas.drawString(40, 720, text)
    canvas.showPage()
    canvas.drawString(40, 750, 'Victoria')
    canvas.drawString(40, 720, 'VIC H1D1 Fire separation Victorian external wall requirements')
    canvas.showPage()
    canvas.drawString(40, 750, 'New South Wales')
    canvas.drawString(40, 720, 'NSW H1D1 Fire separation external wall NSW_ONLY_MARKER')
    canvas.save()
    return buffer.getvalue()


@pytest.fixture
def root(tmp_path, monkeypatch):
    root = tmp_path / 'ncc'
    root.mkdir()
    monkeypatch.setenv('NCC_DOCUMENT_ROOT', str(root))
    monkeypatch.setattr(library, 'DB_PATH', tmp_path / 'library.db')
    return root


def import_all(owner='alice'):
    return catalog.import_pdfs(owner, [(f'NCC 2025 {kind}.pdf', pdf(kind), '2025', kind) for kind in catalog.KINDS])


def test_private_import_and_context_matching(root):
    result = import_all()
    assert result['files'] == 3
    assert library.has_catalog('alice')
    hits = library.search_local_references('alice', 'NCC fire external walls', context={'building_class':'1a','jurisdiction':'VIC'})
    assert hits and all(hit['metadata']['code'] in {'NCC 2025 Volume Two','NCC 2025 Housing Provisions'} for hit in hits)
    assert all(hit['metadata']['source_jurisdiction'] in {'','VIC'} for hit in hits)
    assert all('NSW_ONLY_MARKER' not in hit['text'] for hit in hits)
    hits = library.search_local_references('alice', 'NCC fire walls', context={'building_class':'2','jurisdiction':'VIC'})
    assert hits and all(hit['metadata']['code'] == 'NCC 2025 Volume One' for hit in hits)
    assert all(hit['metadata']['page'] >= 2 and hit['metadata']['document_sha256'] for hit in hits)


def test_no_wrong_edition_or_silent_classification(root):
    import_all()
    for query, context in [('NCC fire',{}), ('NCC 2022 class 1a fire',{}), ('NCC class 2 Volume Two fire',{}), ('NCC class 2 compliance fire',{})]:
        with pytest.raises(catalog.NCCContextRequired):
            library.search_local_references('alice', query, context=context)
    assert library.search_local_references('alice','NCC 2025 Volume One fire')


def test_other_account_cannot_configure_private_library(root):
    result = import_all()
    assert library.search_local_references('bob','NCC fire') == []
    with pytest.raises(library.NCCReferenceError):
        library.save_reference('bob', result['path'], 'NCC 2025')
    with pytest.raises(library.NCCReferenceError):
        library.save_reference('bob', str(Path(result['path']) / 'NCC 2025 Volume One.pdf'), 'NCC 2025')


def test_failed_batch_keeps_previous_collection(root):
    import_all()
    before = library.load_reference('alice')
    with pytest.raises(ValueError):
        catalog.import_pdfs('alice',[('wrong.pdf',pdf('Volume One'),'2022','Volume One')])
    assert library.load_reference('alice') == before
    with pytest.raises(ValueError):
        catalog.import_pdfs('alice',[('../escape.pdf',pdf('Volume One'),'2025','Volume One')])
    assert library.load_reference('alice') == before


def test_changed_pdf_blocks_stale_index(root):
    result = import_all()
    (Path(result['path']) / 'NCC 2025 Volume One.pdf').write_bytes(b'changed')
    with pytest.raises(library.NCCReferenceError, match='changed'):
        library.search_local_references('alice','NCC class 2 fire')


def test_project_context_is_owner_and_project_scoped(root, tmp_path, monkeypatch):
    import project_store
    monkeypatch.setattr(project_store,'DB_PATH',tmp_path / 'projects.db')
    project_store.initialize_project_store()
    a = project_store.create_project(1, 'A')
    b = project_store.create_project(1, 'B')
    library.save_project_context(1,a['id'],'2025','1a','VIC')
    assert library.load_project_context(1,a['id'])['building_class'] == '1a'
    assert library.load_project_context(1,b['id']) == {}
    with pytest.raises(PermissionError):
        library.load_project_context(2,a['id'])


def test_indexed_library_does_not_mix_old_project_code_or_spend_reranking_tokens(root, monkeypatch):
    from core import retriever
    import_all()
    def forbidden(*args, **kwargs):
        raise AssertionError('Managed library must not search old code vectors or call AI reranking')
    monkeypatch.setattr(retriever, 'search_ncc_chunks', forbidden)
    monkeypatch.setattr(retriever, 'rerank', forbidden)
    monkeypatch.setattr(retriever, 'retrieve', lambda *a, **kw: [
        {'text':'OLD_2022_CODE', 'metadata':{'type':'ncc','reference_kind':'project_ncc'}},
        {'text':'PROJECT_EVIDENCE', 'metadata':{'type':'construction','source':'drawing.txt'}}])
    hits = retriever.retrieve_multi('owned_project_scope', 'NCC fire external wall', reference_user_id='alice', reference_context={'building_class':'2','jurisdiction':'VIC'})
    assert hits and all('OLD_2022_CODE' not in hit['text'] for hit in hits)
    assert any(hit['text'] == 'PROJECT_EVIDENCE' for hit in hits)


def test_missing_project_context_asks_before_model_execution(root, tmp_path, monkeypatch):
    import project_store
    from core import engine
    from types import SimpleNamespace
    monkeypatch.setattr(project_store, 'DB_PATH', tmp_path / 'projects.db')
    project_store.initialize_project_store()
    project = project_store.create_project(1, 'Missing classification')
    import_all(1)
    monkeypatch.setattr(engine, 'memory', SimpleNamespace(get=lambda *a: []))
    monkeypatch.setattr(engine, 'agent_executor', lambda *a: pytest.fail('No model call before context clarification'))
    result = engine.run_engine('1', 'NCC fire separation', project_id=project['id'], return_details=True)
    assert result['status'] == 'context_required'
    assert 'building class' in result['result']
    assert result['sources'] == []


def test_full_clause_continuation_and_housing_cross_reference(root):
    def make(kind, pages):
        buf=BytesIO(); canvas=Canvas(buf)
        for lines in [['2025 '+kind]] + pages:
            for index,line in enumerate(lines): canvas.drawString(40,750-index*25,line)
            canvas.showPage()
        canvas.save(); return buf.getvalue()
    two=make('Volume Two', [['H3D3 Fire separation of external walls','Compliance with Part 9.2 of the ABCB Housing Provisions.'],['H3D4 Other provision','An unrelated requirement.']])
    housing=make('Housing Provisions', [['9.2.1 External walls','CONTINUATION_START fire wall construction'],['CONTINUATION_END complete fire wall requirement'],['9.2.2 Measurement of distances','Distance measurement requirement.']])
    result=catalog.import_pdfs('alice',[('two.pdf',two,'2025','Volume Two'),('housing.pdf',housing,'2025','Housing Provisions')])
    hits=library.search_local_references('alice','NCC fire separation external walls',context={'building_class':'1a','jurisdiction':'VIC'})
    assert any('CONTINUATION_START' in hit['text'] and 'CONTINUATION_END' in hit['text'] for hit in hits)
    assert any(hit['metadata']['selection_reason']=='cross-reference' for hit in hits)
    with __import__('sqlite3').connect(Path(result['path'])/'.ncc-index.sqlite3') as connection:
        assert connection.execute('SELECT count(*) FROM pages').fetchone()[0] == 7


def test_protected_operator_default_is_available_without_cross_account_private_access(root, monkeypatch):
    directory=root/'approved'/'ncc2025';directory.mkdir(parents=True)
    records=[]
    for kind in catalog.KINDS:
        name=kind+'.pdf';(directory/name).write_bytes(pdf(kind));records.append((name,'2025',kind))
    catalog.create_catalog(directory,records,'operator_public_ncc')
    monkeypatch.setenv('NCC_DEFAULT_REFERENCE','approved/ncc2025')
    assert library.load_reference('alice')['operator_default']
    assert library.search_local_references('alice','NCC fire walls',context={'building_class':'2','jurisdiction':'VIC'})
    assert library.search_local_references('bob','NCC fire walls',context={'building_class':'1a','jurisdiction':'VIC'})
    library.clear_reference('alice')
    assert library.load_reference('alice') is None
    assert library.load_reference('bob')['operator_default']
