"""Interactive navigation never runs AI; project switches clear drafts and private search state."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from test_document_management import system,legacy_system
import user_store,project_store,template_store

def signed_app(system,monkeypatch):
    owner,_,project,other,_=system
    monkeypatch.setattr(template_store,'DB_PATH',Path(project_store.DB_PATH).with_name('templates.db'))
    session=user_store.create_session(owner['id'])
    source=Path('streamlit_app.py').read_text().replace('auth_cookies = initialize_cookie_manager()',f'auth_cookies = {{"session_token":{session!r}}}')
    app=AppTest.from_string(source,default_timeout=30)
    app.session_state['active_project_id']=project['id'];app.run()
    return app,owner,project,other

def test_workflow_drafts_and_project_switches_never_call_ai(system,monkeypatch):
    import core.engine
    calls=[]
    def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('Navigation invoked AI')
    monkeypatch.setattr(core.engine,'run_engine',forbidden)
    app,owner,project,other=signed_app(system,monkeypatch)
    next(b for b in app.button if b.label=='Explore Workspaces').click().run()
    assert app.session_state['workspace_catalog_open']
    app.selectbox(key='workflow_Construction Workspace').select('Contracts').run()
    app.button(key='workflow_open_Construction Workspace').click().run()
    assert not app.exception and app.session_state['active_section']=='Copilot'
    assert 'contracts' in app.text_area(key='copilot_draft').value
    app.selectbox(key='workspace_project_'+str(owner['id'])).select(other['id']).run()
    assert not app.exception and app.session_state['active_project_id']==other['id']
    assert not any(field.key=='copilot_draft' for field in app.text_area) and not app.session_state['copilot_history']
    assert not calls

def test_quick_navigation_and_report_filter_keep_project_scope(system,monkeypatch):
    import report_store
    app,owner,project,other=signed_app(system,monkeypatch)
    report_store.save_report(owner['id'],project['id'],{'query':'ALPHA owned report','result':'ALPHA EVIDENCE'})
    report_store.save_report(owner['id'],other['id'],{'query':'BRAVO other project','result':'BRAVO EVIDENCE'})
    app.button(key='quick_nav_Reports').click().run()
    assert not app.exception and any('ALPHA EVIDENCE' in item.value for item in app.markdown)
    app.text_input(key='report_search').set_value('BRAVO').run()
    assert any('No matching reports' in item.value for item in app.info)
    assert not any('BRAVO EVIDENCE' in item.value for item in app.markdown)
    app.selectbox(key='workspace_project_'+str(owner['id'])).select(other['id']).run()
    assert not app.exception and app.text_input(key='report_search').value==''
    assert any('BRAVO EVIDENCE' in item.value for item in app.markdown)

def test_bim_findings_filter_has_recoverable_empty_state(system,monkeypatch):
    from core import bim_checks
    from test_bim_checks import model_bytes
    owner,_,project,_,_=system
    bim_checks.import_model(owner['id'],project['id'],'model.ifc',model_bytes())
    app,_,_,_=signed_app(system,monkeypatch)
    app.button(key='quick_nav_BIM').click().run()
    assert not app.exception and not app.error
    field=next(item for item in app.text_input if item.label=='Find an element')
    field.set_value('no-such-element').run()
    assert any('No findings match' in item.value for item in app.info)
    next(item for item in app.text_input if item.label=='Find an element').set_value('').run()
    assert not app.exception and not app.error
    assert any('Download issues CSV' in item.value for item in app.markdown)

from test_streamlit_ui import app as guest_app

def test_guest_settings_is_an_explicit_sign_in_gate(guest_app):
    guest_app.button(key='quick_nav_Settings').click().run()
    assert not guest_app.exception and not guest_app.error
    assert any('Sign in to manage your account' in item.value for item in guest_app.info)
    assert not any(field.label=='NCC server path' for field in guest_app.text_input)
