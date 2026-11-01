"""Real server acceptance. No production customer documents are read by this check."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import types
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
import requests
import user_store, project_store, report_store
from core.ingestion import ingest_document
from core import vector_store, ncc_library

run_id=uuid4().hex[:10]
users=[]
scopes=[]
tokens=[]
checks={}
managed_scopes=set()
old_limit=os.environ.get('MAX_USERS')
os.environ['MAX_USERS']='0'  # Only this verification process, never .env/server settings.
try:
    user_store.initialize_user_store()
    project_store.initialize_project_store()
    for label in ('a','b'):
        password=secrets.token_urlsafe(32)
        username=f'releasecheck_{run_id}_{label}'
        user=user_store.create_user(username,f'{username}@example.test',password)
        users.append((user,password))
        ncc_library.clear_reference(user["id"])  # Canary uses its own synthetic project references.
        assert user_store.authenticate_user(username,password)['id']==user['id']
        assert user_store.authenticate_user(username,'incorrect-password') is None
    checks['real_password_login']=True
    alice,bob=users[0][0],users[1][0]
    a=project_store.create_project(alice['id'],f'Acceptance {run_id} A')
    b=project_store.create_project(alice['id'],f'Acceptance {run_id} B')
    c=project_store.create_project(bob['id'],f'Acceptance {run_id} C')
    scopes=[project_store.document_scope(user['id'],p['id']) for user,p in ((alice,a),(alice,b),(bob,c))]
    marker=f'GAO_RELEASE_MARKER_{run_id.upper()}'
    fixture=f'C2D2 Acceptance fixture only, not an NCC publication. The acceptance marker is {marker}. Do not issue a compliance conclusion.'
    assert ingest_document(alice['id'],a['id'],'acceptance-ncc.txt',fixture.encode(),edition='Synthetic acceptance fixture - not regulatory material')>0
    assert vector_store.search_ncc_chunks(scopes[0],'NCC acceptance marker')
    assert vector_store.search_ncc_chunks(scopes[1],'NCC acceptance marker')==[]
    checks['real_embeddings_and_project_scoped_retrieval']=True
    token=user_store.create_session(alice['id'])
    other=user_store.create_session(bob['id'])
    tokens.extend([token,other])
    base='http://127.0.0.1:8000'
    headers={'Authorization':f'Bearer {token}'}
    body={'query':'NCC reference retrieval acceptance test: return the acceptance marker verbatim from the provided reference. State that this is a synthetic test and do not issue a compliance conclusion.','project_id':a['id']}
    assert requests.post(base+'/analyze',json=body,timeout=20).status_code==401
    assert requests.post(base+'/analyze',json=body,headers={'Authorization':f'Bearer {other}'},timeout=20).status_code==404
    response=requests.post(base+'/analyze',json=body,headers=headers,timeout=240)
    assert response.status_code==200, f'Analyze status {response.status_code}'
    report=response.json()
    assert marker in report['result']
    assert report['sources'] and report['sources'][0]['metadata']['project_id']==a['id']
    checks['real_api_model_and_ncc_citation']=True
    url=f"{base}/projects/{a['id']}/reports/{report['id']}"
    loaded=requests.get(url,headers=headers,timeout=20)
    assert loaded.status_code==200 and loaded.json()['sources']==report['sources']
    assert requests.get(url,headers={'Authorization':f'Bearer {other}'},timeout=20).status_code==404
    assert requests.get(f"{base}/projects/{b['id']}/reports/{report['id']}",headers=headers,timeout=20).status_code==404
    assert report_store.get_report(alice['id'],a['id'],report['id'])['result']==report['result']
    checks['persistent_report_reload_and_access_control']=True
    # Drive the deployed login form and report page in a fresh Streamlit session.
    # Only the browser Cookie JS handshake is substituted; passwords, sessions,
    # ownership, production DBs, saved report and actual UI code are real.
    from streamlit.testing.v1 import AppTest
    class CookieJar(dict):
        def save(self): pass
    module=types.ModuleType('deployment_acceptance_state')
    module.cookie_jar=CookieJar()
    sys.modules[module.__name__]=module
    source=(ROOT/'streamlit_app.py').read_text().replace('auth_cookies = initialize_cookie_manager()','from deployment_acceptance_state import cookie_jar as auth_cookies')
    app=AppTest.from_string(source,default_timeout=90).run()
    assert not app.exception
    next(button for button in app.button if button.label=='Login / Sign Up').click().run()
    app.text_input(key='auth_sign_in_identifier').set_value(alice['username'])
    app.text_input(key='auth_sign_in_password').set_value(users[0][1])
    next(button for button in app.button if button.label=='Sign In').click().run()
    assert not app.exception and app.session_state['is_logged_in']
    app.session_state['active_project_id']=a['id']
    app.session_state['active_section']='Reports'
    app.run()
    assert not app.exception and any(marker in item.value for item in app.markdown)
    assert app.get('download_button')
    app.session_state['active_project_id']=b['id']
    app.run()
    assert not app.exception and app.session_state['history']==[]
    checks['deployed_login_form_report_page_and_project_switch']=True
    # Exercise the managed file path with real embeddings and the deployed UI.
    from core import document_store, bim_checks
    first=document_store.upload(alice['id'],a['id'],'acceptance-feature.txt',b'Synthetic managed evidence FIRST',kind='business')
    second=document_store.upload(alice['id'],a['id'],'acceptance-feature.txt',b'Synthetic managed evidence SECOND',kind='business')
    managed_scopes.add(scopes[0])
    assert document_store.original(alice['id'],a['id'],first['file_id'],first['id'])==b'Synthetic managed evidence FIRST'
    try:document_store.original(bob['id'],a['id'],first['file_id'],first['id'])
    except PermissionError:pass
    else:raise AssertionError('Cross-account original access was accepted')
    assert 'SECOND' in vector_store.search_chunks(scopes[0],'managed evidence')[0]['text']
    document_store.set_archived(alice['id'],a['id'],first['file_id'])
    assert vector_store.search_chunks(scopes[0],'managed evidence')==[]
    document_store.activate_version(alice['id'],a['id'],first['file_id'],first['id'])
    assert 'FIRST' in vector_store.search_chunks(scopes[0],'managed evidence')[0]['text']
    checks['managed_original_versions_archive_restore_and_isolation']=True
    import ifcopenshell
    model=ifcopenshell.file(schema='IFC4')
    unit=model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Prefix='MILLI',Name='METRE')
    model.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new(),Name='Synthetic IFC acceptance',UnitsInContext=model.create_entity('IfcUnitAssignment',Units=[unit]))
    model.create_entity('IfcDoor',GlobalId=ifcopenshell.guid.new(),Name='Acceptance door',OverallWidth=900.,OverallHeight=2100.)
    model_version,model_report=bim_checks.import_model(alice['id'],a['id'],'acceptance-model.ifc',model.to_string().encode())
    inspection=model_report['bim_analysis']
    assert inspection['element_count']==1 and abs(inspection['dimension_samples'][0]['OverallWidth_metres']-.9)<1e-9
    assert inspection['ai_tokens_used']==0 and inspection['issues']
    checks['real_ifc_parser_units_element_findings_and_saved_report']=True
    app.session_state['active_project_id']=a['id'];app.session_state['active_section']='Documents';app.run()
    assert not app.exception and any('Download original' in item.value for item in app.markdown)
    app.session_state['active_section']='BIM';app.run()
    assert not app.exception and any('Download issues CSV' in item.value for item in app.markdown)
    checks['deployed_document_and_bim_ui_private_download_links']=True
    from deploy.operations import verify_document_store
    verify_document_store(ROOT)
    import download_service
    for endpoint in (base,'https://www.gaointelligence.com'):
        ticket=download_service.issue(token,a['id'],'original',first['id'])
        downloaded=requests.get(endpoint+'/private-download/'+ticket,timeout=30)
        assert downloaded.status_code==200 and downloaded.content==b'Synthetic managed evidence FIRST'
        assert 'attachment' in downloaded.headers['Content-Disposition'] and downloaded.headers['Cache-Control']=='private, no-store'
        assert requests.get(endpoint+'/private-download/'+ticket,timeout=20).status_code==404
    revoked_ticket=download_service.issue(token,a['id'],'original',first['id'])
    checks['real_http_original_download_public_proxy_and_replay_denial']=True
    user_store.revoke_session(token)
    assert requests.get(url,headers=headers,timeout=20).status_code==401
    assert requests.get(base+'/private-download/'+revoked_ticket,timeout=20).status_code==404
    checks['session_revocation']=True
    result={'status':'passed','run_id':run_id,'checks':checks,'customer_documents_accessed':False,'live_model_called':True,'browser_cookie_js_verified':False,'synthetic_report_id':report['id']}
    Path('/root/gao-latest-acceptance.json').write_text(json.dumps(result,indent=2))
except Exception as exc:
    Path('/root/gao-latest-acceptance.json').write_text(json.dumps({'status':'failed','run_id':run_id,'checks_completed':checks,'error_type':type(exc).__name__},indent=2))
    raise
finally:
    for token in tokens: user_store.revoke_session(token)
    for scope in scopes:
        # Retain the small, explicitly synthetic managed versions and matching
        # vectors as acceptance evidence; their accounts/sessions are disabled.
        if scope not in managed_scopes:vector_store.clear_store(scope)
    with user_store.get_connection() as connection:
        user_store._ensure_sessions(connection)
        for user,_ in users:
            connection.execute('UPDATE users SET is_active=0 WHERE id=?',(user['id'],))
            connection.execute('DELETE FROM auth_sessions WHERE user_id=?',(user['id'],))
    if old_limit is None: os.environ.pop('MAX_USERS',None)
    else: os.environ['MAX_USERS']=old_limit
