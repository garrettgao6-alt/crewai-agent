"""One project-authorized, idempotent analysis admission and report owner."""
import hashlib,json,time,uuid
from contextlib import closing
import user_store,project_store,subscription_store,report_store
from core import ncc_library
from core.ncc_catalog import NCCContextRequired

class AnalysisBusy(RuntimeError):pass
class AnalysisFailed(RuntimeError):pass

def analyze(user_id,project_id,query,request_id):
    project_store.require_project_access(user_id,project_id)
    user=user_store.get_user_by_id(user_id)
    if not user or not user.get('email_verified',1):raise PermissionError('Verify your account email first.')
    if not isinstance(query,str) or not 1<=len(query.strip())<=30000:raise ValueError('Enter a request of at most 30,000 characters.')
    if not isinstance(request_id,str) or not 8<=len(request_id)<=128:raise ValueError('A valid request identifier is required.')
    query=query.strip();digest=hashlib.sha256(json.dumps([int(project_id),query]).encode()).hexdigest()
    report_id=uuid.uuid5(uuid.NAMESPACE_URL,f'gao:{user_id}:{project_id}:{request_id}').hex
    # Existing job lookup precedes preflight; completed retries never run retrieval/models.
    with closing(user_store.get_connection()) as c:
        c.execute('CREATE TABLE IF NOT EXISTS analysis_jobs(user_id INTEGER,request_id TEXT,project_id INTEGER,digest TEXT,status TEXT,report_id TEXT,created INTEGER,PRIMARY KEY(user_id,request_id))')
        existing=c.execute('SELECT * FROM analysis_jobs WHERE user_id=? AND request_id=?',(int(user_id),request_id)).fetchone()
    if existing:
        if existing['digest']!=digest:raise ValueError('Request identifier was already used for different input.')
        saved=report_store.get_report(user_id,project_id,existing['report_id'])
        if saved:return saved
        if existing['status']=='running':raise AnalysisBusy('This request is already running. Retry with the same request ID to retrieve its result.')
        raise AnalysisFailed('This request failed. Submit a new request to retry; the previous attempt will not run twice.')
    from core.retriever import is_regulatory_query
    if is_regulatory_query(query):
        try:ncc_library.search_local_references(user_id,query,context=ncc_library.load_project_context(user_id,project_id))
        except NCCContextRequired as exc:
            return {'id':'','project_id':int(project_id),'result':'NCC project context required: '+str(exc),'sources':[],'status':'context_required','version':'2.1'}
    with closing(user_store.get_connection()) as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM analysis_jobs WHERE user_id=? AND request_id=?',(int(user_id),request_id)).fetchone():raise AnalysisBusy('This request is already running. Retry with the same request ID.')
        subscription_store.ensure_subscription_columns(c)
        subscription_store._reset_monthly_usage_if_needed(c,int(user_id))
        row=c.execute('SELECT current_request_count,monthly_request_limit FROM users WHERE id=?',(int(user_id),)).fetchone()
        if row is None or (row[1] is not None and row[0]>=row[1]):raise PermissionError('Account request quota reached.')
        c.execute('UPDATE users SET current_request_count=current_request_count+1 WHERE id=?',(int(user_id),))
        subscription_store._record_usage_event(c,int(user_id),'api_requests',1,subscription_store.format_datetime(subscription_store.utc_now()))
        c.execute('INSERT INTO analysis_jobs VALUES(?,?,?,?,?,?,?)',(int(user_id),request_id,int(project_id),digest,'running',report_id,int(time.time())));c.commit()
    try:
        from core.engine import run_engine
        payload=run_engine(str(user_id),query,project_id=int(project_id),return_details=True)
        if payload.get('status') in ('error','failed'):raise AnalysisFailed('Analysis failed; no successful report was saved.')
        saved=report_store.save_report(user_id,project_id,{**payload,'query':query,'mode':'Copilot'},report_id=report_id)
    except Exception:
        with closing(user_store.get_connection()) as c:
            c.execute("UPDATE analysis_jobs SET status='failed' WHERE user_id=? AND request_id=?",(int(user_id),request_id));c.commit()
        raise
    with closing(user_store.get_connection()) as c:
        c.execute("UPDATE analysis_jobs SET status='completed' WHERE user_id=? AND request_id=?",(int(user_id),request_id));c.commit()
    return saved
