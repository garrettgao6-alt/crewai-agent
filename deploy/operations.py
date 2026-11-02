"""Private backup verification and bounded operational alerts. No customer payloads in alerts."""
from __future__ import annotations
import argparse,base64,fcntl,hashlib,json,os,re,shutil,sqlite3,subprocess,sys,tarfile,tempfile,time
from email.message import EmailMessage
from pathlib import Path
import requests
from dotenv import dotenv_values

APP=Path('/root/crewai-agent')
CONFIG=Path('/etc/gaointelligence/operations.env')
STATE=Path('/var/lib/gaointelligence-ops')
ISSUES={
 'ui':'Web application health check failed.', 'api':'Analysis API health check failed.',
 'public':'Public HTTPS health check failed.', 'disk':'Server disk usage is at least 85%.',
 'backup':'A verified off-server backup is missing or older than 26 hours.',
 'mail':'Account verification email delivery failures were recorded.',
 'monitor':'Operational checks could not complete.', 'backup_job':'The scheduled off-server backup failed.',
 'acceptance_test':'Controlled operational alert acceptance test.'}

def configuration():
    if CONFIG.exists() and CONFIG.stat().st_mode&0o077:raise RuntimeError('Operations configuration must be private')
    result={**dotenv_values(APP/'.env'),**dotenv_values(CONFIG)}
    return {k:str(v) for k,v in result.items() if v is not None}

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,sort_keys=True));temp.chmod(0o600);os.replace(temp,path)

