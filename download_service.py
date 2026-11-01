"""Five-minute, single-use download capabilities tied to an active account session and project."""
import hashlib,json,re,secrets,time
from pathlib import Path
from urllib.parse import quote
import user_store,project_store,report_store
from core import document_store

TTL=300
KINDS={'original','bim_json','bim_csv'}

def _hash(value):return hashlib.sha256(value.encode()).hexdigest()
def _schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS download_tickets(token_hash TEXT PRIMARY KEY,user_id INTEGER,project_id INTEGER,session_hash TEXT,kind TEXT,resource TEXT,expires INTEGER,used INTEGER DEFAULT 0)')
    c.execute('CREATE INDEX IF NOT EXISTS download_expiry ON download_tickets(expires)')

def resource(owner,project,kind,identifier):
    project_store.require_project_access(owner,project)
    if kind=='original':
        with document_store.connect() as c:
            row=c.execute('SELECT file_id FROM document_versions WHERE id=? AND user_id=? AND project_id=?',(identifier,int(owner),int(project))).fetchone()
        if not row:raise PermissionError('Download unavailable.')
        version=document_store.get_version(owner,project,row['file_id'],identifier)
        file=document_store.get_file(owner,project,row['file_id']);path=document_store.path_for(version)
        if not path.is_file():raise PermissionError('Original unavailable.')
        return {'path':path,'filename':file['name'],'sha':version['sha']}
    if kind not in ('bim_json','bim_csv'):raise PermissionError('Download unavailable.')
    report=report_store.get_report(owner,project,identifier)
    if not report or report.get('category')!='bim':raise PermissionError('Download unavailable.')
    return {'report':report,'filename':'ifc_inspection.json' if kind=='bim_json' else 'ifc_issues.csv'}

def issue(session_token,project,kind,identifier):
    user=user_store.resolve_session(session_token)
    if not user or kind not in KINDS:raise PermissionError('Sign in to download this file.')
    resource(user['id'],project,kind,identifier)
    token=secrets.token_urlsafe(32);now=int(time.time())
    with user_store.get_connection() as c:
        _schema(c);c.commit();c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM download_tickets WHERE expires<?',(now-3600,))
        count=c.execute('SELECT count(*) FROM download_tickets WHERE session_hash=? AND used=0 AND expires>?',(_hash(session_token),now)).fetchone()[0]
        if count>=100:raise ValueError('Too many pending downloads. Wait five minutes and refresh.')
        c.execute('INSERT INTO download_tickets VALUES(?,?,?,?,?,?,?,0)',(_hash(token),user['id'],int(project),_hash(session_token),kind,identifier,now+TTL))
    return token

def reusable(session_token,token,project,kind,identifier):
    user=user_store.resolve_session(session_token)
    if not user or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token or ''):return False
    with user_store.get_connection() as c:
        _schema(c)
        return c.execute('SELECT 1 FROM download_tickets WHERE token_hash=? AND session_hash=? AND user_id=? AND project_id=? AND kind=? AND resource=? AND used=0 AND expires>?',(_hash(token),_hash(session_token),user['id'],int(project),kind,identifier,int(time.time()))).fetchone() is not None

def consume(token):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise PermissionError('Download unavailable.')
    with user_store.get_connection() as c:
        _schema(c);c.commit();c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM download_tickets WHERE token_hash=? AND used=0 AND expires>?',(_hash(token),int(time.time()))).fetchone()
        if not row:raise PermissionError('Download unavailable.')
        # Session revocation, password recovery and account deactivation revoke tickets too.
        active=c.execute('SELECT 1 FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.user_id=? AND s.expires_at>? AND u.is_active=1',(row['session_hash'],row['user_id'],user_store.utc_now())).fetchone()
        if not active:raise PermissionError('Download unavailable.')
        item=resource(row['user_id'],row['project_id'],row['kind'],row['resource'])
        c.execute('UPDATE download_tickets SET used=1 WHERE token_hash=?',(_hash(token),))
    if row['kind']=='original':
        with item['path'].open('rb') as handle:sha=hashlib.file_digest(handle,'sha256').hexdigest()
        if sha!=item['sha']:raise RuntimeError('Original file integrity check failed.')
        return item
    analysis=item.pop('report')['bim_analysis']
    if row['kind']=='bim_json':item['data']=json.dumps(analysis,indent=2).encode();item['media_type']='application/json'
    else:
        from core.bim_checks import issues_csv
        item['data']=issues_csv(analysis);item['media_type']='text/csv'
    return item
