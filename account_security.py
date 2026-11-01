"""Shared database-backed authentication controls; never record passwords/codes."""
import hashlib,time

def fingerprint(value):return hashlib.sha256(str(value).strip().lower().encode()).hexdigest()

def schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS auth_attempts(kind TEXT,subject TEXT,source TEXT,stamp INTEGER)')
    c.execute('CREATE INDEX IF NOT EXISTS auth_attempt_time ON auth_attempts(kind,stamp)')
    c.execute('CREATE TABLE IF NOT EXISTS security_events(kind TEXT,subject TEXT,stamp INTEGER)')

def allowed(c,kind,identifier,source,account_limit=5,source_limit=30):
    schema(c);now=int(time.time());subject=fingerprint(identifier);origin=fingerprint(source or 'local')
    c.execute('DELETE FROM auth_attempts WHERE stamp<?',(now-900,))
    account=c.execute('SELECT count(*) FROM auth_attempts WHERE kind=? AND subject=?',(kind,subject)).fetchone()[0]
    sources=c.execute('SELECT count(*) FROM auth_attempts WHERE kind=? AND source=?',(kind,origin)).fetchone()[0]
    if account>=account_limit or sources>=source_limit:return False
    c.execute('INSERT INTO auth_attempts VALUES(?,?,?,?)',(kind,subject,origin,now))
    return True

def event(c,kind,identifier):
    schema(c);c.execute('DELETE FROM security_events WHERE stamp<?',(int(time.time())-90*86400,))
    c.execute('INSERT INTO security_events VALUES(?,?,?)',(kind,fingerprint(identifier),int(time.time())))
