import pytest
import account_recovery as r
import user_store as u

@pytest.fixture
def account(tmp_path,monkeypatch):
    monkeypatch.setattr(u,'DB_PATH',tmp_path/'users.db')
    monkeypatch.setenv('MAX_USERS','0')
    monkeypatch.delenv('ADMIN_USERNAME',raising=False)
    monkeypatch.setenv('SMTP_HOST','example.test')
    monkeypatch.setenv('SMTP_FROM','noreply@example.test')
    u.initialize_user_store()
    user=u.create_user('Alice','alice@example.test','old-password')
    sent=[]
    monkeypatch.setattr(r,'_send',lambda email,code:sent.append(code))
    return user,sent

def test_reset_is_single_use_and_revokes_sessions(account):
    user,sent=account; token=u.create_session(user['id'])
    assert r.request_code('unknown@example.test')==r.request_code(user['email'])
    r.request_code(user['email']); assert len(sent)==1
    with u.get_connection() as c:
        assert sent[0] not in str(dict(c.execute('SELECT * FROM password_recovery').fetchone()))
    r.reset_password(user['email'],sent[0],'new-password')
    assert u.resolve_session(token) is None
    assert u.authenticate_user(user['email'],'old-password') is None
    assert u.authenticate_user(user['email'],'new-password')
    with pytest.raises(ValueError):r.reset_password(user['email'],sent[0],'another-password')

def test_attempts_and_expiry(account,monkeypatch):
    user,sent=account;r.request_code(user['email'])
    for _ in range(5):
        with pytest.raises(ValueError):r.reset_password(user['email'],'bad','new-password')
    with pytest.raises(ValueError):r.reset_password(user['email'],sent[0],'new-password')
    assert u.authenticate_user(user['email'],'old-password')
    monkeypatch.setattr(r.time,'time',lambda:9999999999)
    with pytest.raises(ValueError):r.reset_password(user['email'],sent[0],'new-password')

def test_rename_identity_password_and_conflict(account):
    user,_=account;u.create_user('Bob','bob@example.test','other-password')
    with pytest.raises(ValueError):r.change_username(user['id'],'wrong','NewAlice')
    with pytest.raises(ValueError):r.change_username(user['id'],'old-password','bOB')
    updated=r.change_username(user['id'],'old-password','NewAlice')
    assert updated['id']==user['id'] and updated['email']==user['email']
    assert u.authenticate_user('NewAlice','old-password')
    assert u.authenticate_user('Alice','old-password') is None

def test_delivery_unavailable_and_failure(account,monkeypatch):
    user,_=account;monkeypatch.delenv('SMTP_HOST')
    with pytest.raises(u.UserStoreError):r.request_code(user['email'])
    monkeypatch.setenv('SMTP_HOST','example.test')
    def fail(*args):raise RuntimeError('delivery failed')
    monkeypatch.setattr(r,'_send',fail)
    assert r.request_code(user['email'])==r.GENERIC_RESPONSE
    with u.get_connection() as c:assert c.execute('SELECT count(*) FROM password_recovery').fetchone()[0]==0