def read_json(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return {}

def digest(path):
    with Path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

def verify_archive(archive):
    """Restore into temporary storage; validate tar paths, SQLite and account ownership."""
    with tempfile.TemporaryDirectory(prefix='gao-restore-') as temp:
        root=Path(temp).resolve()
        with tarfile.open(archive,'r:gz') as tar:
            for member in tar.getmembers():
                if not (root/member.name).resolve().is_relative_to(root) or member.issym() or member.islnk():
                    raise RuntimeError('Unsafe archive')
            tar.extractall(root,filter='data')
        app=root/'crewai-agent'
        if not (app/'streamlit_app.py').is_file():raise RuntimeError('Missing application')
        for file in root.rglob('*'):
            if not file.is_file():continue
            with file.open('rb') as handle:header=handle.read(16)
            if header==b'SQLite format 3\x00':
                with sqlite3.connect(f'file:{file}?mode=ro',uri=True) as c:
                    if c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Database integrity failed')
        if (app/'users.db').exists() and (app/'projects.db').exists():
            with sqlite3.connect(app/'users.db') as c:users={r[0] for r in c.execute('SELECT id FROM users')}
            with sqlite3.connect(app/'projects.db') as c:projects=dict(c.execute('SELECT id,user_id FROM projects'))
            if any(owner not in users for owner in projects.values()):raise RuntimeError('Orphan project')
            if (app/'reports.db').exists():
                with sqlite3.connect(app/'reports.db') as c:
                    if c.execute("SELECT 1 FROM sqlite_master WHERE name='reports'").fetchone():
                        if any(projects.get(project)!=owner for owner,project in c.execute('SELECT user_id,project_id FROM reports')):raise RuntimeError('Report ownership mismatch')
        verify_document_store(app)

def verify_document_store(app):
    """Validate retained originals and their ownership inside a restored application."""
    app=Path(app);db=app/'documents.db'
    if not db.exists():return
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='document_files'").fetchone():return
        files={r['id']:dict(r) for r in c.execute('SELECT * FROM document_files')}
        versions={r['id']:dict(r) for r in c.execute('SELECT * FROM document_versions')}
    with sqlite3.connect(app/'projects.db') as c:projects=dict(c.execute('SELECT id,user_id FROM projects'))
    for file in files.values():
        if projects.get(file['project_id'])!=file['user_id']:raise RuntimeError('Document project ownership mismatch')
        if file['active_version']:
            version=versions.get(file['active_version'])
            if not version or version['file_id']!=file['id'] or version['status']!='ready':raise RuntimeError('Invalid active document version')
    for version in versions.values():
        file=files.get(version['file_id'])
        if not file or (version['user_id'],version['project_id'])!=(file['user_id'],file['project_id']):raise RuntimeError('Document version ownership mismatch')
        if not re.fullmatch('[a-f0-9]{32}',version['id']):raise RuntimeError('Invalid original file identifier')
        path=app/'project_documents'/f"u{version['user_id']}"/f"p{version['project_id']}"/(version['id']+'.bin')
        if path.exists():
            if path.is_symlink() or digest(path)!=version['sha']:raise RuntimeError('Original file integrity failed')
        elif version['status']=='ready':raise RuntimeError('A ready document original is missing')


def restic_env(config):
    repository=config.get('RESTIC_REPOSITORY','')
    # A local directory cannot masquerade as an off-server success.
    if not re.fullmatch(r's3:https://[A-Za-z0-9.-]+(?::443)?/[A-Za-z0-9._/-]+',repository):
        raise RuntimeError('Configure an HTTPS S3 backup repository')
    from urllib.parse import urlparse
    host=urlparse(repository[3:]).hostname or ''
    if host in ('localhost','127.0.0.1','0.0.0.0') or host.endswith('.local'):raise RuntimeError('Off-server repository required')
    key=Path(config.get('RESTIC_PASSWORD_FILE','/nonexistent'))
    if not key.is_file() or key.stat().st_mode&0o077:raise RuntimeError('Protected recovery key required')
    if not all(config.get(k) for k in ('AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY')):raise RuntimeError('Backup credentials missing')
    env={**os.environ,**config,'RESTIC_PASSWORD_FILE':str(key),'RESTIC_CACHE_DIR':str(STATE/'restic-cache')}
    return env

def restic(args,env):
    result=subprocess.run(['restic',*args],env=env,capture_output=True,text=True,timeout=3600)
    if result.returncode:raise RuntimeError('Encrypted backup operation failed')
    return result.stdout

def offsite_copy(directory,config=None):
    config=configuration() if config is None else config;env=restic_env(config)
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    directory=Path(directory).resolve();archive=directory/'application-and-data.tar.gz';manifest=directory/'manifest.json'
    expected=read_json(manifest).get('sha256')
    if not expected or digest(archive)!=expected:raise RuntimeError('Local archive checksum failed')
    output=restic(['backup',str(archive),str(manifest),'--tag','gaointelligence','--json'],env)
    records=[json.loads(line) for line in output.splitlines() if line.strip().startswith('{')]
    snapshot=next((r['snapshot_id'] for r in reversed(records) if r.get('snapshot_id')),None)
    if not snapshot or not re.fullmatch('[a-f0-9]{8,64}',snapshot):raise RuntimeError('No verified snapshot identifier')
    restic(['check'],env)
    with tempfile.TemporaryDirectory(prefix='remote-restore-',dir=STATE) as temp:
        restic(['restore',snapshot,'--target',temp],env)
        restored=Path(temp)/archive.relative_to('/')
        restored_manifest=Path(temp)/manifest.relative_to('/')
        if read_json(restored_manifest).get('sha256')!=expected or digest(restored)!=expected:raise RuntimeError('Remote restore checksum failed')
        verify_archive(restored)
    receipt={'verified_at':int(time.time()),'snapshot':snapshot,'archive_sha256':expected,'remote_restore_verified':True,'ownership_verified':True,'repository_fingerprint':hashlib.sha256(config['RESTIC_REPOSITORY'].encode()).hexdigest()}
    atomic_json(STATE/'offsite-last.json',receipt)
    print('OFFSITE_ENCRYPTED_RESTORE_VERIFIED',snapshot,flush=True)
    return receipt

def send_mail(subject,body,config):
    sender=config.get('SMTP_FROM','');recipient=config.get('GAO_ALERT_TO',sender)
    if not re.fullmatch(r'[^\s@\r\n]+@[^\s@\r\n]+\.[^\s@\r\n]+',recipient):raise RuntimeError('Alert recipient missing')
    message=EmailMessage();message['From']=sender;message['To']=recipient;message['Subject']=subject;message.set_content(body)
    if config.get('MAIL_PROVIDER')!='gmail_api':raise RuntimeError('Configure the existing Gmail alert transport')
    r=requests.post('https://oauth2.googleapis.com/token',data={'client_id':config['GMAIL_CLIENT_ID'],'client_secret':config['GMAIL_CLIENT_SECRET'],'refresh_token':config['GMAIL_REFRESH_TOKEN'],'grant_type':'refresh_token'},timeout=15)
    r.raise_for_status();token=r.json()['access_token']
    r=requests.post('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',headers={'Authorization':'Bearer '+token},json={'raw':base64.urlsafe_b64encode(message.as_bytes()).decode()},timeout=15);r.raise_for_status()

def alert_cycle(observations,config=None,now=None,sender=None):
    """One persistent state across processes; three failures, six-hour reminders, eight emails/day."""
    config=configuration() if config is None else config;now=int(time.time()) if now is None else int(now);sender=send_mail if sender is None else sender
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (STATE/'alerts.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        state=read_json(STATE/'alerts.json');issues=state.setdefault('issues',{});day=time.strftime('%Y-%m-%d',time.gmtime(now))
        if state.get('day')!=day:state.update(day=day,sent=0)
        for code,failed in observations.items():
            if code not in ISSUES:raise ValueError('Unknown issue code')
            issue=issues.setdefault(code,{'streak':0,'open':False,'last_sent':0})
            issue['streak']=issue['streak']+1 if failed else 0
            needs_failure=failed and issue['streak']>=(1 if code=='backup_job' else 3) and (not issue['open'] or now-issue['last_sent']>=21600)
            needs_recovery=not failed and issue['open']
            if not (needs_failure or needs_recovery) or state['sent']>=8 or now<issue.get('retry_after',0):continue
            # Reserve before network call: crashes or mail-provider failures cannot cause storms.
            previous_open=issue['open'];state['sent']+=1;issue['last_sent']=now
            issue['open']=bool(failed);atomic_json(STATE/'alerts.json',state)
            status='ALERT' if failed else 'RECOVERED'
            try:sender('Gao Intelligence '+status+': '+code,ISSUES[code]+'\nStatus: '+status+'\nUTC: '+time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(now))+'\nNo customer documents, credentials or verification codes are included.',config)
            except Exception:
                issue['open']=previous_open
                # Treat uncertain delivery as spent; retry after the reminder interval.
                issue['retry_after']=now+21600
                atomic_json(STATE/'alerts.json',state)
                raise RuntimeError('Alert delivery failed') from None
        atomic_json(STATE/'alerts.json',state)

def health():
    result={}
    for code,url in [('ui','http://127.0.0.1:8501/workspace/_stcore/health'),('api','http://127.0.0.1:8000/health'),('public','https://www.gaointelligence.com/_stcore/health')]:
        try:result[code]=requests.get(url,timeout=10,allow_redirects=False).status_code!=200
        except requests.RequestException:result[code]=True
    result['disk']=shutil.disk_usage('/').used/shutil.disk_usage('/').total>=0.85
    receipt=read_json(STATE/'offsite-last.json');age=time.time()-receipt.get('verified_at',0)
    repository=configuration().get('RESTIC_REPOSITORY','')
    result['backup']=not (0<=age<=26*3600 and receipt.get('remote_restore_verified') and repository and receipt.get('repository_fingerprint')==hashlib.sha256(repository.encode()).hexdigest())
    result['mail']=False
    db=APP/'users.db'
    if db.exists():
        with sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=5) as c:
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='security_events'").fetchone():
                result['mail']=c.execute("SELECT count(*) FROM security_events WHERE kind='mail_delivery_failed' AND stamp>?",(int(time.time())-900,)).fetchone()[0]>0
    return result

