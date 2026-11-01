"""Authorized originals and immutable versions. Archival never deletes originals or report evidence."""
from contextlib import contextmanager,closing
from pathlib import Path
from contextvars import ContextVar
from copy import deepcopy
import fcntl,hashlib,json,os,re,sqlite3,time,unicodedata,uuid
import project_store,user_store,subscription_store
from core.storage_lock import Connection,snapshot_guard

MAX_BYTES=50*1024*1024
OWNER_BYTES=600*1024*1024
FORMATS={'.pdf','.txt','.docx','.xlsx','.ifc'}
_snapshot=ContextVar('document_visibility',default=None)

def root():return Path(project_store.DB_PATH).resolve().parent/'project_documents'
def database():return Path(project_store.DB_PATH).with_name('documents.db')
def authorize(owner,project):
    project_store.require_project_access(owner,project)
    if not user_store.get_user_by_id(owner):raise PermissionError('An active account is required.')

def connect():
    c=sqlite3.connect(database(),timeout=30,factory=Connection);c.row_factory=sqlite3.Row
    c.executescript('''CREATE TABLE IF NOT EXISTS document_files(id TEXT PRIMARY KEY,user_id INTEGER,project_id INTEGER,name TEXT,name_key TEXT,active_version TEXT,archived INTEGER DEFAULT 0,created INTEGER,UNIQUE(user_id,project_id,name_key));
    CREATE TABLE IF NOT EXISTS document_versions(id TEXT PRIMARY KEY,file_id TEXT,user_id INTEGER,project_id INTEGER,version INTEGER,size INTEGER,sha TEXT,extension TEXT,status TEXT,kind TEXT,edition TEXT,chunks INTEGER DEFAULT 0,error TEXT DEFAULT '',analysis TEXT DEFAULT '{}',created INTEGER,charged INTEGER DEFAULT 0,quota_period TEXT DEFAULT '');
    CREATE INDEX IF NOT EXISTS document_owner ON document_files(user_id,project_id);
    CREATE INDEX IF NOT EXISTS document_version_file ON document_versions(file_id,version);''')
    columns={r[1] for r in c.execute('PRAGMA table_info(document_versions)')}
    for name,definition in [('charged','INTEGER DEFAULT 0'),('quota_period',"TEXT DEFAULT ''")]:
        if name not in columns:c.execute(f'ALTER TABLE document_versions ADD COLUMN {name} {definition}')
    c.commit()
    return c

def filename(value):
    value=unicodedata.normalize('NFC',str(value).strip())
    if not value or len(value)>200 or value in ('.','..') or any(unicodedata.category(c).startswith('C') or c in '/\\' for c in value):raise ValueError('Use a plain filename of at most 200 characters.')
    extension=Path(value).suffix.lower()
    if extension not in FORMATS:raise ValueError('Supported files: PDF, TXT, DOCX, XLSX and IFC.')
    return value,extension

