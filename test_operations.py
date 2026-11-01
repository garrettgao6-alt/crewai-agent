import importlib.util,json,sqlite3,tarfile,hashlib,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from deploy import operations as ops

@pytest.fixture
def system(tmp_path,monkeypatch):
    monkeypatch.setattr(ops,'STATE',tmp_path/'state');ops.STATE.mkdir()
    return tmp_path

def test_alert_threshold_dedup_recovery_and_redaction(system):
    sent=[];send=lambda *args:sent.append(args)
    for now in (1000,1300):ops.alert_cycle({'ui':True},config={},now=now,sender=send)
    assert not sent
    ops.alert_cycle({'ui':True},config={},now=1600,sender=send)
    ops.alert_cycle({'ui':True},config={},now=1900,sender=send)
    assert len(sent)==1 and 'ALERT: ui' in sent[0][0]
    ops.alert_cycle({'ui':False},config={},now=2200,sender=send)
    ops.alert_cycle({'ui':False},config={},now=2500,sender=send)
    assert len(sent)==2 and 'RECOVERED: ui' in sent[1][0]
    assert 'customer documents' in sent[0][1] and 'password_hash' not in sent[0][1]

def test_failed_delivery_remains_spent_and_waits(system):
    attempts=[]
    def fail(*args):attempts.append(1);raise RuntimeError('SECRET_SENTINEL')
    for now in (1000,1300):ops.alert_cycle({'api':True},config={},now=now,sender=fail)
    with pytest.raises(RuntimeError,match='^Alert delivery failed$'):ops.alert_cycle({'api':True},config={},now=1600,sender=fail)
    ops.alert_cycle({'api':True},config={},now=1900,sender=fail)
    assert len(attempts)==1 and ops.read_json(ops.STATE/'alerts.json')['sent']==1
    assert 'SECRET_SENTINEL' not in (ops.STATE/'alerts.json').read_text()

def test_alert_cap_and_immediate_backup_failure(system):
    sent=[]
    for i in range(12):
        ops.alert_cycle({'backup_job':True},config={},now=100000+i*2,sender=lambda *a:sent.append(a))
        ops.alert_cycle({'backup_job':False},config={},now=100001+i*2,sender=lambda *a:sent.append(a))
    assert len(sent)==8

def test_parallel_alerts_cannot_send_duplicates(system):
    sent=[]
    for _ in range(2):ops.alert_cycle({'mail':True},config={},now=1000,sender=lambda *a:None)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda _:ops.alert_cycle({'mail':True},config={},now=1300,sender=lambda *a:sent.append(a)),range(8)))
    assert len(sent)==1

def test_healthy_probe_resets_consecutive_threshold(system):
    sent=[]
    for i,failed in enumerate([True,True,False,True,True]):ops.alert_cycle({'public':failed},config={},now=1000+i*300,sender=lambda *a:sent.append(a))
    assert not sent

def test_arbitrary_alert_content_is_rejected(system):
    with pytest.raises(ValueError):ops.alert_cycle({'secret text':True},config={},now=1000,sender=lambda *a:None)

def config(system):
    key=system/'recovery-key';key.write_text('test-key');key.chmod(0o600)
    return {'RESTIC_REPOSITORY':'s3:https://sfo3.digitaloceanspaces.com/private-bucket/gao','RESTIC_PASSWORD_FILE':str(key),'AWS_ACCESS_KEY_ID':'test','AWS_SECRET_ACCESS_KEY':'test-secret'}

def test_backup_requires_remote_encrypted_and_private_key(system):
    cfg=config(system);assert ops.restic_env(cfg)['RESTIC_PASSWORD_FILE']==cfg['RESTIC_PASSWORD_FILE']
    for repo in ('/tmp/fake','s3:http://unsafe/bucket','s3:https://localhost/bucket'):
        with pytest.raises(RuntimeError):ops.restic_env({**cfg,'RESTIC_REPOSITORY':repo})
    Path(cfg['RESTIC_PASSWORD_FILE']).chmod(0o644)
    with pytest.raises(RuntimeError):ops.restic_env(cfg)

