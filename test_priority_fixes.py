from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path
from threading import Event
import json,sqlite3,tarfile
import pytest
import user_store as u,subscription_store as subscriptions,project_store as projects,report_store as reports
import account_recovery as recovery,analysis_service as service
from core import private_ai,engine,ncc_library

@pytest.fixture
def system(tmp_path,monkeypatch):
    for module,name in ((u,'users'),(subscriptions,'users'),(projects,'projects'),(reports,'reports'),(private_ai,'private_ai'),(ncc_library,'ncc')):
        monkeypatch.setattr(module,'DB_PATH',tmp_path/(name+'.db'))
    monkeypatch.setenv('MAX_USERS','0');monkeypatch.setenv('ADMIN_USERNAME','');monkeypatch.setenv('ADMIN_PASSWORD','')
    monkeypatch.setenv('MAIL_PROVIDER','smtp');monkeypatch.setenv('SMTP_HOST','test.invalid');monkeypatch.setenv('SMTP_FROM','test@example.test')
    monkeypatch.delenv('NCC_DEFAULT_REFERENCE',raising=False)
    u.initialize_user_store();projects.initialize_project_store()
    owner=u.create_user('Owner','owner@example.test','Safe-test-password')
    other=u.create_user('Other','other@example.test','Other-test-password')
    project=projects.create_project(owner['id'],'Existing project')
    return owner,other,project

def test_unknown_email_flood_does_not_consume_delivery_capacity(system,monkeypatch):
    owner,_,_=system;sent=[]
    monkeypatch.setattr(recovery,'_send',lambda *a,**k:sent.append(a))
    for i in range(100):recovery.request_code(f'unknown{i}@example.test',source='attacker')
    with u.get_connection() as c:assert c.execute('SELECT count(*) FROM recovery_sends').fetchone()[0]==0
    recovery.request_code(owner['email'],source='legitimate')
    assert len(sent)==1

def test_activation_is_required_only_for_new_public_accounts(system,monkeypatch):
    owner,_,project=system;sent=[]
    monkeypatch.setattr(recovery,'_send',lambda *a,**k:sent.append(a[1]))
    new=u.create_user('NewMember','new@example.test','New-test-password',require_verification=True)
    assert not new['is_active'] and u.authenticate_user(new['email'],'New-test-password') is None
    with pytest.raises(PermissionError):u.create_session(new['id'])
    recovery.request_code(new['email'],purpose='activate',source='new')
    with pytest.raises(ValueError):recovery.reset_password(new['email'],sent[0],'Other-password')
    recovery.activate_account(new['email'],sent[0])
    assert u.authenticate_user(new['email'],'New-test-password')['id']==new['id']
    assert projects.require_project_access(owner['id'],project['id'])['user_id']==owner['id']
    assert u.authenticate_user(owner['email'],'Safe-test-password')
    with pytest.raises(ValueError):recovery.activate_account(new['email'],sent[0])

def test_default_enrollment_allows_fourth_account(system,monkeypatch):
    monkeypatch.delenv('MAX_USERS')
    assert u.get_max_users()==0
    u.create_user('Third','third@example.test','Safe-test-password')
    assert u.create_user('Fourth','fourth@example.test','Safe-test-password')['id']

def test_login_lockout_persists_across_sources_and_expires(system,monkeypatch):
    import account_security
    owner,other,_=system
    for i in range(5):assert u.authenticate_user(owner['email'],'wrong',source=str(i)) is None
    assert u.authenticate_user(owner['email'],'Safe-test-password',source='another') is None
    assert u.authenticate_user(other['email'],'Other-test-password',source='legit')
    original=account_security.time.time
    now=original();monkeypatch.setattr(account_security.time,'time',lambda:now+901)
    assert u.authenticate_user(owner['email'],'Safe-test-password',source='legit')