@contextmanager
def writer(owner,project):
    authorize(owner,project)
    with snapshot_guard():
        root().mkdir(parents=True,exist_ok=True,mode=0o700);root().chmod(0o700)
        locks=root()/'.locks';locks.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (locks/f'u{int(owner)}.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            yield

def path_for(version):
    if not re.fullmatch('[a-f0-9]{32}',version['id']):raise ValueError('Invalid document version.')
    base=root().resolve();path=base/f"u{int(version['user_id'])}"/f"p{int(version['project_id'])}"/(version['id']+'.bin')
    if not path.resolve().is_relative_to(base):raise PermissionError('Invalid document path.')
    return path

def list_files(owner,project,archived=False):
    authorize(owner,project);recover_interrupted(owner,project)
    with closing(connect()) as c:
        rows=c.execute('SELECT f.*,v.version,v.size,v.sha,v.status,v.kind,v.chunks,v.error,v.created AS uploaded FROM document_files f LEFT JOIN document_versions v ON v.id=COALESCE(f.active_version,(SELECT id FROM document_versions WHERE file_id=f.id ORDER BY version DESC LIMIT 1)) WHERE f.user_id=? AND f.project_id=? AND f.archived=? ORDER BY f.name_key',(int(owner),int(project),int(archived))).fetchall()
        return [dict(r) for r in rows]

def get_file(owner,project,file_id):
    authorize(owner,project)
    with closing(connect()) as c:row=c.execute('SELECT * FROM document_files WHERE id=? AND user_id=? AND project_id=?',(file_id,int(owner),int(project))).fetchone()
    if not row:raise PermissionError('Document not found or access denied.')
    return dict(row)

def versions(owner,project,file_id):
    get_file(owner,project,file_id)
    with closing(connect()) as c:return [dict(r) for r in c.execute('SELECT id,file_id,user_id,project_id,version,size,sha,extension,status,kind,edition,chunks,error,created,charged,quota_period FROM document_versions WHERE file_id=? AND user_id=? AND project_id=? ORDER BY version DESC',(file_id,int(owner),int(project)))]

def get_version(owner,project,file_id,version_id):
    get_file(owner,project,file_id)
    with closing(connect()) as c:row=c.execute('SELECT * FROM document_versions WHERE id=? AND file_id=? AND user_id=? AND project_id=?',(version_id,file_id,int(owner),int(project))).fetchone()
    if not row:raise PermissionError('Document version not found or access denied.')
    return dict(row)

def original(owner,project,file_id,version_id):
    version=get_version(owner,project,file_id,version_id);path=path_for(version)
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=version['sha']:raise RuntimeError('Original file checksum failed. Restore from a verified backup.')
    return data

def _reserve_usage(owner,version_id):
    # ATTACH keeps the monthly reservation and durable version marker in one
    # SQLite transaction, so interrupted uploads can be refunded exactly once.
    with user_store.get_connection() as c:
        c.execute('ATTACH DATABASE ? AS docs',(str(database()),));c.execute('BEGIN IMMEDIATE')
        subscription_store.ensure_subscription_columns(c);subscription_store._reset_monthly_usage_if_needed(c,int(owner))
        row=c.execute('SELECT is_active,email_verified,current_document_count,monthly_document_limit,subscription_start FROM users WHERE id=?',(int(owner),)).fetchone()
        if not row or not row[0] or not row[1]:raise PermissionError('Verify your email before uploading documents.')
        if row[3] is not None and row[2]>=row[3]:raise PermissionError('Monthly document quota reached.')
        c.execute('UPDATE users SET current_document_count=current_document_count+1 WHERE id=?',(int(owner),))
        c.execute('UPDATE docs.document_versions SET charged=1,quota_period=? WHERE id=?',(row[4] or '',version_id))
        subscription_store._record_usage_event(c,int(owner),'documents',1,subscription_store.format_datetime(subscription_store.utc_now()))


def _fail_version(owner,version_id,reason):
    with user_store.get_connection() as c:
        c.execute('ATTACH DATABASE ? AS docs',(str(database()),));c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT charged,quota_period FROM docs.document_versions WHERE id=? AND user_id=?',(version_id,int(owner))).fetchone()
        period=c.execute('SELECT subscription_start FROM users WHERE id=?',(int(owner),)).fetchone()
        if row and row[0] and period and (period[0] or '')==row[1]:
            c.execute('UPDATE users SET current_document_count=MAX(0,current_document_count-1) WHERE id=?',(int(owner),))
            subscription_store._record_usage_event(c,int(owner),'documents',-1,subscription_store.format_datetime(subscription_store.utc_now()))
        c.execute("UPDATE docs.document_versions SET status='failed',charged=0,error=? WHERE id=? AND user_id=?",(reason[:400],version_id,int(owner)))


def recover_interrupted(owner,project):
    authorize(owner,project)
    with snapshot_guard():
        root().mkdir(parents=True,exist_ok=True,mode=0o700);root().chmod(0o700)
        locks=root()/'.locks';locks.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (locks/f'u{int(owner)}.lock').open('a+b') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return
            with closing(connect()) as c:
                ids=[r[0] for r in c.execute("SELECT id FROM document_versions WHERE user_id=? AND project_id=? AND status='processing' AND created<?",(int(owner),int(project),int(time.time())-1200))]
            for version_id in ids:_fail_version(owner,version_id,'Processing was interrupted. The original is retained; retry the upload.')


def upload(owner,project,name,data,kind=None,edition='',local_processor=None):
    authorize(owner,project);name,extension=filename(name)
    if not isinstance(data,bytes) or not data or len(data)>MAX_BYTES:raise ValueError('Upload a nonempty file no larger than 50 MB.')
    if extension=='.ifc' and local_processor is None:raise ValueError('Use BIM Model Checks to inspect an IFC model.')
    sha=hashlib.sha256(data).hexdigest()
    with writer(owner,project):
        with closing(connect()) as c:
            c.execute('BEGIN IMMEDIATE')
            file=c.execute('SELECT * FROM document_files WHERE user_id=? AND project_id=? AND name_key=?',(int(owner),int(project),name.casefold())).fetchone()
            if file and not file['archived'] and file['active_version']:
                existing=c.execute('SELECT * FROM document_versions WHERE id=?',(file['active_version'],)).fetchone()
                if existing and existing['status']=='ready' and existing['sha']==sha and existing['kind']==(kind or 'auto') and existing['edition']==edition:return dict(existing)
            if file:name=file['name']
            total=c.execute('SELECT COALESCE(sum(size),0) FROM document_versions WHERE user_id=?',(int(owner),)).fetchone()[0]
            if c.execute('SELECT count(*) FROM document_versions WHERE user_id=?',(int(owner),)).fetchone()[0]>=1000:raise PermissionError('The 1,000 retained-version limit has been reached. Contact the administrator.')
            if total+len(data)>OWNER_BYTES:raise PermissionError('The 600 MB original-file storage limit has been reached. Archived versions also use storage.')
            file_id=file['id'] if file else uuid.uuid4().hex
            if not file:c.execute('INSERT INTO document_files VALUES(?,?,?,?,?,NULL,0,?)',(file_id,int(owner),int(project),name,name.casefold(),int(time.time())))
            number=c.execute('SELECT COALESCE(max(version),0)+1 FROM document_versions WHERE file_id=?',(file_id,)).fetchone()[0]
            version_id=uuid.uuid4().hex
            c.execute('INSERT INTO document_versions(id,file_id,user_id,project_id,version,size,sha,extension,status,kind,edition,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(version_id,file_id,int(owner),int(project),number,len(data),sha,extension,'processing',kind or 'auto',edition,int(time.time())))
            c.commit()
        version=get_version(owner,project,file_id,version_id);path=path_for(version)
        try:
            path.parent.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.parent.parent.chmod(0o700)
            path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.parent.chmod(0o700)
            temporary=path.with_suffix('.upload')
            try:
                with temporary.open('xb') as handle:
                    os.chmod(temporary,0o600);handle.write(data);handle.flush();os.fsync(handle.fileno())
                os.replace(temporary,path)
            finally:
                temporary.unlink(missing_ok=True)
            _reserve_usage(owner,version_id)
            if local_processor:
                analysis=local_processor(path);count=0
            else:
                from core.ingestion import ingest_document
                count=ingest_document(owner,project,name,data,kind,edition=edition,managed_version_id=version_id);analysis={}
            with closing(connect()) as c:
                c.execute('BEGIN IMMEDIATE')
                c.execute("UPDATE document_versions SET status='ready',chunks=?,analysis=? WHERE id=?",(count,json.dumps(analysis),version_id))
                c.execute('UPDATE document_files SET active_version=?,archived=0 WHERE id=?',(version_id,file_id));c.commit()
        except Exception as exc:
            safe=str(exc) if isinstance(exc,(ValueError,PermissionError)) else 'Processing failed. The preceding active version is preserved. Check file validity, account budget and service availability.'
            _fail_version(owner,version_id,safe)
            raise ValueError(safe) from None
        return get_version(owner,project,file_id,version_id)

def set_archived(owner,project,file_id,archived=True):
    with writer(owner,project):
        get_file(owner,project,file_id)
        with closing(connect()) as c:c.execute('UPDATE document_files SET archived=? WHERE id=?',(int(archived),file_id));c.commit()

def activate_version(owner,project,file_id,version_id):
    with writer(owner,project):
        version=get_version(owner,project,file_id,version_id)
        if version['status']!='ready':raise ValueError('Only successfully processed versions can be restored.')
        original(owner,project,file_id,version_id)
        with closing(connect()) as c:c.execute('UPDATE document_files SET active_version=?,archived=0 WHERE id=?',(version_id,file_id));c.commit()

def _visibility(scope):
    """Exclude archived, superseded and failed versions, while retaining untouched legacy indexes."""
    match=re.fullmatch(r'u(\d+)_p(\d+)',str(scope))
    if not match or not database().exists():return None
    owner,project=map(int,match.groups());authorize(owner,project)
    with closing(connect()) as c:
        rows=c.execute('SELECT name,active_version,archived FROM document_files WHERE user_id=? AND project_id=? AND (active_version IS NOT NULL OR archived=1)',(owner,project)).fetchall()
        inactive=[r[0] for r in c.execute('SELECT v.id FROM document_versions v JOIN document_files f ON f.id=v.file_id WHERE v.user_id=? AND v.project_id=? AND (f.archived=1 OR f.active_version IS NULL OR f.active_version!=v.id)',(owner,project))]
    conditions=[]
    if inactive:conditions.append({'managed_version_id':{'$nin':inactive}})
    if rows:
        names=[r['name'] for r in rows];active=[r['active_version'] for r in rows if not r['archived'] and r['active_version']]
        branches=[{'source':{'$nin':names}}]
        if active:branches.append({'managed_version_id':{'$in':active}})
        conditions.append(branches[0] if len(branches)==1 else {'$or':branches})
    return None if not conditions else conditions[0] if len(conditions)==1 else {'$and':conditions}

def legacy_indexes(owner,project):
    authorize(owner,project)
    from core import vector_store
    scope=project_store.document_scope(owner,project)
    with closing(connect()) as c:managed={r[0] for r in c.execute('SELECT name FROM document_files WHERE user_id=? AND project_id=? AND (active_version IS NOT NULL OR archived=1)',(int(owner),int(project)))}
    result={}
    for collection in [vector_store.get_collection(scope),vector_store.get_ncc_collection(scope),vector_store.get_ncc_collection(scope,housing=True)]:
        for metadata in collection.get(include=['metadatas']).get('metadatas',[]):
            if metadata and not metadata.get('managed_version_id') and metadata.get('source') not in managed:
                name=metadata.get('source','Unknown source');result[name]=result.get(name,0)+1
    return [{'File':name,'Indexed chunks':count,'Original':'Not retained by the old upload pipeline; re-upload to manage versions.'} for name,count in sorted(result.items())]

@contextmanager
def retrieval_snapshot(scope):
    token=_snapshot.set((str(scope),_visibility(scope)))
    try:yield
    finally:_snapshot.reset(token)


def retrieval_filter(scope,where=None):
    cached=_snapshot.get()
    visible=deepcopy(cached[1]) if cached and cached[0]==str(scope) else _visibility(scope)
    return {'$and':[where,visible]} if where and visible else where or visible


def validate_managed_version(owner,project,version_id,name,sha):
    authorize(owner,project)
    with closing(connect()) as c:
        row=c.execute('SELECT v.sha,v.status,f.name FROM document_versions v JOIN document_files f ON f.id=v.file_id WHERE v.id=? AND v.user_id=? AND v.project_id=?',(version_id,int(owner),int(project))).fetchone()
    if not row or row['sha']!=sha or row['name']!=name or row['status']!='processing':raise PermissionError('Invalid processing version.')


def is_managed(owner,project,name):
    if not database().exists():return False
    with closing(connect()) as c:return c.execute('SELECT 1 FROM document_files WHERE user_id=? AND project_id=? AND name_key=?',(int(owner),int(project),unicodedata.normalize('NFC',name.strip()).casefold())).fetchone() is not None