def monitor(notify=True):
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    observations=health()
    if notify:alert_cycle(observations)
    atomic_json(STATE/'monitor-last.json',{'checked_at':int(time.time()),'issues':observations})
    print(json.dumps({'healthy':not any(observations.values()),'issues':observations}))
    return not any(observations.values())

def scheduled_backup():
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (STATE/'backup.lock').open('a+b') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Backup already running') from None
        # Serialize with deployments without changing application data or service state.
        with Path('/root/gao-release.lock').open('a+b') as release:
            fcntl.flock(release,fcntl.LOCK_EX)
            restic_env(configuration()) # Never create unbounded local archives when destination is absent.
            if shutil.disk_usage('/').free<2*1024**3:raise RuntimeError('Insufficient backup workspace')
            directory=Path('/root/gao-backups')/(time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-scheduled')
            directory.mkdir(parents=True,mode=0o700)
            from online_backup import backup
            backup(APP,directory)
            alert_cycle({'backup_job':False,'backup':False})

def watchdog():
    observations=health();last=read_json(STATE/'monitor-last.json')
    healthy=not any(observations.values()) and 0<=time.time()-last.get('checked_at',0)<900
    print(json.dumps({'healthy':healthy,'issues':observations,'monitor_fresh':0<=time.time()-last.get('checked_at',0)<900}))
    return healthy

def main():
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['monitor','backup','watchdog','test-alert']);args=parser.parse_args()
    try:
        if args.operation=='backup':scheduled_backup()
        elif args.operation=='monitor':monitor()
        elif args.operation=='watchdog':return 0 if watchdog() else 1
        else:
            # Controlled test does not stop a service or read customer documents.
            for _ in range(3):alert_cycle({'acceptance_test':True})
            alert_cycle({'acceptance_test':False})
        return 0
    except Exception as exc:
        if args.operation=='backup':
            try:alert_cycle({'backup_job':True})
            except Exception:pass
        print('OPERATIONS_FAILED',type(exc).__name__,file=sys.stderr) # Exception strings may contain transport secrets.
        return 1
if __name__=='__main__':sys.exit(main())