def test_idempotent_analysis_charges_and_saves_once(system,monkeypatch):
    owner,other,project=system;calls=[]
    def model(*a,**k):calls.append(1);return {'result':'Grounded test result','sources':[],'status':'draft','version':'test'}
    monkeypatch.setattr(engine,'run_engine',model)
    a=service.analyze(owner['id'],project['id'],'Review project','same-key-123')
    b=service.analyze(owner['id'],project['id'],'Review project','same-key-123')
    assert a['id']==b['id'] and len(calls)==1
    assert subscriptions.get_usage(owner['id'])['current_request_count']==1
    assert len(reports.list_reports(owner['id'],project['id']))==1
    with pytest.raises(PermissionError):service.analyze(other['id'],project['id'],'Review project','same-key-123')
    with pytest.raises(ValueError):service.analyze(owner['id'],project['id'],'Different input','same-key-123')

def test_inflight_retry_cannot_duplicate_work(system,monkeypatch):
    owner,_,project=system;started=Event();release=Event();calls=[]
    def model(*a,**k):
        calls.append(1);started.set();assert release.wait(10)
        return {'result':'Result','sources':[],'status':'draft','version':'test'}
    monkeypatch.setattr(engine,'run_engine',model)
    with ThreadPoolExecutor(2) as pool:
        future=pool.submit(service.analyze,owner['id'],project['id'],'Review','concurrent-key')
        assert started.wait(10)
        try:
            with pytest.raises(service.AnalysisBusy):service.analyze(owner['id'],project['id'],'Review','concurrent-key')
        finally:release.set()
        future.result()
    assert len(calls)==1 and subscriptions.get_usage(owner['id'])['current_request_count']==1

def test_missing_context_does_not_call_model_or_charge(system,monkeypatch):
    owner,_,project=system
    def missing(*a,**k):raise ncc_library.__dict__.get('NCCContextRequired',__import__('core.ncc_catalog',fromlist=['NCCContextRequired']).NCCContextRequired)('Specify building class and state')
    monkeypatch.setattr(ncc_library,'search_local_references',missing)
    monkeypatch.setattr(engine,'run_engine',lambda *a,**k:pytest.fail('Model path invoked'))
    result=service.analyze(owner['id'],project['id'],'NCC fire','context-key')
    assert result['status']=='context_required'
    assert subscriptions.get_usage(owner['id'])['current_request_count']==0
    assert not reports.list_reports(owner['id'],project['id'])

def test_budget_reservations_are_shared_and_provider_is_bounded(system,monkeypatch):
    owner,_,project=system;calls=[];constructor=[]
    def create(**kwargs):calls.append(kwargs);return SimpleNamespace(usage=SimpleNamespace(total_tokens=10),output_text='Grounded result')
    def factory(**kwargs):constructor.append(kwargs);return SimpleNamespace(responses=SimpleNamespace(create=create),embeddings=SimpleNamespace(create=create))
    monkeypatch.setenv('PRIVATE_AI_GLOBAL_DAILY_TOKENS','5000')
    with private_ai.scope(owner['id'],project['id']):
        client=private_ai.client(factory)
        client.responses.create(model='test',input='Review',max_output_tokens=9999,store=True)
        with pytest.raises(private_ai.BudgetError):client.responses.create(model='test',input='Review')
    assert len(calls)==1 and calls[0]['store'] is False and calls[0]['max_output_tokens']==2000
    assert constructor==[{'max_retries':0,'timeout':45}]
    with pytest.raises(private_ai.BudgetError):private_ai.client(factory)

def test_concurrent_budget_reservation_is_atomic(system,monkeypatch):
    monkeypatch.setenv('PRIVATE_AI_GLOBAL_DAILY_TOKENS','5000')
    def claim(i):
        with private_ai.scope(i,i):
            try:private_ai.reserve(4000);return True
            except private_ai.BudgetError:return False
    with ThreadPoolExecutor(2) as pool:outcomes=list(pool.map(claim,[1,2]))
    assert sum(outcomes)==1

def test_failed_provider_reservation_is_not_refunded(system):
    owner,_,project=system
    def fail(**kwargs):raise RuntimeError('Provider unavailable')
    def factory(**kwargs):return SimpleNamespace(responses=SimpleNamespace(create=fail),embeddings=SimpleNamespace(create=fail))
    with private_ai.scope(owner['id'],project['id']):
        with pytest.raises(RuntimeError):private_ai.client(factory).responses.create(input='Test',model='test')
    with sqlite3.connect(private_ai.DB_PATH) as c:
        assert c.execute('SELECT reserved,status FROM ai_calls').fetchone()[1]=='failed'
        assert c.execute("SELECT tokens FROM ai_budget WHERE scope='global' ORDER BY length(period) DESC").fetchone()[0]>0

