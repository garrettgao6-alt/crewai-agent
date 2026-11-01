from core.storage_lock import Connection as SnapshotConnection
"""Fail-closed, shared private AI reservations; no prompts or credentials in ledger."""
from contextlib import contextmanager, closing
from contextvars import ContextVar
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import hashlib,json,os,sqlite3,uuid
from functools import wraps
import re

DB_PATH=Path(__file__).resolve().parents[1]/'private_ai.db'
_current=ContextVar('private_ai_scope',default=None)
class BudgetError(RuntimeError):pass

def _cap(name,default):
    try:return max(0,min(int(os.getenv(name,str(default))),default))
    except ValueError:return default

@contextmanager
def scope(user_id,project_id):
    identity=(str(user_id),str(project_id))
    existing=_current.get()
    if existing:
        if existing['identity']!=identity:raise PermissionError('AI scope cannot change during a request.')
        yield;return
    token=_current.set({'identity':identity,'tokens':0,'calls':0})
    try:yield
    finally:_current.reset(token)

def project_scope(function):
    @wraps(function)
    def wrapped(user_id,*args,**kwargs):
        match=re.fullmatch(r'u(\d+)_p(\d+)',str(user_id))
        if not match:return function(user_id,*args,**kwargs)
        import project_store
        project_store.require_project_access(*match.groups())
        with scope(*match.groups()):return function(user_id,*args,**kwargs)
    return wrapped

def _connect():
    c=sqlite3.connect(DB_PATH,timeout=10,isolation_level=None,factory=SnapshotConnection)
    c.executescript('''CREATE TABLE IF NOT EXISTS ai_budget(period TEXT,scope TEXT,tokens INTEGER NOT NULL,calls INTEGER NOT NULL,blocked INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(period,scope));
    CREATE TABLE IF NOT EXISTS ai_calls(id TEXT PRIMARY KEY,day TEXT,owner TEXT,project TEXT,reserved INTEGER,actual INTEGER,status TEXT);''')
    return c

def reserve(tokens):
    context=_current.get()
    if context is None:raise BudgetError('An authorized project AI scope is required.')
    if tokens<=0 or context['tokens']+tokens>_cap('PRIVATE_AI_REQUEST_TOKENS',250000) or context['calls']>=256:
        raise BudgetError('This request exceeds its token/call budget. Narrow the question or document batch.')
    now=datetime.now(ZoneInfo('Australia/Melbourne'));day=now.date().isoformat();month=now.strftime('%Y-%m')
    owner,project=context['identity']
    limits=[('global','GLOBAL',2000000,20000000,2000),('u:'+owner,'USER',500000,5000000,500),('p:'+owner+':'+project,'PROJECT',250000,2000000,300)]
    try:
        with closing(_connect()) as c:
            c.execute('BEGIN IMMEDIATE')
            for name,prefix,daily,monthly,calls in limits:
                for period,cap in ((day,_cap('PRIVATE_AI_'+prefix+'_DAILY_TOKENS',daily)),(month,_cap('PRIVATE_AI_'+prefix+'_MONTHLY_TOKENS',monthly))):
                    row=c.execute('SELECT tokens,calls,blocked FROM ai_budget WHERE period=? AND scope=?',(period,name)).fetchone() or (0,0,0)
                    if row[2] or row[0]+tokens>cap or row[1]+1>(calls if period==day else calls*31):raise BudgetError('Private AI budget reached. Try after the budget resets or contact the administrator.')
                    c.execute('INSERT INTO ai_budget(period,scope,tokens,calls) VALUES(?,?,?,1) ON CONFLICT(period,scope) DO UPDATE SET tokens=tokens+excluded.tokens,calls=calls+1',(period,name,tokens))
            call=uuid.uuid4().hex
            c.execute('INSERT INTO ai_calls VALUES(?,?,?,?,?,NULL,?)',(call,day,owner,project,tokens,'reserved'));c.commit()
    except sqlite3.Error:raise BudgetError('AI budget storage unavailable; no provider call was sent.') from None
    context['tokens']+=tokens;context['calls']+=1
    return call

def finish(call,actual,status):
    try:
        with closing(_connect()) as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT day,reserved FROM ai_calls WHERE id=?',(call,)).fetchone()
            if row and actual is not None and actual>row[1]:
                c.execute("UPDATE ai_budget SET blocked=1 WHERE scope='global' AND period IN (?,?)",(row[0],row[0][:7]));status='accounting_anomaly'
            c.execute('UPDATE ai_calls SET actual=?,status=? WHERE id=?',(actual,status,call));c.commit()
    except sqlite3.Error:pass # Reservation remains spent on failure; never refund uncertain work.

class _Resource:
    def __init__(self,resource,kind):self.resource,self.kind=resource,kind
    def create(self,**kwargs):
        data=kwargs.get('input','')
        size=len(json.dumps(data,ensure_ascii=False).encode('utf-8'))+len(str(kwargs.get('instructions','')).encode('utf-8'))
        if size>120000:raise BudgetError('AI input exceeds the 120 KB safety limit. Narrow this review.')
        if self.kind=='responses':
            kwargs['max_output_tokens']=min(int(kwargs.get('max_output_tokens',2000)),2000)
            kwargs['store']=False
            output=kwargs['max_output_tokens']
        else:output=0
        call=reserve(size+2048+output)
        try:
            result=self.resource.create(**kwargs)
            usage=getattr(result,'usage',None)
            actual=getattr(usage,'total_tokens',None)
            finish(call,actual,'completed')
            return result
        except Exception:
            finish(call,None,'failed');raise

def client(factory):
    if _current.get() is None:raise BudgetError('Private AI requires an authorized project scope.')
    raw=factory(max_retries=0,timeout=45)
    class Client:pass
    result=Client();result.responses=_Resource(raw.responses,'responses');result.embeddings=_Resource(raw.embeddings,'embeddings')
    return result
