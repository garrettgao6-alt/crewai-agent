import hashlib,time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from test_document_management import system,legacy_system
from core import document_store
import download_service,user_store
from api import app


def test_http_original_is_owned_single_use_and_has_safe_headers(system):
    owner,other,p,q,_=system
    version=document_store.upload(owner['id'],p['id'],'original.txt',b'PRIVATE_HTTP_ORIGINAL',kind='business')
    token=user_store.create_session(owner['id']);bad=user_store.create_session(other['id'])
    with pytest.raises(PermissionError):download_service.issue(bad,p['id'],'original',version['id'])
    with pytest.raises(PermissionError):download_service.issue(token,q['id'],'original',version['id'])
    ticket=download_service.issue(token,p['id'],'original',version['id'])
    assert token not in ticket and download_service.reusable(token,ticket,p['id'],'original',version['id'])
    client=TestClient(app);url='/private-download/'+ticket
    response=client.get(url)
    assert response.status_code==200 and response.content==b'PRIVATE_HTTP_ORIGINAL'
    assert 'attachment' in response.headers['content-disposition'] and response.headers['cache-control']=='private, no-store'
    assert response.headers['referrer-policy']=='no-referrer'
    assert client.get(url).status_code==404


def test_downloads_expire_and_session_revocation_applies(system,monkeypatch):
    owner,_,p,_,_=system
    version=document_store.upload(owner['id'],p['id'],'original.txt',b'PRIVATE_HTTP_ORIGINAL',kind='business')
    token=user_store.create_session(owner['id']);ticket=download_service.issue(token,p['id'],'original',version['id'])
    now=download_service.time.time();monkeypatch.setattr(download_service.time,'time',lambda:now+301)
    assert TestClient(app).get('/private-download/'+ticket).status_code==404
    monkeypatch.setattr(download_service.time,'time',lambda:now)
    ticket=download_service.issue(token,p['id'],'original',version['id']);user_store.revoke_session(token)
    assert TestClient(app).get('/private-download/'+ticket).status_code==404


def test_concurrent_downloads_cannot_replay_one_ticket(system):
    owner,_,p,_,_=system
    version=document_store.upload(owner['id'],p['id'],'original.txt',b'PRIVATE_HTTP_ORIGINAL',kind='business')
    token=user_store.create_session(owner['id']);ticket=download_service.issue(token,p['id'],'original',version['id'])
    def consume(_):
        try:download_service.consume(ticket);return True
        except PermissionError:return False
    with ThreadPoolExecutor(2) as pool:assert sum(pool.map(consume,range(2)))==1


def test_corrupt_original_is_not_served(system):
    owner,_,p,_,_=system
    version=document_store.upload(owner['id'],p['id'],'original.txt',b'PRIVATE_HTTP_ORIGINAL',kind='business')
    token=user_store.create_session(owner['id']);ticket=download_service.issue(token,p['id'],'original',version['id'])
    document_store.path_for(version).write_bytes(b'changed')
    assert TestClient(app).get('/private-download/'+ticket).status_code==500