def test_online_backup_restores_live_sqlite_and_ncc(tmp_path):
    from deploy.online_backup import backup
    app=tmp_path/'app';app.mkdir();destination=tmp_path/'backup';destination.mkdir()
    (app/'streamlit_app.py').write_text('# fixture')
    ncc=tmp_path/'ncc';ncc.mkdir();(ncc/'reference.txt').write_text('Original NCC fixture')
    (app/'.env').write_text('NCC_DOCUMENT_ROOT='+str(ncc)+'\n')
    c=sqlite3.connect(app/'live.db');c.execute('PRAGMA journal_mode=WAL');c.execute('CREATE TABLE facts(value TEXT)');c.execute("INSERT INTO facts VALUES('preserved')");c.commit()
    try:backup(app,destination)
    finally:c.close()
    manifest=json.loads((destination/'manifest.json').read_text())
    assert manifest['online'] and manifest['restore_integrity_checked']
    with tarfile.open(destination/'application-and-data.tar.gz') as tar:
        assert tar.extractfile('crewai-agent/streamlit_app.py').read()==b'# fixture'
        assert any(member.name.endswith('reference.txt') for member in tar.getmembers())
        restored=tmp_path/'restored.db';restored.write_bytes(tar.extractfile('crewai-agent/live.db').read())
        with sqlite3.connect(restored) as checked:assert checked.execute('SELECT value FROM facts').fetchone()[0]=='preserved'

def test_failed_job_never_saves_a_success_report_or_runs_twice(system,monkeypatch):
    owner,_,project=system;calls=[]
    def fail(*a,**k):calls.append(1);raise RuntimeError('provider failed')
    monkeypatch.setattr(engine,'run_engine',fail)
    with pytest.raises(RuntimeError):service.analyze(owner['id'],project['id'],'Review','failed-key')
    with pytest.raises(service.AnalysisFailed):service.analyze(owner['id'],project['id'],'Review','failed-key')
    assert len(calls)==1 and not reports.list_reports(owner['id'],project['id'])

def test_legacy_account_migration_preserves_id_hash_and_session(tmp_path,monkeypatch):
    path=tmp_path/'legacy.db';monkeypatch.setattr(u,'DB_PATH',path)
    monkeypatch.setenv('ADMIN_USERNAME','')
    password_hash=u.hash_password('Original-password')
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,email TEXT,password_hash TEXT)')
        c.execute('INSERT INTO users VALUES(42,?,?,?)',('legacy','legacy@example.test',password_hash))
        c.execute('CREATE TABLE auth_sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires_at TEXT NOT NULL)')
        import hashlib
        c.execute('INSERT INTO auth_sessions VALUES(?,?,?)',(hashlib.sha256(b'existing-session').hexdigest(),42,'2999-01-01T00:00:00+00:00'))
    u.initialize_user_store()
    assert u.resolve_session('existing-session')['id']==42
    assert u.authenticate_user('legacy','Original-password')['email_verified']==1
    with u.get_connection() as c:assert c.execute('SELECT password_hash FROM users WHERE id=42').fetchone()[0]==password_hash

def test_api_retry_returns_same_report_and_one_quota_charge(system,monkeypatch):
    from fastapi.testclient import TestClient
    import api
    owner,_,project=system;token=u.create_session(owner['id']);calls=[]
    def model(*a,**k):calls.append(1);return {'result':'Evidence-based result','sources':[],'status':'draft','version':'test'}
    monkeypatch.setattr(engine,'run_engine',model)
    client=TestClient(api.app);payload={'query':'Review project','project_id':project['id'],'request_id':'http-retry-key'}
    headers={'Authorization':'Bearer '+token}
    first=client.post('/analyze',json=payload,headers=headers);second=client.post('/analyze',json=payload,headers=headers)
    assert first.status_code==second.status_code==200
    assert first.json()['id']==second.json()['id'] and len(calls)==1
    assert subscriptions.get_usage(owner['id'])['current_request_count']==1