def archive(system,wrong_owner=False):
    app=system/'source'/'crewai-agent';app.mkdir(parents=True);(app/'streamlit_app.py').write_text('print("ok")')
    with sqlite3.connect(app/'users.db') as c:c.execute('CREATE TABLE users(id INTEGER)');c.execute('INSERT INTO users VALUES(1)')
    with sqlite3.connect(app/'projects.db') as c:c.execute('CREATE TABLE projects(id INTEGER,user_id INTEGER)');c.execute('INSERT INTO projects VALUES(7,1)')
    with sqlite3.connect(app/'reports.db') as c:c.execute('CREATE TABLE reports(user_id INTEGER,project_id INTEGER)');c.execute('INSERT INTO reports VALUES(?,7)',(2 if wrong_owner else 1,))
    directory=system/'backup';directory.mkdir();p=directory/'application-and-data.tar.gz'
    with tarfile.open(p,'w:gz') as tar:tar.add(app,arcname='crewai-agent')
    (directory/'manifest.json').write_text(json.dumps({'sha256':ops.digest(p)}));return directory

def test_restore_checks_account_project_report_ownership(system):
    directory=archive(system,wrong_owner=True)
    with pytest.raises(RuntimeError,match='ownership'):ops.verify_archive(directory/'application-and-data.tar.gz')

def test_offsite_only_marked_verified_after_download_and_restore(system,monkeypatch):
    directory=archive(system);commands=[]
    def restic(args,env):
        commands.append(args)
        if args[0]=='backup':return json.dumps({'snapshot_id':'a'*64})
        if args[0]=='restore':
            dest=Path(args[args.index('--target')+1])/directory.relative_to('/')
            dest.mkdir(parents=True);shutil.copytree(directory,dest,dirs_exist_ok=True)
        return ''
    monkeypatch.setattr(ops,'restic',restic)
    receipt=ops.offsite_copy(directory,config(system))
    assert receipt['remote_restore_verified'] and receipt['ownership_verified']
    assert [c[0] for c in commands]==['backup','check','restore']

def test_failed_remote_restore_does_not_publish_success(system,monkeypatch):
    directory=archive(system)
    def restic(args,env):
        if args[0]=='backup':return json.dumps({'snapshot_id':'a'*64})
        if args[0]=='restore':raise RuntimeError('Unavailable')
        return ''
    monkeypatch.setattr(ops,'restic',restic)
    with pytest.raises(RuntimeError):ops.offsite_copy(directory,config(system))
    assert not (ops.STATE/'offsite-last.json').exists()

def test_external_watchdog_checks_heartbeat(system,monkeypatch):
    monkeypatch.setattr(ops,'health',lambda:{'api':False,'backup':False})
    monkeypatch.setattr(ops.time,'time',lambda:10000)
    assert not ops.watchdog()
    ops.atomic_json(ops.STATE/'monitor-last.json',{'checked_at':9999})
    assert ops.watchdog()
    ops.atomic_json(ops.STATE/'monitor-last.json',{'checked_at':9000})
    assert not ops.watchdog()

def test_old_or_other_repository_receipt_is_not_healthy(system,monkeypatch):
    class Response:status_code=200
    monkeypatch.setattr(ops,'APP',system/'app');ops.APP.mkdir()
    monkeypatch.setattr(ops.requests,'get',lambda *a,**k:Response())
    monkeypatch.setattr(ops,'configuration',lambda:{'RESTIC_REPOSITORY':'s3:https://example.test/bucket'})
    monkeypatch.setattr(ops.time,'time',lambda:10000)
    receipt={'verified_at':9999,'remote_restore_verified':True,'repository_fingerprint':'wrong'}
    ops.atomic_json(ops.STATE/'offsite-last.json',receipt);assert ops.health()['backup']
    receipt['repository_fingerprint']=hashlib.sha256(b's3:https://example.test/bucket').hexdigest()
    ops.atomic_json(ops.STATE/'offsite-last.json',receipt);assert not ops.health()['backup']
    receipt['verified_at']=100000;ops.atomic_json(ops.STATE/'offsite-last.json',receipt);assert ops.health()['backup']
